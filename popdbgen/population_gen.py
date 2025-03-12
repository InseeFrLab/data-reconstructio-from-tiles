from collections.abc import Callable, Generator

import geopandas as gpd
import numpy as np
import pandas as pd

from .households_gen import generate_households, generate_tile_households


def generate_tile_population(hh: pd.Series) -> Generator[dict]:
    """
    Génère une base d'individus d'un ménage donné

    Args:
        hh (gpd.GeoSeries): Information sur un ménage

    Returns:
        gpd.GeoDataFrame: Base d'individus et leurs caractéristiques.
    """
    # Génération d'une base d'individus basée sur la base de ménages
    repeate_idmen = np.repeat(hh["IDMEN"], hh["TAILLE"])
    individual_id = np.concatenate(
        [[idmen + "_" + str(i + 1) for i in range(n)] for n, idmen in zip(hh["TAILLE"], hh["IDMEN"], strict=False)]
    )
    statut = np.concatenate(
        [
            np.concatenate([np.repeat("adulte", nb_adultes), np.repeat("mineur", nb_mineurs)])
            for nb_adultes, nb_mineurs in zip(hh["NB_ADULTES"], hh["NB_MINEURS"], strict=False)
        ]
    )

    # Ajout de l'âge
    age_adultes = np.concatenate([np.repeat(cat, tile[cat]) for cat in ADULT_AGE_COLUMNS])
    if (age_adultes.shape[0] - hh.NB_ADULTES.sum()) != 0:
        print(hh)
    np.random.shuffle(age_adultes)
    age_mineurs = np.concatenate([np.repeat(cat, tile[cat]) for cat in MINOR_AGE_COLUMNS_INT])
    np.random.shuffle(age_mineurs)

    individuals_df = pd.DataFrame({"ID": individual_id, "IDMEN": repeate_idmen, "STATUT": statut, "CATAGE": ""})
    individuals_df.loc[individuals_df["STATUT"] == "adulte", "CATAGE"] = age_adultes
    individuals_df.loc[individuals_df["STATUT"] == "mineur", "CATAGE"] = age_mineurs
    individuals_df = individuals_df.merge(pd.DataFrame.from_dict(AGES), on="CATAGE")

    individuals_df["AGE"] = individuals_df.apply(lambda row: np.random.randint(row["INF"], row["SUP"] + 1), axis=1)
    individuals_df = individuals_df.drop(["INF", "SUP", "LIM"], axis=1)
    # Info sur les ménages
    individuals_df = individuals_df.merge(
        hh[["tile_id", "IDMEN", "TAILLE", "NIVEAU_VIE", "MONOPARENT", "GRD_MENAGE", "x", "y"]], on="IDMEN"
    )
    return individuals_df


def generate_population(
    tile_population_generator: Callable[[pd.Series], Generator[dict]] = generate_tile_population,
    households: gpd.GeoDataFrame | None = None,
    tile_household_generator: Callable[[pd.Series, pd.DataFrame], Generator[dict]] = generate_tile_households,
    filo_df: gpd.GeoDataFrame | None = None,
    ban_df: pd.DataFrame | None = None,
    territory: str = "france",
):
    """
    Génère une base d'individus.

    Args:
        tile_population_generator (Callable[[pd.Series], Generator[dict]], optional):
            Function generating individual information from household details.
        households (gpd.GeoDataFrame, optional):
            Households database. Will be generated if omitted.
        tile_household_generator (Callable[[pd.Series, pd.DataFrame], Generator[dict]],optional):
            Function generating household information from a tile aggregated details and a list of addresses.
        filo_df (gpd.GeoDataFrame, optional):
            FILO database. Will be (down)loaded if omitted.
        ban_df (pd.DataFrame, optional):
            BAN database. Will be (down)loaded if omitted.
        territory (str, optional):
            A name of the territory to consider: 'france' (default), '974' or '972'.

    Returns:
        gpd.GeoDataFrame: Base d'individus et leurs caractéristiques.
    """
    if households is None:
        # Households generation using
        households = generate_households(
            tile_household_generator=tile_household_generator, filo_df=filo_df, ban_df=ban_df, territory=territory
        )
    return gpd.GeoDataFrame(
        [households for _, row in households.iterrows() for households in tile_population_generator(row)],
        geometry="geometry",
    )
