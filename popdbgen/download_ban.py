#!/usr/bin/env python3
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from pyproj import Transformer

from .utils import DATA_DIR, TerritoryCode, filo_crs, filo_epsg, territory_code, territory_crs

# Template d'URL du fichier de la base d'adresses nationale (BAN)
BAN_TEMPLATE_URL = "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-{}.csv.gz"
BAN_FILENAME_TEMPLATE = "adresses-{}.csv.gz"


def get_BAN_URL(territory: str | int = "france") -> str:
    """
    Returns the URL linking to the open data BAN file.
    """
    return BAN_TEMPLATE_URL.format(territory_code(territory))


def download_BAN(territory: str | int = "france", dataDir: Path = DATA_DIR, overwriteIfExists: bool = False) -> Path:
    """
    Downloads the open data BAN file for argument territory.
    Returns the pathlib.Path to the saved file.
    """
    logging.info("Downloading and extracting BAN file...")

    if not dataDir.exists():
        logging.info("Creating data folder")
        dataDir.mkdir(exist_ok=True)

    # Chemin complet du fichier à télécharger
    file_path = dataDir / f"adresses-{territory_code(territory)}.csv.gz"

    if file_path.is_file():
        if overwriteIfExists:
            logging.info("Overwriting already existing data file")
        else:
            logging.info("Data file already exists, skipping download.")
            return file_path

    url = get_BAN_URL(territory)
    logging.info(f"Downloading BAN data from {url}")
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(file_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        logging.info(f"File successfully downloaded and saved in {file_path}")
    else:
        error_msg = f"BAN download fail! Response status: {response.status_code}"
        logging.error(error_msg)
        raise ConnectionError(error_msg)
    logging.info(f"BAN data successfully downloaded and saved in {file_path}")
    return file_path


def load_BAN(
    territory: str | int = "france", dataDir: Path = DATA_DIR, overwriteIfExists: bool = False
) -> pd.DataFrame:
    # Download
    terr_code: TerritoryCode = territory_code(territory)
    ban_file = download_BAN(territory=terr_code, dataDir=dataDir, overwriteIfExists=overwriteIfExists)

    ban = pd.read_csv(ban_file, sep=";", usecols=["x", "y"])

    transformer = Transformer.from_crs(territory_crs(terr_code), filo_crs(terr_code), always_xy=True)
    x, y = transformer.transform(ban.x, ban.y)

    ban["tile_id"] = (
        f"CRS{filo_epsg[terr_code]}RES200mN"
        + (200 * np.floor(y / 200).astype(int)).astype(str)
        + "E"
        + (200 * np.floor(x / 200).astype(int)).astype(str)
    )

    return ban


if __name__ == "__main__":
    download_BAN()
