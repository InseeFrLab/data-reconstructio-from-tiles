import logging
from pathlib import Path
from typing import Literal

import geopandas as gpd
import numpy as np
import pandas as pd

from .metadata import households_dtype, population_dtype

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


TerritoryCode = Literal["france", "972", "974"]


def territory_code(territory: str | int) -> TerritoryCode:
    territory = str(territory).lower()
    if territory in ("france", "met", "metro"):
        return "france"
    elif territory in ("972", "martinique", "mart"):
        return "972"
    elif territory in ("974", "reunion", "reun", "reu"):
        return "974"
    else:
        raise NameError(f"Territory not supported: {territory}")


territory_epsg: dict[TerritoryCode, int] = {
    "france": 2154,
    "974": 2975,
    "972": 2154,  # FIXME: implement proper EPSG
}

filo_epsg: dict[TerritoryCode, int] = {
    "france": 3035,
    "974": 2975,
    "972": 3035,  # FIXME: implement proper EPSG
}


def territory_crs(territory: TerritoryCode) -> str:
    return f"EPSG:{territory_epsg[territory]}"


def filo_crs(territory: TerritoryCode) -> str:
    return f"EPSG:{filo_epsg[territory]}"


ADULT_AGE_LITERAL = Literal["ind_18_24", "ind_25_39", "ind_40_54", "ind_55_64", "ind_65_79", "ind_80p", "ind_inc"]
MINOR_AGE_LITERAL = Literal["ind_0_3", "ind_4_5", "ind_6_10", "ind_11_17"]
ALL_AGE_LITERAL = Literal[
    "ind_0_3",
    "ind_4_5",
    "ind_6_10",
    "ind_11_17",
    "ind_18_24",
    "ind_25_39",
    "ind_40_54",
    "ind_55_64",
    "ind_65_79",
    "ind_80p",
    "ind_inc",
]

MINOR_AGE_COLUMNS: list[MINOR_AGE_LITERAL] = ["ind_0_3", "ind_4_5", "ind_6_10", "ind_11_17"]
ADULT_AGE_COLUMNS: list[ADULT_AGE_LITERAL] = [
    "ind_18_24",
    "ind_25_39",
    "ind_40_54",
    "ind_55_64",
    "ind_65_79",
    "ind_80p",
    "ind_inc",
]
ALL_AGE_COLUMNS: list[ALL_AGE_LITERAL] = MINOR_AGE_COLUMNS + ADULT_AGE_COLUMNS


age_categories: dict[ALL_AGE_LITERAL, tuple[bool, int, int]] = {
    # adult (T/F), min age, max age (included)
    "ind_0_3": (False, 0, 3),
    "ind_4_5": (False, 4, 5),
    "ind_6_10": (False, 6, 10),
    "ind_11_17": (False, 11, 17),
    "ind_18_24": (True, 18, 24),
    "ind_25_39": (True, 25, 39),
    "ind_40_54": (True, 40, 54),
    "ind_55_64": (True, 55, 64),
    "ind_65_79": (True, 65, 79),
    "ind_80p": (True, 80, 105),
    "ind_inc": (True, 18, 80),
}


def mkHouseholdsDataFrame(data, territory: TerritoryCode):
    return gpd.GeoDataFrame(data=data, geometry="geometry", crs=territory_crs(territory)).astype(
        dtype=households_dtype, copy=False
    )


def mkPopulationDataFrame(data, territory: TerritoryCode):
    return gpd.GeoDataFrame(data=data, geometry="geometry", crs=territory_crs(territory)).astype(
        dtype=population_dtype, copy=False
    )
