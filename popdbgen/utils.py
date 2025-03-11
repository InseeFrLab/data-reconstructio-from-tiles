import logging
from pathlib import Path

import numpy as np
import pandas as pd

# Path vers la racine du projet
PROJECT_DIR: Path = Path(__file__).resolve().parents[1]
# Répertoire pour enregistrer le fichier téléchargé
DATA_DIR: Path = PROJECT_DIR / "data"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%Y-%m-%d %I:%M:%S %p")


def round_alea(x: pd.Series) -> pd.Series:
    """
    If X = I + D (I natural, 0 <= D < 1),
    then returns I+1 with probability D and I with probablity 1-D
    """
    i, d = divmod(x, 1)
    return (i + (np.random.rand(len(x)) < d)).astype(int)


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
