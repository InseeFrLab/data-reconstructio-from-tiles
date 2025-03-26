#!/usr/bin/env python3
import logging
from argparse import ArgumentParser
from pathlib import Path

from popdbgen import DATA_DIR, download_extract_FILO

if __name__ == "__main__":
    argparser = ArgumentParser()
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
        "-o",
        "--overwrite",
        dest="overwrite",
        default=False,
        action="store_true",
        help="""
        overwrite data files if they exist
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
    # Run main program
    download_extract_FILO(dataDir=Path(args.datadir) if args.datadir else DATA_DIR, overwriteIfExists=args.overwrite)
