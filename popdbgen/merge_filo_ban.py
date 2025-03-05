from collections.abc import Callable

import geopandas as gpd
import pandas as pd

from .download_ban import load_BAN
from .download_filo import load_FILO


def build_population(tile: pd.Series, addresses: pd.DataFrame):
    # Create a single fake address if no addresses are found in the tile
    if addresses.empty:
        addresses = pd.DataFrame(
            [
                {
                    "x": tile["XSO"] + (tile["XNE"] - tile["XSO"]) * 0.5,  # or use random.random()
                    "y": tile["YSO"] + (tile["YNE"] - tile["YSO"]) * 0.5,  # or use random.random()
                    "tile_id": tile["tile_id"],
                }
            ]
        )
    # Dummy implem: one individual per address, regardless of tile info
    data = [{"x": addr.x, "y": addr.y, "tile_id": tile["tile_id"]} for _, addr in addresses.iterrows()]
    # TODO:
    # - replace data definition with actual tile population generation algo
    return pd.DataFrame(data)


# Fonction de test
def test(reduce_f: Callable[[pd.Series, pd.DataFrame], pd.DataFrame]):
    # TODO
    # - Build dummy FILO tile Series and BAN addresses dataframe
    # - Call "reduce_f" on it
    # - Implement some sanity check on the output
    pass


def merge_FILO_BAN(
    reduce_f: Callable[[pd.Series, pd.DataFrame], pd.DataFrame] = build_population,
    filo_df: gpd.GeoDataFrame | None = None,
    ban_df: pd.DataFrame | None = None,
    territory: str = "france",
    tile_id_column: str = "tile_id",
):
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
    def process_tile(tile):
        idcar = tile[tile_id_column]
        if idcar in tiled_ban.groups:
            addresses = tiled_ban.get_group(idcar).sample(frac=1).reset_index(drop=True)
        else:
            addresses = pd.DataFrame(columns=ban.columns)
        return reduce_f(tile, addresses)

    return pd.concat([process_tile(row) for _, row in filo.iterrows()], ignore_index=True)
