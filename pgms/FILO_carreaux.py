import logging
import zipfile
from pathlib import Path

import py7zr
import requests

from .utils import DATA_DIR

# URL par défaut du fichier à télécharger
FILO_DEFAULT_URL: str = "https://www.insee.fr/fr/statistiques/fichier/7655475/Filosofi2019_carreaux_200m_gpkg.zip"


def download_extract_FILO(url: str = FILO_DEFAULT_URL, dataDir: Path = DATA_DIR) -> None:
    logging.info("Downloading FILO resources")

    if not dataDir.exists():
        logging.info("Creating data folder")
        dataDir.mkdir(exist_ok=True)

    # Chemin pour enregistrer le fichier zip téléchargé
    zip_path: Path = dataDir / "carreaux_200m.7z"
    # Chemin pour enregistrer le fichier 7z téléchargé
    seven_zip_path = dataDir / "Filosofi2019_carreaux_200m_gpkg.7z"

    logging.info(f"Downloading data file from {url}")
    response = requests.get(url)
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


if __name__ == "__main__":
    download_extract_FILO()
