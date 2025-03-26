import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal, TypedDict

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

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


class PopulationFeature(TypedDict):
    geometry: Point
    ID: str
    HOUSEHOLD_ID: str
    TILE_ID: str
    HOUSEHOLD_SIZE: int
    GRD_MENAGE: bool
    MONOPARENT: bool
    NIVEAU_VIE: float
    AGE_CAT: str
    AGE: int
    ADULT: bool
    STATUT: str


class HouseholdsFeature(TypedDict):
    geometry: Point
    ID: str
    TILE_ID: str
    SIZE: int
    NB_ADULTS: int
    NB_MINORS: int
    GRD_MENAGE: bool
    MONOPARENT: bool
    NIVEAU_VIE: float
    ind_0_3: int
    ind_4_5: int
    ind_6_10: int
    ind_11_17: int
    ind_18_24: int
    ind_25_39: int
    ind_40_54: int
    ind_55_64: int
    ind_65_79: int
    ind_80p: int
    ind_inc: int


population_dtype: Mapping[Any, pd._typing.Dtype] = {
    "geometry": "geometry",
    "ID": "string",
    "HOUSEHOLD_ID": "string",
    "TILE_ID": "string",
    "HOUSEHOLD_SIZE": np.int64,
    "GRD_MENAGE": "boolean",
    "MONOPARENT": "boolean",
    "NIVEAU_VIE": np.float64,
    "AGE_CAT": "string",
    "AGE": np.int64,
    "ADULT": "boolean",
    "STATUT": "string",
}

households_dtype: Mapping[Any, pd._typing.Dtype] = {
    "geometry": "geometry",
    "ID": "string",
    "TILE_ID": "string",
    "SIZE": np.int64,
    "NB_ADULTS": np.int64,
    "NB_MINORS": np.int64,
    "GRD_MENAGE": "boolean",
    "MONOPARENT": "boolean",
    "NIVEAU_VIE": np.float64,
    "ind_0_3": np.int64,
    "ind_4_5": np.int64,
    "ind_6_10": np.int64,
    "ind_11_17": np.int64,
    "ind_18_24": np.int64,
    "ind_25_39": np.int64,
    "ind_40_54": np.int64,
    "ind_55_64": np.int64,
    "ind_65_79": np.int64,
    "ind_80p": np.int64,
    "ind_inc": np.int64,
}


def mkHouseholdsDataFrame(data, territory: TerritoryCode):
    return gpd.GeoDataFrame(data=data, geometry="geometry", crs=territory_crs(territory)).astype(
        dtype=households_dtype, copy=False
    )


def mkPopulationDataFrame(data, territory: TerritoryCode):
    return gpd.GeoDataFrame(data=data, geometry="geometry", crs=territory_crs(territory)).astype(
        dtype=population_dtype, copy=False
    )


households_gpkg_schema = {
    "geometry": {"type": "Geometry", "geometry_type": "Point"},
    "ID": {"type": "String"},
    "TILE_ID": {"type": "String"},
    "SIZE": {"type": "Integer"},
    "NB_ADULTS": {"type": "Integer"},
    "NB_MINORS": {"type": "Integer"},
    "GRD_MENAGE": {"type": "Boolean"},
    "MONOPARENT": {"type": "Boolean"},
    "NIVEAU_VIE": {"type": "Real"},
    "ind_0_3": {"type": "Integer"},
    "ind_4_5": {"type": "Integer"},
    "ind_6_10": {"type": "Integer"},
    "ind_11_17": {"type": "Integer"},
    "ind_18_24": {"type": "Integer"},
    "ind_25_39": {"type": "Integer"},
    "ind_40_54": {"type": "Integer"},
    "ind_55_64": {"type": "Integer"},
    "ind_65_79": {"type": "Integer"},
    "ind_80p": {"type": "Integer"},
    "ind_inc": {"type": "Integer"},
}

population_gpkg_schema = {
    "geometry": {"type": "Geometry", "geometry_type": "Point"},
    "ID": {"type": "String"},
    "HOUSEHOLD_ID": {"type": "String"},
    "TILE_ID": {"type": "String"},
    "HOUSEHOLD_SIZE": {"type": "Integer"},
    "GRD_MENAGE": {"type": "Boolean"},
    "MONOPARENT": {"type": "Boolean"},
    "NIVEAU_VIE": {"type": "Real"},
    "AGE_CAT": {"type": "String"},
    "AGE": {"type": "Integer"},
    "ADULT": {"type": "Boolean"},
    "STATUT": {"type": "String"},
}
