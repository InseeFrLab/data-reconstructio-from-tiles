#!/usr/bin/env python3
import logging
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import py7zr
import requests

from .utils import DATA_DIR

# URL par défaut du fichier à télécharger
FILO_URL: str = "https://www.insee.fr/fr/statistiques/fichier/7655475/Filosofi2019_carreaux_200m_gpkg.zip"


def get_FILO_filename(territory: str | int = "france", dataDir: Path = DATA_DIR) -> Path:
    territory = str(territory).lower()
    if territory in ("france", "met", "metro"):
        return dataDir / "carreaux_200m_met.gpkg"
    elif territory in ("972", "martinique", "mart"):
        return dataDir / "carreaux_200m_mart.gpkg"
    elif territory in ("974", "reunion", "reun", "reu"):
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


def round_alea(x: pd.Series):
    xfl = np.floor(x).astype("int")
    return xfl + (np.random.rand(x.size) < x - xfl)


def refine_FILO(gdf: gpd.GeoDataFrame, territory: str | int = "france", coherence_check: bool = False) -> pd.DataFrame:
    gdf.rename(columns={"idcar_200m": "tile_id"}, inplace=True)

    gdf["indi"] = round_alea(gdf.ind)

    # plus18: at least 1 and no more than indi
    gdf["plus18i"] = np.maximum(
        1,
        np.minimum(
            gdf.indi,
            round_alea(gdf.ind_18_24 + gdf.ind_25_39 + gdf.ind_40_54 + gdf.ind_55_64 + gdf.ind_65_79 + gdf.ind_80p),
        ),
    )
    gdf["moins18i"] = gdf.indi - gdf.plus18i
    # meni: at least 1 and no more than plus18i
    gdf["meni"] = np.maximum(1, np.minimum(gdf.plus18i, round_alea(gdf.men)))

    # Coordonnées des points NE et SO - le point de référence est le point en bas à gauche
    gdf["YSO"] = gdf["tile_id"].str.extract(r"200mN(.*?)E").astype(int)
    gdf["XSO"] = gdf["tile_id"].str.extract(r".*E(.*)").astype(int)
    gdf["YNE"] = gdf["YSO"] + 200
    gdf["XNE"] = gdf["XSO"] + 200

    # TODO
    # - preprocess more columns from FILO (age categories, revenue, etc.)
    # - cleanup: remove original columns with little interest
    # - (optional) return a fresh GeoDataFrame copy rather than edit in place
    return gdf


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
