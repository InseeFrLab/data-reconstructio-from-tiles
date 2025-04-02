from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypedDict

import numpy as np
import pandas as pd
import yaml
from shapely.geometry import Point


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

# SmartNoise style metadata : https://docs.smartnoise.org/sql/metadata.html#table-options
households_smartnoise_columns = {
    "ID": {
        "type": "string",
        "private_id": True,
        "nullable": False,
    },
    "TILE_ID": {
        "type": "string",
        "nullable": False,
    },
    "SIZE": {
        "type": "int",
        "precision": 64,
        "lower": 0,
        "upper": 500,
        "nullable": False,
    },
    "NB_ADULTS": {
        "type": "int",
        "precision": 64,
        "lower": 0,
        "upper": 500,
        "nullable": False,
    },
    "NB_MINORS": {
        "type": "int",
        "precision": 64,
        "lower": 0,
        "upper": 500,
        "nullable": False,
    },
    "GRD_MENAGE": {
        "type": "boolean",
        "nullable": False,
    },
    "MONOPARENT": {
        "type": "boolean",
        "nullable": False,
    },
    "NIVEAU_VIE": {
        "type": "float",
        "precision": 64,
        "lower": 0,
        "upper": 1_000_000_000,
        "nullable": False,
    },
    "ind_0_3": {
        "type": "int",
        "precision": 64,
        "lower": 0,
        "upper": 500,
        "nullable": False,
    },
    "ind_4_5": {
        "type": "int",
        "precision": 64,
        "lower": 0,
        "upper": 500,
        "nullable": False,
    },
    "ind_6_10": {
        "type": "int",
        "precision": 64,
        "lower": 0,
        "upper": 500,
        "nullable": False,
    },
    "ind_11_17": {
        "type": "int",
        "precision": 64,
        "lower": 0,
        "upper": 500,
        "nullable": False,
    },
    "ind_18_24": {
        "type": "int",
        "precision": 64,
        "lower": 0,
        "upper": 500,
        "nullable": False,
    },
    "ind_25_39": {
        "type": "int",
        "precision": 64,
        "lower": 0,
        "upper": 500,
        "nullable": False,
    },
    "ind_40_54": {
        "type": "int",
        "precision": 64,
        "lower": 0,
        "upper": 500,
        "nullable": False,
    },
    "ind_55_64": {
        "type": "int",
        "precision": 64,
        "lower": 0,
        "upper": 500,
        "nullable": False,
    },
    "ind_65_79": {
        "type": "int",
        "precision": 64,
        "lower": 0,
        "upper": 500,
        "nullable": False,
    },
    "ind_80p": {
        "type": "int",
        "precision": 64,
        "lower": 0,
        "upper": 500,
        "nullable": False,
    },
    "ind_inc": {
        "type": "int",
        "precision": 64,
        "lower": 0,
        "upper": 500,
        "nullable": False,
    },
}

# SmartNoise style metadata : https://docs.smartnoise.org/sql/metadata.html#table-options
population_smartnoise_columns = {
    "ID": {
        "type": "string",
        "private_id": True,
        "nullable": False,
    },
    "HOUSEHOLD_ID": {
        "type": "string",
        "nullable": False,
    },
    "TILE_ID": {
        "type": "string",
        "nullable": False,
    },
    "HOUSEHOLD_SIZE": {
        "type": "int",
        "nullable": False,
    },
    "GRD_MENAGE": {
        "type": "boolean",
        "nullable": False,
    },
    "MONOPARENT": {
        "type": "boolean",
        "nullable": False,
    },
    "NIVEAU_VIE": {
        "type": "float",
        "lower": 0,
        "upper": 1_000_000_000,
        "nullable": False,
    },
    "AGE_CAT": {
        "type": "string",
        "cardinality": 11,
        "categories": [
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
        ],
        "nullable": False,
    },
    "AGE": {
        "type": "int",
        "lower": 0,
        "upper": 105,
        "nullable": False,
    },
    "ADULT": {
        "type": "boolean",
        "nullable": False,
    },
    "STATUT": {
        "type": "string",
        "cardinality": 2,
        "categories": [
            "ADULT",
            "MINOR",
        ],
        "nullable": False,
    },
}


def save_households_metadata(file: Path, nb_rows: int | None = None):
    data = {
        "max_ids": 1,
        "row_privacy": True,
        "censor_dims": False,
        "columns": households_smartnoise_columns,
    }
    if nb_rows is not None:
        data["rows"] = nb_rows
    with open(file, "w") as outfile:
        yaml.dump(data, outfile, sort_keys=False, default_flow_style=False)


def save_population_metadata(file: Path, nb_rows: int | None = None):
    data = {
        "max_ids": 1,
        "row_privacy": True,
        "censor_dims": False,
        "columns": population_smartnoise_columns,
    }
    if nb_rows is not None:
        data["rows"] = nb_rows
    with open(file, "w") as outfile:
        yaml.dump(data, outfile, sort_keys=False, default_flow_style=False)
