#!/usr/bin/env python3
import logging
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from popdbgen import DATA_DIR, load_BAN, load_FILO, merge_FILO_BAN


def main(data_dir: Path = DATA_DIR, territory: str = "france", seed: int = 1703):
    np.random.seed(seed)

    logging.info("Loading FILO...")
    filo: pd.DataFrame = load_FILO(data_dir=data_dir, territory=territory)

    logging.info("Loading BAN...")
    ban: pd.DataFrame = load_BAN(data_dir=data_dir, territory=territory)

    fig, ax = plt.subplots(1, 1, figsize=(20, 20))
    filo.plot(column="ind", ax=ax, legend=True, cmap="OrRd", legend_kwds={"label": "Population par carreaux"})
    plt.title("Carte de la population par carreaux")
    plt.show()

    full_hh_database = merge_FILO_BAN(filo_df=filo, ban_df=ban)

    geometry = gpd.points_from_xy(full_hh_database.x, full_hh_database.y)
    hh_gdf = gpd.GeoDataFrame(full_hh_database, geometry=geometry)

    # Plot the density maps side by side
    fig, ax = plt.subplots(1, 1, figsize=(20, 20))

    # Plot the density map from the individuals table
    hh_gdf.plot(ax=ax, markersize=0.2, alpha=0.5)
    ax.set_title("Carte de densité de population (ménages)")
    plt.show()

    # Export
    hh_gdf.to_file("data/individus_gdf.gpkg", driver="GPKG")


if __name__ == "__main__":
    main()
