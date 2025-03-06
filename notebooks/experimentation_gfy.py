# %%
import sys
import time
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from popdbgen import DATA_DIR, load_FILO, load_BAN, merge_FILO_BAN

np.random.seed(1703)


# %%
filo = load_FILO("974")
print(f"Loaded FILO database: {filo.shape[0]} lines, {filo.shape[1]} columns")
print(f"Total households: {filo.meni.sum()}")
print(f"Total population: {filo.indi.sum()}")
print(f"Total adults: {filo.plus18i.sum()} ({filo.plus18i.sum()/filo.indi.sum():.2%})")


# %%
ban = load_BAN("974")
print(f"Loaded BAN database: {ban.shape[0]} lines, {ban.shape[1]} columns")
print(f"Non empty tiles: {ban.tile_id.nunique()}")


# %%
def build_population(tile: pd.Series, addresses: pd.DataFrame):
    # (Should not happen) If no households expected, then return empty list
    if tile.meni == 0:
        return []
    # Create a single fake address if no addresses are found in the tile
    if addresses.empty:
        addresses = pd.DataFrame([{
            "x": tile.XSO + (tile.XNE - tile.XSO) * 0.5, # or replace 0.5 with np.random.rand() ?
            "y": tile.YSO + (tile.YNE - tile.YSO) * 0.5, # or replace 0.5 with np.random.rand() ?
            "tile_id": tile.tile_id
        }])
    # if less households than addresses, keep only as many as there are households
    # Note: the addresses were already shuffled beforehand so there should be no bias
    addresses = addresses[:int(tile.meni)]
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
            "x": addresses.loc[ (i % tile.meni) % len(addresses.index) ].x,
            "y": addresses.loc[ (i % tile.meni) % len(addresses.index) ].y
        }
        for i in range(int(tile.indi))
    ]
    # TODO:
    # - replace data definition with actual tile population generation algo
    return data

pop_database = merge_FILO_BAN(build_population, filo_df=filo, ban_df=ban)
print(f"Merged FILO BAN to produce pop database: {pop_database.shape[0]} lines, {pop_database.shape[1]} columns")


# %%
fig, ax = plt.subplots(1, 1, figsize=(10, 10))
filo.plot(column="ind", ax=ax, legend=True, cmap="OrRd", legend_kwds={"label": "Population par carreau"})
plt.title("Carte de la population par carreaux")

# %%
pop_gdf = gpd.GeoDataFrame(
    pop_database, geometry=gpd.points_from_xy(pop_database.x, pop_database.y), crs="EPSG:2975"
)

# %%
fig, ax = plt.subplots(1, 1, figsize=(15, 15))
pop_gdf.plot(markersize=0.2, ax=ax, legend=True)
plt.title("Generated population database")

# %%
