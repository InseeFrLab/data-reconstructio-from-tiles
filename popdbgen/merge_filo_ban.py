from collections.abc import Callable, Generator

import geopandas as gpd
import pandas as pd

from .download_ban import load_BAN
from .download_filo import load_FILO
from .households_tile_generation import generate_households


# Fonction de test
def test(reduce_f: Callable[[pd.Series, pd.DataFrame], pd.DataFrame]):
    # TODO
    # - Build dummy FILO tile Series and BAN addresses dataframe
    # - Call "reduce_f" on it
    # - Implement some sanity check on the output
    pass


def merge_FILO_BAN(
    reduce_f: Callable[[pd.Series, pd.DataFrame], Generator[dict]] = generate_households,
    filo_df: gpd.GeoDataFrame | None = None,
    ban_df: pd.DataFrame | None = None,
    territory: str = "france",
    tile_id_column: str = "tile_id",
) -> pd.DataFrame:
    """
    Args:
        reduce_f (function): Function to generate DataFrame from a row of the filo_df
            and a DataFrame of all corresponding addresses in ban_df
        filo_df (GeoDataFrame, optional): GeoDataFrame containing FILO tile information
        ban_df (DataFrame, optional): DataFrame containing addresses
        territory (str, optional): Name of the territory (used to load data)
    Returns:
        GeoDataFrame: Un GeoDataFrame contenant les points situés dans les polygones,
                      avec les colonnes x, y, geometry (points) et la colonne identifiant les polygones.
    """
    filo: pd.DataFrame = load_FILO(territory) if filo_df is None else filo_df
    ban: pd.DataFrame = load_BAN(territory) if ban_df is None else ban_df
    tiled_ban = ban.groupby(tile_id_column, sort=False)

    # Function to apply reduce_f to a given row and to each addresses matching it
    def process_tile(tile: pd.Series) -> Generator[dict]:
        idcar = tile[tile_id_column]
        if idcar in tiled_ban.groups:
            addresses = tiled_ban.get_group(idcar).sample(frac=1).reset_index(drop=True)
        else:
            addresses = pd.DataFrame(columns=ban.columns)
        return reduce_f(tile, addresses)

    return pd.DataFrame([pop_row for _, row in filo.iterrows() for pop_row in process_tile(row)])
