# from .build_population import generate_individuals
from .download_ban import download_BAN, get_BAN_URL, load_BAN
from .download_filo import (
    ADULT_AGE_COLUMNS,
    ALL_AGE_COLUMNS,
    MINOR_AGE_COLUMNS,
    download_extract_FILO,
    get_FILO_filename,
    load_FILO,
    load_raw_FILO,
    refine_FILO,
)
from .households_gen import (
    generate_batched_households,
    generate_households,
    get_batched_households_gdf,
    get_batched_households_population_gdf,
    get_batched_population_gdf,
    get_households_gdf,
    get_households_population_gdf,
    get_population_gdf,
)
from .utils import (
    DATA_DIR,
    PROJECT_DIR,
    TerritoryCode,
    filo_crs,
    filo_epsg,
    households_gpkg_schema,
    population_gpkg_schema,
    round_alea,
    territory_code,
    territory_crs,
    territory_epsg,
)

__all__ = [
    # utils
    "DATA_DIR",
    "PROJECT_DIR",
    "TerritoryCode",
    "territory_code",
    "filo_epsg",
    "filo_crs",
    "territory_epsg",
    "territory_crs",
    "households_gpkg_schema",
    "population_gpkg_schema",
    "round_alea",
    # download BAN data source
    "download_BAN",
    "get_BAN_URL",
    "load_BAN",
    # download FILO data source
    "get_FILO_filename",
    "download_extract_FILO",
    "refine_FILO",
    "load_FILO",
    "MINOR_AGE_COLUMNS",
    "ADULT_AGE_COLUMNS",
    "ALL_AGE_COLUMNS",
    "load_raw_FILO",
    # Households generation (merging FILO <-> BAN)
    "generate_households",
    "get_households_gdf",
    "get_population_gdf",
    "get_households_population_gdf",
    "generate_batched_households",
    "get_batched_households_gdf",
    "get_batched_population_gdf",
    "get_batched_households_population_gdf",
]
