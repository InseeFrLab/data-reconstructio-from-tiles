from collections.abc import Callable

import geopandas as gpd
import pandas as pd

from .download_ban import load_BAN
from .download_filo import load_FILO


def build_population(tile: pd.Series, addresses: pd.DataFrame) -> list[dict]:
    # (Should not happen) If no households expected, then return empty list
    if tile.meni == 0:
        return []
    # Create a single fake address if no addresses are found in the tile
    if addresses.empty:
        addresses = pd.DataFrame(
            [
                {
                    "x": tile.XSO + (tile.XNE - tile.XSO) * 0.5,  # or replace 0.5 with np.random.rand() ?
                    "y": tile.YSO + (tile.YNE - tile.YSO) * 0.5,  # or replace 0.5 with np.random.rand() ?
                    "tile_id": tile.tile_id,
                }
            ]
        )
    # if less households than addresses, keep only as many as there are households
    # Note: the addresses were already shuffled beforehand so there should be no bias
    addresses = addresses[: int(tile.meni)]
    # Dummy implem: one individual per address, regardless of tile info
    data = [
        {
            "tile_id": tile.tile_id,
            # Househods are numerotated for 0 to tile.meni-1
            # Individuals are dispatched in each households in that order
            "men_id": i % tile.meni,
            # The first plus18i individuals are adults
            # note: there should be at least one in each household since plus18i <= meni
            "adult": i > tile.plus18i,
            # Location is found at position men_id in the adress list
            # (so that individuals sharing the same household have the same loc)
            "x": addresses.loc[(i % tile.meni) % len(addresses.index)].x,
            "y": addresses.loc[(i % tile.meni) % len(addresses.index)].y,
        }
        for i in range(int(tile.indi))
    ]
    # TODO:
    # - replace data definition with actual tile population generation algo
    return data


# Fonction de test
def test(reduce_f: Callable[[pd.Series, pd.DataFrame], pd.DataFrame]):
    # TODO
    # - Build dummy FILO tile Series and BAN addresses dataframe
    # - Call "reduce_f" on it
    # - Implement some sanity check on the output
    pass


def merge_FILO_BAN(
    reduce_f: Callable[[pd.Series, pd.DataFrame], list[dict]] = build_population,
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

    print(tiled_ban)

    # Function to apply reduce_f to a given row and to each addresses matching it
    def process_tile(tile: pd.Series) -> list[dict]:
        idcar = tile[tile_id_column]
        if idcar in tiled_ban.groups:
            addresses = tiled_ban.get_group(idcar).sample(frac=1).reset_index(drop=True)
        else:
            addresses = pd.DataFrame(columns=ban.columns)
        return reduce_f(tile, addresses)

    return pd.DataFrame([pop_row for _, row in filo.iterrows() for pop_row in process_tile(row)])
