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
MINOR_AGE_COLUMNS: list[str] = ["ind_0_3", "ind_4_5", "ind_6_10", "ind_11_17"]
ADULT_AGE_COLUMNS: list[str] = ["ind_18_24", "ind_25_39", "ind_40_54", "ind_55_64", "ind_65_79", "ind_80p", "ind_inc"]
ALL_AGE_COLUMNS: list[str] = MINOR_AGE_COLUMNS + ADULT_AGE_COLUMNS
HOUSEHOLD_IND_COLUMNS: list[str] = [
    "men_1ind",  # Nombre de ménages d'un seul individu
    "men_5ind",  # Nombre de ménages de 5 individus ou plus
    "men_fmp",  # Nombre de ménages monoparentaux
]
HOUSEHOLD_BAT_COLUMNS: list[str] = [
    "men_prop",  # Nombre de ménages propriétaires
    "men_coll",  # Nombre de ménages en logement collectif
    "men_mais",  # Nombre de ménages en maison
]
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
    logging.info("Downloading and extracting FILO resources...")

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
            logging.info("Data files already exists, skipping download.")
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

    logging.info(f"FILO data successfully downloaded and extracted in {dataDir}")


def name_integer_column(names: list[str]) -> list[str]:
    return [s + "i" for s in names]


def divmod1(x: float) -> tuple[int, float]:
    i, d = divmod(x, 1)
    return int(i), d


def single_round_alea(x: float) -> int:
    i, d = divmod1(x)
    return i + (np.random.random() < d)


def refine_FILO_tile(s: pd.Series) -> dict:
    o = {}
    o["ind"] = max(1, single_round_alea(s.ind))
    o["men"] = min(o["ind"], max(1, single_round_alea(s.men)))

    bumps = {}
    for c in ADULT_AGE_COLUMNS + MINOR_AGE_COLUMNS:
        i, d = divmod1(s[c])
        # Keep the rounded down value for now
        o[c] = i
        # A score for this column's likelihood to be bumped +1
        bumps[c] = d * np.random.random()

    age_adult = sum(int(o[k]) for k in ADULT_AGE_COLUMNS)
    missing_adults = o["men"] - age_adult
    if missing_adults > 0:
        # We need more adults to have one per household
        cols = sorted(ADULT_AGE_COLUMNS, key=lambda c: bumps[c], reverse=True)
        for c in cols[:missing_adults]:
            o[c] += 1
            bumps[c] = 0

    age_indiv = sum(int(o[k]) for k in ADULT_AGE_COLUMNS + MINOR_AGE_COLUMNS)
    missing_indiv = o["ind"] - age_indiv
    if missing_indiv > 0:
        # We need more people in the age columns to match the total "ind"
        cols = sorted(ADULT_AGE_COLUMNS + MINOR_AGE_COLUMNS, key=lambda c: bumps[c], reverse=True)
        for c in cols[:missing_indiv]:
            o[c] += 1
    elif missing_indiv < 0:
        # We added to many adults to match households and now need to remove (children necessarily)
        eligible_cols = [c for c in MINOR_AGE_COLUMNS if o[c] > 0]
        # Sort by bump score, starting with the lowest
        cols = sorted(eligible_cols, key=lambda c: bumps[c], reverse=False)
        for c in cols[:-missing_indiv]:
            o[c] -= 1

    o["men_1ind"], remain_men_1ind = divmod1(s["men_1ind"])
    o["men_5ind"], remain_men_5ind = divmod1(s["men_5ind"])
    o["men_fmp"], remain_men_fmp = divmod1(s["men_fmp"])

    # ind is bounded below by:
    #   men_1ind + 5*men_5ind + 2*(men-men_1ind-men_5ind)
    # Meaning
    #   ind >= 2*men + 3*men_5ind - men_1ind
    # a)  men_1ind >= 2*men + 3*men_5ind - ind
    # b) 3*men_5ind <= ind - 2*men + men_1ind
    #
    # Besides, if men_5ind == 0, then ind is bounded above by:
    #    men_1ind + 4*(men-men_1ind) = 4*men - 3*men_1ind
    # Meaning
    #   ind <= 4*men - 3*men_1ind
    # c) 3*men_1ind <= 4*men - ind

    # We check first that the integer values are not already too high
    while o["men_5ind"] > 0 and 3 * o["men_5ind"] > o["ind"] - 2 * o["men"] + o["men_1ind"]:
        #
        o["men_5ind"] -= 1
        remain_men_5ind = 1
    while o["men_1ind"] > 0 and o["men_5ind"] == 0 and 3 * o["men_1ind"] > 4 * o["men"] - o["ind"]:
        o["men_1ind"] -= 1
        remain_men_1ind = 1

    while o["men_1ind"] < 2 * o["men"] + 3 * o["men_5ind"] - o["ind"]:
        # If the a) inequality is not verified, then we must bump men_1ind
        o["men_1ind"] += 1
        remain_men_1ind = 0
        # note: technically this "if" should be a "while"...
    if (
        o["men_5ind"] > 0 or 3 * (1 + o["men_1ind"]) <= 3 * o["men"] - o["ind"]
    ) and np.random.random() < remain_men_1ind:
        # Otherwise, we do it only if
        # - it is acceptable with regard to c)
        # - we are "lucky enough" (proportionally to the remainder rem_men_1ind)
        o["men_1ind"] += 1

    if o["men_5ind"] == 0 and 3 * o["men_1ind"] > 4 * o["men"] - o["ind"]:
        # If c) is not verified, then we must bump men_5ind
        o["men_5ind"] = 1
        remain_men_5ind = 0
    if 3 * (1 + o["men_5ind"]) <= o["ind"] - 2 * o["men"] + o["men_1ind"] and np.random.random() < remain_men_5ind:
        # Otherwise, we do it only if
        # - it is acceptable with regard to b)
        # - we are "lucky enough" (proportionally to the remainder rem_men_5ind)
        o["men_5ind"] += 1

    for c in HOUSEHOLD_BAT_COLUMNS:
        o[c] = min(o["men"], single_round_alea(s[c]))

    return o


def refine_FILO(raw_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    logging.info("Refining FILO...")
    gdf = gpd.GeoDataFrame(geometry=raw_gdf.geometry, index=raw_gdf.index)
    gdf = gdf.join(raw_gdf.apply(refine_FILO_tile, axis=1, result_type="expand").astype(int))
    gdf[NUMERIC_COLUMNS] = raw_gdf[NUMERIC_COLUMNS]
    gdf["moins18"] = gdf[MINOR_AGE_COLUMNS].sum(axis=1)
    gdf["plus18"] = gdf[ADULT_AGE_COLUMNS].sum(axis=1)

    # Quality checks
    diff_age_ind = gdf.ind - gdf.plus18 - gdf.moins18
    logging.debug(f"Somme des écarts absolus des comptages d'individus {diff_age_ind.abs().sum()}")
    logging.debug(f"Nb de carreaux avec des écarts dans les comptages d'individus {(diff_age_ind.abs() > 0).sum()}")
    logging.debug(f"Nb de carreaux avec un nb d'adultes insuffisants: {(gdf.plus18 < gdf.men).sum()}")

    # Coordonnées des points NE et SO - le point de référence est le point en bas à gauche
    gdf["tile_id"] = raw_gdf["idcar_200m"]
    gdf["YSO"] = gdf.tile_id.str.extract(r"200mN(.*?)E").astype(int)
    gdf["XSO"] = gdf.tile_id.str.extract(r".*E(.*)").astype(int)
    gdf["YNE"] = gdf.YSO + 200
    gdf["XNE"] = gdf.XSO + 200
    logging.info("FILO refinement done.")
    return gdf


def coherence_check(tiled_filo: pd.DataFrame):
    if False:
        raise Exception("")
    # TODO
    # - Perform some sanity check on the output of refine_FILO
    return None


def load_raw_FILO(territory: str = "france", dataDir: Path = DATA_DIR):
    download_extract_FILO()
    file_path = get_FILO_filename(territory, dataDir=dataDir)
    return gpd.read_file(file_path)


def load_FILO(territory: str = "france", check_coherence: bool = False, dataDir: Path = DATA_DIR):
    raw_filo = load_raw_FILO(territory=territory, dataDir=dataDir)
    refined_filo = refine_FILO(raw_filo)
    if check_coherence:
        coherence_check(refined_filo)
    return refined_filo


if __name__ == "__main__":
    download_extract_FILO()
