import logging
from pathlib import Path

# Path vers la racine du projet
PROJECT_DIR: Path = Path(__file__).resolve().parents[1]
# Répertoire pour enregistrer le fichier téléchargé
DATA_DIR: Path = PROJECT_DIR / "data"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%Y-%m-%d %I:%M:%S %p")


def territory_code(territory: str | int) -> str:
    territory = str(territory).lower()
    if territory in ("france", "met", "metro"):
        return "france"
    elif territory in ("972", "martinique", "mart"):
        return "972"
    elif territory in ("974", "reunion", "reun", "reu"):
        return "974"
    else:
        raise NameError(f"Territory not supported: {territory}")
