#!/usr/bin/env python3
import logging
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

from popdbgen import (
    DATA_DIR,
    get_batched_households_population_gdf,
    households_gpkg_schema,
    load_BAN,
    load_FILO,
    population_gpkg_schema,
)


def generate_households_population_databases(
    territory: str = "france",
    dataDir: Path = DATA_DIR,
    seed: int = 1703,
    batchSize: int = 1000,
):
    np.random.seed(seed)

    filo: pd.DataFrame = load_FILO(dataDir=dataDir, territory=territory)
    ban: pd.DataFrame = load_BAN(dataDir=dataDir, territory=territory)

    households_output_file = dataDir / f"households_{territory}.gpkg"
    population_output_file = dataDir / f"population_{territory}.gpkg"
    logging.info(f"Exporting households to {households_output_file}")
    logging.info(f"Exporting population to {population_output_file}")

    nb_households = int(filo.men.sum())
    logging.info(f"Number of households to process: {nb_households}")

    nb_batches = 1 + (nb_households - 1) // batchSize

    batches = get_batched_households_population_gdf(batch_size=batchSize, filo_df=filo, ban_df=ban)

    hh_first_batch, pop_first_batch = next(batches)
    hh_first_batch.to_file(
        households_output_file, layer="households", schema=households_gpkg_schema, driver="GPKG", mode="w"
    )
    pop_first_batch.to_file(
        population_output_file, layer="population", schema=population_gpkg_schema, driver="GPKG", mode="w"
    )
    del hh_first_batch
    del pop_first_batch

    for batch_index, (households, population) in enumerate(batches):
        logging.info(f"Processed batch: {batch_index} out of {nb_batches} ({float(batch_index)/nb_batches:.2%})")
        households.to_file(
            households_output_file, layer="households", schema=households_gpkg_schema, driver="GPKG", mode="a"
        )
        population.to_file(
            population_output_file, layer="population", schema=population_gpkg_schema, driver="GPKG", mode="a"
        )
        del households
        del population
    logging.info("All batches processed")
    logging.info(f"Households database generated: {households_output_file}")
    logging.info(f"Population database generated: {population_output_file}")


if __name__ == "__main__":
    argparser = ArgumentParser()
    argparser.add_argument(
        "-t",
        "--territory",
        dest="territory",
        type=str,
        default="france",
        help="""
        territory to run on (france, 974, 972)
        """,
    )
    argparser.add_argument(
        "-d",
        "--datadir",
        dest="datadir",
        type=str,
        help="""
        path to the data directory
        """,
    )
    argparser.add_argument(
        "-b",
        "--batchsize",
        dest="batchSize",
        type=int,
        help="""
        Batch size for large database processing
        """,
    )
    argparser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        default=False,
        action="store_true",
        help="""
        set logging level to DEBUG
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
        set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
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

    territories = [t.strip() for t in args.territory.split(",") if t]
    # Run main loop
    for territory in territories:
        logging.info(f"Running generation on territory: {territory}...")
        generate_households_population_databases(
            territory=territory, dataDir=Path(args.datadir) if args.datadir else DATA_DIR, batchSize=args.batchSize
        )
