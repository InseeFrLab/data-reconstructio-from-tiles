# %%
# 1- Imports
import geopandas as gpd
import pandas as pd

from popdbgen import generate_households, load_FILO, load_BAN, merge_FILO_BAN


# %%
# Load FILO
filo: pd.DataFrame = load_FILO("974")
ban: pd.DataFrame = load_BAN("974")

# Debug
from popdbgen import get_FILO_filename
fil = gpd.read_file(get_FILO_filename("974"))

def debug(tile_id):
    return fil[fil["idcar_200m"] == tile_id].T, filo[filo["tile_id"] == tile_id].T


# %%
# Generate households database
full_hh_database = merge_FILO_BAN(generate_households, filo_df=filo, ban_df=ban)


# %%

def validate_households(households: pd.DataFrame, tile: pd.Series) -> bool:
    """
    Teste la cohérence d'une base de ménages générée sur un carreau avec les informations
    du carreau lui-même.
    """
    total_adults = int(sum(tile[ADULT_AGE_COLUMNS_INT]))
    total_minors = tile.ind - total_adults
    checks = {
        "TAILLE": households['TAILLE'].sum() == tile.ind,
        "NB_ADULTES": households['NB_ADULTES'].sum() == total_adults,
        "NB_MINEURS": households['NB_MINEURS'].sum() == total_minors,
        "MONOPARENT": households['MONOPARENT'].sum() == tile.men_fmp,
        "GRD_MENAGE": households['GRD_MENAGE'].sum() == tile.men_5ind
    }

    return all(checks.values())
