#!/usr/bin/env python3
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .utils import DATA_DIR

# Template d'URL du fichier de la base d'adresses nationale (BAN)
BAN_TEMPLATE_URL = "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-{}.csv.gz"
BAN_FILENAME_TEMPLATE = "adresses-{}.csv.gz"


def get_BAN_URL(territory: str = "france") -> str:
    """
    Returns the URL linking to the open data BAN file.
    """
    return BAN_TEMPLATE_URL.format(territory)


def download_BAN(territory: str = "france", dataDir: Path = DATA_DIR, overwriteIfExists: bool = False) -> Path:
    """
    Downloads the open data BAN file for argument territory.
    Returns the pathlib.Path to the saved file.
    """
    logging.info("Downloading and extracting BAN file...")

    if not dataDir.exists():
        logging.info("Creating data folder")
        dataDir.mkdir(exist_ok=True)

    # Chemin complet du fichier à télécharger
    file_path = dataDir / f"adresses-{territory}.csv.gz"

    if file_path.is_file():
        if overwriteIfExists:
            logging.info("Overwriting already existing data file")
        else:
            logging.info("Data file already exists, skipping download")
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


def load_BAN(territory: str = "france") -> pd.DataFrame:
    # Download
    ban_file = download_BAN(territory)

    epsg = "2154"
    if territory == "974":
        epsg = "2975"
    # TODO
    # - Finish this to handle all other territories

    ban = pd.read_csv(ban_file, sep=";", usecols=["x", "y"])

    # A adapter en fonction du CRS
    # TODO:
    # - Check that the tile_id format forllow that same template in FILO for all territories
    ban["tile_id"] = (
        f"CRS{epsg}RES200mN"
        + (200 * np.floor(ban.y / 200).astype(int)).astype(str)
        + "E"
        + (200 * np.floor(ban.x / 200).astype(int)).astype(str)
    )

    return ban


if __name__ == "__main__":
    download_BAN()
