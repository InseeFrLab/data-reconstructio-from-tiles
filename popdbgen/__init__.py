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
    generate_households,
    get_households_gdf,
    get_households_population_gdf,
    get_population_gdf,
)
from .utils import DATA_DIR, PROJECT_DIR, round_alea, territory_code, territory_crs, territory_epsg

__all__ = [
    # utils
    "DATA_DIR",
    "PROJECT_DIR",
    "territory_code",
    "territory_epsg",
    "territory_crs",
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
]
