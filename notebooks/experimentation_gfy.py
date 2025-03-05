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


# %%
ban = load_BAN("974")
print(f"Loaded BAN database: {ban.shape[0]} lines, {ban.shape[1]} columns")


# %%
def build_population(tile: pd.Series, addresses: pd.DataFrame):
    # Create a single fake address if no addresses are found in the tile
    if addresses.empty:
        addresses = pd.DataFrame([{
            "x": tile["XSO"] + (tile["XNE"] - tile["XSO"]) * 0.5, # or use random.random()
            "y": tile["YSO"] + (tile["YNE"] - tile["YSO"]) * 0.5, # or use random.random()
            "tile_id": tile["tile_id"]
        }])
    # Dummy implem: one individual per address, regardless of tile info
    data = [
        {
            "x": addr.x,
            "y": addr.y,
            "tile_id": tile["tile_id"]
        }
        for _, addr in addresses.iterrows()
    ]
    # TODO:
    # - replace data definition with actual tile population generation algo
    return pd.DataFrame(data)

result = merge_FILO_BAN(build_population, filo_df=filo, ban_df=ban)
print(f"Merged FILO BAN to produce pop database: {result.shape[0]} lines, {result.shape[1]} columns")


# %%
fig, ax = plt.subplots(1, 1, figsize=(10, 10))
filo.plot(column="ind", ax=ax, legend=True, cmap="OrRd", legend_kwds={"label": "Population par carreau"})
plt.title("Carte de la population par carreaux")
