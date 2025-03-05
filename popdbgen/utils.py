import logging
from pathlib import Path

# Path vers la racine du projet
PROJECT_DIR: Path = Path(__file__).resolve().parents[1]
# Répertoire pour enregistrer le fichier téléchargé
DATA_DIR: Path = PROJECT_DIR / "data"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%Y-%m-%d %I:%M:%S %p")
