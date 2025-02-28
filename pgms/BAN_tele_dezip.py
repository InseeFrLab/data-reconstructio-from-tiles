import gzip
import logging
import shutil
from pathlib import Path

import requests

from .utils import DATA_DIR

# URL du fichier de la base d'adresses nationale
BAN_DEFAULT_URL = "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-france.csv.gz"


def download_extract_BAN(url: str = BAN_DEFAULT_URL, dataDir: Path = DATA_DIR) -> None:
    logging.info("Downloading and extracting BAN resources")

    if not dataDir.exists():
        logging.info("Creating data folder")
        dataDir.mkdir(exist_ok=True)

    # Chemin complet du fichier à télécharger
    file_path = dataDir / "adresses.csv.gz"
    # Chemin du fichier décompressé
    decompressed_file_path = dataDir / "adresses.csv"

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

    # GFY: is this step necessary ? pandas is able to read compressed csv.gz directly
    logging.info("Extracting from gunzip file")
    with gzip.open(file_path, "rb") as f_in, open(decompressed_file_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

    logging.info(f"BAN data successfully extracted and saved in {decompressed_file_path}")


if __name__ == "__main__":
    download_extract_BAN()
