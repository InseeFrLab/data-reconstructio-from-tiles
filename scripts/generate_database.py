#!/usr/bin/env python3
import logging
from argparse import ArgumentParser, BooleanOptionalAction
from pathlib import Path

import numpy as np
import pandas as pd

from popdbgen import (
    DATA_DIR,
    get_batched_households_population_gdf,
    load_BAN,
    load_FILO,
    save_households_metadata,
    save_population_metadata,
)


def generate_households_population_databases(
    territory: str = "METRO",
    dataDir: Path = DATA_DIR,
    seed: int = 1703,
    batchSize: int = 100_000,
    saveAsGeoPackage: bool = True,
    saveAsGeoParquet: bool = False,
):
    if not (saveAsGeoPackage or saveAsGeoParquet):
        logging.error("No export format was specified to save the generated database!")
        return

    np.random.seed(seed)

    filo: pd.DataFrame = load_FILO(dataDir=dataDir, territory=territory)
    ban: pd.DataFrame = load_BAN(dataDir=dataDir, territory=territory)

    hho_gpkg_output_file = dataDir / f"households_{territory}.gpkg"
    pop_gpkg_output_file = dataDir / f"population_{territory}.gpkg"
    hho_parquet_output_file = dataDir / f"households_{territory}.parquet"
    pop_parquet_output_file = dataDir / f"population_{territory}.parquet"

    hho_metadata_output_file = dataDir / f"households_{territory}.yaml"
    pop_metadata_output_file = dataDir / f"population_{territory}.yaml"

    if saveAsGeoPackage:
        logging.info(f"Exporting households to {hho_gpkg_output_file}")
        logging.info(f"Exporting population to {pop_gpkg_output_file}")
    if saveAsGeoParquet:
        logging.info(f"Exporting households to {hho_parquet_output_file}")
        logging.info(f"Exporting population to {pop_parquet_output_file}")

    nb_households = int(filo.men.sum())
    nb_individuals = int(filo.ind.sum())
    logging.info(f"Number of households to process: {nb_households}")
    logging.info(f"Number of individuals to generate: {nb_individuals}")

    nb_batches = 1 + (nb_households - 1) // batchSize

    batches = get_batched_households_population_gdf(batch_size=batchSize, territory=territory, filo_df=filo, ban_df=ban)

    hh_first_batch, pop_first_batch = next(batches)
    if saveAsGeoPackage:
        hh_first_batch.to_file(hho_gpkg_output_file, layer="households", driver="GPKG", mode="w")
        pop_first_batch.to_file(pop_gpkg_output_file, layer="population", driver="GPKG", mode="w")
    if saveAsGeoParquet:
        hh_first_batch.to_wkb().to_parquet(hho_parquet_output_file, engine="fastparquet")
        pop_first_batch.to_wkb().to_parquet(pop_parquet_output_file, engine="fastparquet")
    del hh_first_batch
    del pop_first_batch

    for batch_index, (households, population) in enumerate(batches):
        logging.info(f"Processed batch: {batch_index+1} out of {nb_batches} ({float(batch_index+1)/nb_batches:.2%})")
        if saveAsGeoPackage:
            households.to_file(hho_gpkg_output_file, layer="households", driver="GPKG", mode="a")
            population.to_file(pop_gpkg_output_file, layer="population", driver="GPKG", mode="a")
        if saveAsGeoParquet:
            households.to_wkb().to_parquet(hho_parquet_output_file, engine="fastparquet", append=True)
            population.to_wkb().to_parquet(pop_parquet_output_file, engine="fastparquet", append=True)
        del households
        del population
    logging.info("All batches processed")

    logging.info("Saving metadata")
    save_households_metadata(hho_metadata_output_file, nb_households)
    save_population_metadata(pop_metadata_output_file, nb_individuals)

    if saveAsGeoPackage:
        logging.info(f"Households database generated: {hho_gpkg_output_file}")
        logging.info(f"Population database generated: {pop_gpkg_output_file}")
    if saveAsGeoParquet:
        logging.info(f"Households database generated: {hho_parquet_output_file}")
        logging.info(f"Population database generated: {pop_parquet_output_file}")


if __name__ == "__main__":
    argparser = ArgumentParser()
    argparser.add_argument(
        "-t",
        "--territory",
        dest="territory",
        type=str,
        default="METRO",
        help="""
        comma-separated list of territories to run on (METRO, 974, 972)
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
        default=100_000,
        help="""
        batch size for large database processing (default: 100_000)
        """,
    )
    argparser.add_argument(
        "--geopackage",
        dest="saveAsGeoPackage",
        type=bool,
        default=True,
        action=BooleanOptionalAction,
        help="""
        export generated database as a geopackage file (--geopackage, default), or not (--no-geopackage)
        """,
    )
    argparser.add_argument(
        "--geoparquet",
        dest="saveAsGeoParquet",
        type=bool,
        default=False,
        action=BooleanOptionalAction,
        help="""
        export generated database as a geoparquet file (--geoparquet) or not (--no-geoparquet, default)
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
            territory=territory,
            dataDir=Path(args.datadir) if args.datadir else DATA_DIR,
            batchSize=args.batchSize,
            saveAsGeoPackage=args.saveAsGeoPackage,
            saveAsGeoParquet=args.saveAsGeoParquet,
        )
