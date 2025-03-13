#!/usr/bin/env python3
import logging
from argparse import ArgumentParser
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from popdbgen import DATA_DIR, get_households_population_gdf, load_BAN, load_FILO, territory_epsg


def main(dataDir: Path = DATA_DIR, territory: str = "france", seed: int = 1703):
    np.random.seed(seed)

    logging.info("Loading FILO...")
    filo: pd.DataFrame = load_FILO(dataDir=dataDir, territory=territory)

    logging.info("Loading BAN...")
    ban: pd.DataFrame = load_BAN(dataDir=dataDir, territory=territory)

    fig, ax = plt.subplots(1, 1, figsize=(20, 20))
    filo.plot(column="ind", ax=ax, legend=True, cmap="OrRd", legend_kwds={"label": "Population par carreaux"})
    plt.title("Carte de la population par carreaux")
    plt.show()

    households, population = get_households_population_gdf(filo_df=filo, ban_df=ban)

    # Export
    households.to_file(dataDir / "households.gpkg", driver="GPKG", crs=f"EPSG:{territory_epsg(territory)}")
    population.to_file(dataDir / "population.gpkg", crs=f"EPSG:{territory_epsg(territory)}", driver="GPKG")


if __name__ == "__main__":
    argparser = ArgumentParser()
    argparser.add_argument(
        "-t",
        "--territory",
        dest="territory",
        type=str,
        help="""
        Territory to run on (france, 974, 972)
        """,
    )
    argparser.add_argument(
        "-d",
        "--datadir",
        dest="datadir",
        type=str,
        help="""
        Path to the data directory
        """,
    )
    argparser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        default=False,
        action="store_true",
        help="""
        Set logging level to DEBUG
        """,
    )
    argparser.add_argument(
        "-l",
        "--log",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        dest="loglevel",
        default="INFO",
        type=str.upper,
        help="""
        Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """,
    )
    # Parse arguments
    args = argparser.parse_args()
    # Setup logging level base on -v and -l flags
    logging.basicConfig(
        format="%(asctime)s %(message)s",
        datefmt="%Y-%m-%d %I:%M:%S %p",
        level="DEBUG" if args.verbose else args.loglevel,
    )
    # Run main program
    main(dataDir=Path(args.datadir) if args.datadir else DATA_DIR, territory=args.territory or "france")
