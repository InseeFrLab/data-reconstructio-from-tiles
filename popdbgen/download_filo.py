#!/usr/bin/env python3
import logging
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import py7zr
import requests

from .utils import DATA_DIR, territory_code

# URL par défaut du fichier à télécharger
FILO_URL: str = "https://www.insee.fr/fr/statistiques/fichier/7655475/Filosofi2019_carreaux_200m_gpkg.zip"
ADULT_AGE_COLUMNS: list[str] = ["ind_18_24", "ind_25_39", "ind_40_54", "ind_55_64", "ind_65_79", "ind_80p", "ind_inc"]
MINOR_AGE_COLUMNS: list[str] = ["ind_0_3", "ind_4_5", "ind_6_10", "ind_11_17"]
HOUSEHOLD_COLUMNS: list[str] = ["men_1ind", "men_5ind", "men_prop", "men_fmp", "men_coll", "men_mais"]
NUMERIC_COLUMNS: list[str] = ["ind_snv", "men_pauv"]


def get_FILO_filename(territory: str | int = "france", dataDir: Path = DATA_DIR) -> Path:
    territory = territory_code(territory)
    if territory == "france":
        return dataDir / "carreaux_200m_met.gpkg"
    elif territory == "972":
        return dataDir / "carreaux_200m_mart.gpkg"
    elif territory == "974":
        return dataDir / "carreaux_200m_reun.gpkg"
    else:
        raise FileNotFoundError(f"No FILO file for territory [{territory}]!")


def download_extract_FILO(dataDir: Path = DATA_DIR, overwriteIfExists: bool = False) -> None:
    logging.info("Downloading FILO resources")

    if not dataDir.exists():
        logging.info("Creating data folder")
        dataDir.mkdir(exist_ok=True)

    # Chemin pour enregistrer le fichier zip téléchargé
    zip_path: Path = dataDir / "carreaux_200m.7z"
    # Chemin pour enregistrer le fichier 7z téléchargé
    seven_zip_path = dataDir / "Filosofi2019_carreaux_200m_gpkg.7z"

    # Check that the files were not already created
    met_gpkg_zip_path = dataDir / get_FILO_filename()
    if met_gpkg_zip_path.is_file():
        if overwriteIfExists:
            logging.info("Overwriting already existing data files")
        else:
            logging.info("Data files already exists, skipping download")
            return

    logging.info(f"Downloading data file from {FILO_URL}")
    response = requests.get(FILO_URL)
    with open(zip_path, "wb") as file:
        file.write(response.content)

    logging.info("Extracting from zip file")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(dataDir)

    logging.info("Removing zip file")
    zip_path.unlink()

    logging.info("Extracting from 7z file")
    with py7zr.SevenZipFile(seven_zip_path, mode="r") as z:
        z.extractall(path=dataDir)

    logging.info("Removing 7z file")
    seven_zip_path.unlink()

    logging.info("Download and extraction done.")


def round_alea(x: pd.Series) -> pd.Series:
    """
    If X = I + D (I natural, 0 <= D < 1),
    then returns I+1 with probability D and I with probablity 1-D
    """
    i, d = divmod(x, 1)
    return (i + (np.random.rand(len(x)) < d)).astype(int)


def name_integer_column(names: list[str]) -> list[str]:
    return [s + "i" for s in names]


def refine_FILO(gdf: gpd.GeoDataFrame, territory: str | int = "france", coherence_check: bool = False) -> pd.DataFrame:
    gdf.drop(columns=["idcar_1km", "idcar_nat", "i_est_200", "i_est_1km"], inplace=True)
    gdf.rename(columns={"idcar_200m": "tile_id"}, inplace=True)

    logging.info("Counts to integers")

    variables = ["ind", "men"] + ADULT_AGE_COLUMNS + MINOR_AGE_COLUMNS + HOUSEHOLD_COLUMNS
    gdfi = gdf[variables].apply(round_alea)
    gdfi.columns = name_integer_column(variables)
    gdfi = pd.concat([gdf[["tile_id"] + NUMERIC_COLUMNS], gdfi], axis=1)

    gdfi.loc[(gdfi["meni"] == 0) * (gdfi["indi"] > 0), "meni"] = 1

    gdfi["inda"] = gdfi[name_integer_column(ADULT_AGE_COLUMNS + MINOR_AGE_COLUMNS)].sum(axis=1)
    gdfi["diff_ind"] = gdfi.indi - gdfi.inda
    gdfi["men_adult_inconsist"] = gdfi.meni > gdfi[name_integer_column(ADULT_AGE_COLUMNS)].sum(axis=1)

    # ou mettre en logging.debug
    logging.debug(f"Somme des écarts absolus des comptages d'individus {gdfi.diff_ind.abs().sum()}")  # flush=True
    logging.debug(f"Nb de carreaux avec des écarts dans les comptages d'individus {(gdfi.diff_ind != 0).sum()}")
    logging.debug(f"Nb de carreaux avec un nb d'adultes insuffisants {sum(gdfi.men_adult_inconsist)}")

    logging.info("Handling inconsistencies")

    for i, row in gdfi.iterrows():
        if row["diff_ind"] == 0 and not row["men_adult_inconsist"]:
            continue

        # Gestion de la cohérence des âges des individus avec le nb d'individus
        diff = row["diff_ind"]
        if diff > 0:  # indi > inda => ajouter des individus la classe d'âge inconnu
            row["ind_inci"] += diff
        elif (
            diff < 0
        ):  # indi < inda => retirer des individus dans certaines catégories d'âge (en priorité la catégorie inconnue)
            inci = row["ind_inci"]
            if inci > 0:
                new_inci = np.maximum(0, inci + diff)
                row["ind_inci"] = new_inci
                diff += inci - new_inci

            while diff != 0:
                if sum(row[name_integer_column(ADULT_AGE_COLUMNS)]) > row.meni:
                    eligible_categories = [
                        s
                        for s in name_integer_column(ADULT_AGE_COLUMNS + MINOR_AGE_COLUMNS)
                        if s != "ind_inci" and row[s] > 0
                    ]
                else:
                    eligible_categories = [
                        s for s in name_integer_column(MINOR_AGE_COLUMNS) if s != "ind_inci" and row[s] > 0
                    ]

                if diff > 0:
                    raise Exception("Le code est absurde !")
                else:
                    drawn_cat = np.random.choice(eligible_categories)
                    row[drawn_cat] -= 1
                    diff += 1

        # Gestion des incohérences résiduelles entre nb d'adultes et nb de ménages
        diff = row.meni - sum(row[name_integer_column(ADULT_AGE_COLUMNS)])
        while diff > 0:
            eligible_categories = [s for s in name_integer_column(MINOR_AGE_COLUMNS) if row[s] > 0]
            drawn_cat = np.random.choice(eligible_categories)
            row[drawn_cat] -= 1
            row["ind_inci"] += 1
            diff -= 1

        gdfi.iloc[i] = row

    gdfi["plus18i"] = gdfi[name_integer_column(ADULT_AGE_COLUMNS)].sum(axis=1)
    gdfi["moins18i"] = gdfi[name_integer_column(MINOR_AGE_COLUMNS)].sum(axis=1)
    gdfi["inda"] = gdfi["plus18i"] + gdfi["moins18i"]
    gdfi["diff_ind"] = gdfi.indi - gdfi.inda

    logging.debug(f"Somme des écarts absolus des comptages d'individus {gdfi.diff_ind.abs().sum()}")
    logging.debug(f"Nb de carreaux avec des écarts dans les comptages d'individus {str(sum(gdfi.diff_ind.abs() > 0 ))}")
    logging.debug(
        f"Nb de carreaux avec un nb d'adultes insuffisants \
            {str(sum(gdfi.meni > gdfi[name_integer_column(ADULT_AGE_COLUMNS)].sum(axis=1)))}"
    )

    # plus18: at least 1 and no more than indi
    # gdf["plus18i"] = np.maximum(
    #     1,
    #     np.minimum(
    #         gdf.indi,
    #         round_alea(gdf.ind_18_24 + gdf.ind_25_39 + gdf.ind_40_54 + gdf.ind_55_64 + gdf.ind_65_79 + gdf.ind_80p),
    #     ),
    # )
    # gdf["moins18i"] = gdf.indi - gdf.plus18i
    # # meni: at least 1 and no more than plus18i
    # gdf["meni"] = np.maximum(1, np.minimum(gdf.plus18i, round_alea(gdf.men)))

    # Coordonnées des points NE et SO - le point de référence est le point en bas à gauche
    gdfi["YSO"] = gdfi.tile_id.str.extract(r"200mN(.*?)E").astype(int)
    gdfi["XSO"] = gdfi.tile_id.str.extract(r".*E(.*)").astype(int)
    gdfi["YNE"] = gdfi.YSO + 200
    gdfi["XNE"] = gdfi.XSO + 200

    # TODO
    # - preprocess more columns from FILO (age categories, revenue, etc.)
    # - cleanup: remove columns with little interest from the original GeoDataFrame
    # - (optional) return a fresh GeoDataFrame copy rather than edit in place ?
    return gdfi


def coherence_check(tiled_filo: pd.DataFrame):
    if False:
        raise Exception("")
    # TODO
    # - Perform some sanity check on the output of refine_FILO
    return None


def load_FILO(territory: str = "france", check_coherence: bool = False, dataDir: Path = DATA_DIR):
    download_extract_FILO()
    file_path = get_FILO_filename(territory, dataDir=dataDir)
    tiled_filo = gpd.read_file(file_path)
    refined_filo = refine_FILO(tiled_filo, territory=territory)
    if check_coherence:
        coherence_check(refined_filo)
    return refined_filo


if __name__ == "__main__":
    download_extract_FILO()
