import logging
import random
from collections.abc import Callable, Generator
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from .download_ban import load_BAN
from .download_filo import ADULT_AGE_COLUMNS, ALL_AGE_COLUMNS, MINOR_AGE_COLUMNS, load_FILO
from .utils import territory_crs

age_categories = {  # adult (T/F), min age, max age (included)
    "ind_0_3": (False, 0, 3),
    "ind_4_5": (False, 4, 5),
    "ind_6_10": (False, 6, 10),
    "ind_11_17": (False, 11, 17),
    "ind_18_24": (True, 18, 24),
    "ind_25_39": (True, 25, 39),
    "ind_40_54": (True, 40, 54),
    "ind_55_64": (True, 55, 64),
    "ind_65_79": (True, 65, 79),
    "ind_80p": (True, 80, 105),
    "ind_inc": (True, 18, 80),
}


def generate_household_sizes(tile: pd.Series) -> list[int]:
    """
    Initialise la liste de tailles des ménages en fonction du
    nombre de ménages d'une personne et de ménages de 5 personnes ou plus.
    """

    # Start by fixing tile information if they are impossible to comply to
    # note: This should not happen if FILO input dataframe is properly refined
    # (see: refine_FILO_tile function)
    nb_households = tile.men
    hh_1 = tile.men_1ind
    hh_5p = tile.men_5ind
    hh_24 = nb_households - hh_1 - hh_5p

    if hh_24 < 0:
        hh_5p = max(0, hh_5p + hh_24)
        hh_24 = nb_households - hh_1 - hh_5p

    if hh_24 < 0:
        hh_1 = max(0, hh_1 + hh_24)
        hh_24 = nb_households - hh_1 - hh_5p

    while hh_5p > 0 and hh_1 + 2 * hh_24 + 5 * hh_5p > tile.ind:
        hh_5p -= 1
        hh_24 += 1
    while hh_24 > 0 and hh_1 + 2 * hh_24 + 5 * hh_5p > tile.ind:
        hh_24 -= 1
        hh_1 += 1

    while hh_1 > 0 and hh_1 + 4 * hh_24 + 5 * hh_5p < tile.ind:
        hh_1 -= 1
        hh_24 += 1
    while hh_24 > 0 and hh_1 + 4 * hh_24 + 5 * hh_5p < tile.ind:
        hh_24 -= 1
        hh_5p += 1

    sizes = [1] * hh_1 + [2] * hh_24 + [5] * hh_5p
    remaining_ind = tile.ind - hh_1 - 2 * hh_24 - 5 * hh_5p

    # Les individus viennent compléter les ménages de taille intermédiaire (2-3)
    adjustable_indices = [i for i, size in enumerate(sizes) if size in (2, 3)]
    while remaining_ind > 0 and adjustable_indices:
        index = np.random.choice(adjustable_indices)
        sizes[index] += 1
        remaining_ind -= 1
        if sizes[index] == 4:
            adjustable_indices.remove(index)

    # Ajuste la taille des grands ménages (5+) s'il reste des individus à placer
    adjustable_indices = [i for i, size in enumerate(sizes) if size >= 5]
    while remaining_ind > 0 and adjustable_indices:
        index = np.random.choice(adjustable_indices)
        sizes[index] += 1
        remaining_ind -= 1

    # Ajuste la taille de n'importe quel ménage s'il reste des individus à placer
    if remaining_ind > 0:
        adjustable_indices = [i for i in range(len(sizes))]
        while remaining_ind > 0 and adjustable_indices:
            index = np.random.choice(adjustable_indices)
            sizes[index] += 1
            remaining_ind -= 1

    return sizes


def get_households_with_ages(tile: pd.Series) -> list[dict[str, Any]]:
    """
    Alloue un nombre d'adultes à chacun des ménages du carreau.

    Returns:
        Generator[dict]: Liste des ménages générés avec un dictionnaire de features
    """
    sizes = generate_household_sizes(tile)
    if len(sizes) == 0:
        return []
    if sum(sizes) != tile.ind or len(sizes) != tile.men:
        raise Exception(f"[allocate_adults] TILE {tile.tile_id}: Incoherent household sizes!")

    # Lists of all age classes to dispatch among households, repeated as many times as they occur and shuffled
    adult_ages = [age_class for age_class in ADULT_AGE_COLUMNS for _ in range(tile[age_class])]
    minor_ages = [age_class for age_class in MINOR_AGE_COLUMNS for _ in range(tile[age_class])]
    random.shuffle(adult_ages)
    random.shuffle(minor_ages)

    if (  # Quick sanity check (should not be too much of a strain on overall perf)
        tile.men == 0
        or tile.plus18 < tile.men
        or len(adult_ages) != tile.plus18
        or len(minor_ages) != tile.moins18
        or tile.plus18 + tile.moins18 != tile.ind
    ):
        raise Exception(f"[allocate_adults] TILE {tile.tile_id}: Incoherent input tile!")

    households: list[dict[str, Any]] = [{c: 0 for c in ALL_AGE_COLUMNS} for _ in sizes]
    for i, (hh, size) in enumerate(zip(households, sizes, strict=True)):
        hh["TILE_ID"] = tile.tile_id
        hh["HOUSEHOLD_ID"] = f"{tile['tile_id']}_{i+1}"
        hh["SIZE"] = size
        hh["GRD_MENAGE"] = size >= 5
        # Start with at least one adult per household (and no minor for now)
        hh["NB_ADULTS"] = 1
        hh["NB_MINORS"] = 0
        hh[adult_ages.pop()] += 1

    # Successively distribute the remaining adult ages in eligible households
    while adult_ages:
        eligible_indices = [i for i, hh in enumerate(households) if hh["NB_ADULTS"] < hh["SIZE"]]
        if not eligible_indices:
            break
        chosen_hh = households[np.random.choice(eligible_indices)]
        chosen_hh[adult_ages.pop()] += 1
        chosen_hh["NB_ADULTS"] += 1

    # Then distribute the minor ages in the eligible households
    for hh in households:
        hh["NB_MINORS"] = hh["SIZE"] - hh["NB_ADULTS"]
        for _ in range(hh["NB_MINORS"]):
            hh[minor_ages.pop()] += 1
        hh["MONOPARENT"] = hh["NB_ADULTS"] == 1 and hh["NB_ADULTS"] > 1
    return households


def draw_adresses(tile: pd.Series, addresses: pd.DataFrame) -> list[Point]:
    """Tire un ensemble d'adresses pour chacun des ménages du carreau.

    Args:
        tile (pd.Series): informations sur le carreau
        addresses (pd.DataFrame): adresses contenues dans le carreau

    Returns:
        list[Point]: Points (x, y) des adresses tirées pour les ménages du carreau.
        Contient autant de lignes que le carreau contient de ménages.
    """
    # Si aucune adresses n'est disponible, des points fictifs sont créés au sein du carreau
    if tile.men == 0:
        return []
    elif addresses.empty:
        return [
            Point(np.random.uniform(tile.XSO, tile.XNE), np.random.uniform(tile.YSO, tile.YNE)) for _ in range(tile.men)
        ]
    else:
        # Tirage des adresses:
        # Possibilité de tirer plusieurs fois la même adresse.
        return [
            Point(addresses.x[i], addresses.y[i])
            for i in np.random.randint(low=addresses.shape[0], high=None, size=tile.men)
        ]


def generate_tile_households(tile: pd.Series, addresses: pd.DataFrame) -> Generator[dict[str, Any]]:
    """
    Génère une base de ménages d'un carreau
    """
    households = get_households_with_ages(tile)
    drawn_addresses = draw_adresses(tile, addresses)

    # Le niveau de vie des individus dans le ménage
    # On répartit le total des niveaux de vie entre les ménages
    # Les niveaux de vie des individus d'un même ménage sont identiques
    parts = np.random.uniform(0, 1, tile.men)  # tirage uniforme, potentiellement trop perturbateur...
    norm_parts = sum(parts)

    for hh, part, addr in zip(households, parts, drawn_addresses, strict=True):
        hh["NIVEAU_VIE"] = tile.ind_snv * part / norm_parts / hh["SIZE"]
        hh["geometry"] = addr
        yield hh


def generate_population(hh: dict) -> Generator[dict]:
    """
    Génère une base d'individus d'un ménage donné

    Args:
        hh (dict): Information sur un ménage

    Returns:
        Generator[dict]: Base d'individus et leurs caractéristiques.
    """
    # Génération d'une base d'individus basée sur la base de ménages
    individuals = [
        {
            "IND_ID": f"{hh["HOUSEHOLD_ID"]}_{i+1}",
            "HOUSEHOLD_ID": hh["HOUSEHOLD_ID"],
            "HOUSEHOLD_SIZE": hh["SIZE"],
            "GRD_MENAGE": hh["GRD_MENAGE"],
            "MONOPARENT": hh["MONOPARENT"],
            "NIVEAU_VIE": hh["NIVEAU_VIE"],
            "TILE_ID": hh["TILE_ID"],
            "geometry": hh["geometry"],
        }
        for i in range(hh["SIZE"])
    ]
    i = 0
    for age_cat in ALL_AGE_COLUMNS:
        adult, age_min, age_max = age_categories[age_cat]
        for _ in range(hh[age_cat]):
            ind = individuals[i]
            i += 1
            ind["AGE_CAT"] = age_cat
            ind["AGE"] = np.random.randint(age_min, age_max + 1)
            ind["ADULT"] = adult
            ind["STATUT"] = "ADULT" if adult else "MINOR"
            yield ind


def generate_households(
    filo_df: gpd.GeoDataFrame | None = None,
    ban_df: pd.DataFrame | None = None,
    territory: str = "france",
    tile_households_generator: Callable[[pd.Series, pd.DataFrame], Generator[dict]] = generate_tile_households,
    population_generator: Callable[[dict], Generator[dict]] = generate_population,
) -> Generator[dict]:
    """
    Args:
        filo_df (gpd.GeoDataFrame, optional):
            FILO database. Will be (down)loaded if omitted.
        ban_df (pd.DataFrame, optional):
            BAN database. Will be (down)loaded if omitted.
        territory (str, optional):
            A name of the territory to consider: 'france' (default), '974' or '972'.
        tile_household_generator (Callable[[pd.Series, pd.DataFrame], Generator[dict]], optional):
            Function generating household information from a tile aggregated details and a list of addresses.
        population_generator (Callable[[dict], Generator[dict]], optional):
            Function generating population information from household details.

    Returns:
        GeoDataFrame: Un GeoDataFrame contenant les points situés dans les polygones,
                      avec les colonnes x, y, geometry (points) et la colonne identifiant les polygones.
    """
    filo: pd.DataFrame = load_FILO(territory) if filo_df is None else filo_df
    ban: pd.DataFrame = load_BAN(territory) if ban_df is None else ban_df
    tiled_ban = ban.groupby("tile_id", sort=False)

    # Function to apply the tile_household_generator to a given row and the addresses matching it
    def get_addresses(tile: pd.Series) -> pd.DataFrame:
        if tile.tile_id in tiled_ban.groups:
            return tiled_ban.get_group(tile.tile_id).sample(frac=1).reset_index(drop=True)
        else:
            return pd.DataFrame(columns=ban.columns)

    for _, row in filo.iterrows():
        yield from tile_households_generator(row, get_addresses(row))


def get_households_gdf(
    filo_df: gpd.GeoDataFrame | None = None,
    ban_df: pd.DataFrame | None = None,
    territory: str = "france",
    tile_households_generator: Callable[[pd.Series, pd.DataFrame], Generator[dict]] = generate_tile_households,
    population_generator: Callable[[dict], Generator[dict]] = generate_population,
) -> gpd.GeoDataFrame:
    logging.info("Generating households database...")
    households = generate_households(
        filo_df=filo_df,
        ban_df=ban_df,
        territory=territory,
        tile_households_generator=tile_households_generator,
        population_generator=population_generator,
    )
    return gpd.GeoDataFrame(data=households, geometry="geometry", crs=territory_crs(territory))


def get_population_gdf(
    filo_df: gpd.GeoDataFrame | None = None,
    ban_df: pd.DataFrame | None = None,
    territory: str = "france",
    tile_households_generator: Callable[[pd.Series, pd.DataFrame], Generator[dict]] = generate_tile_households,
    population_generator: Callable[[dict], Generator[dict]] = generate_population,
) -> gpd.GeoDataFrame:
    logging.info("Generating population database...")
    households = generate_households(
        filo_df=filo_df,
        ban_df=ban_df,
        territory=territory,
        tile_households_generator=tile_households_generator,
        population_generator=population_generator,
    )
    return gpd.GeoDataFrame(
        data=[ind for hh in households for ind in population_generator(hh)],
        geometry="geometry",
        crs=territory_crs(territory),
    )


def get_households_population_gdf(
    filo_df: gpd.GeoDataFrame | None = None,
    ban_df: pd.DataFrame | None = None,
    territory: str = "france",
    tile_households_generator: Callable[[pd.Series, pd.DataFrame], Generator[dict]] = generate_tile_households,
    population_generator: Callable[[dict], Generator[dict]] = generate_population,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    logging.info("Generating households and population databases...")
    households = list(
        generate_households(
            filo_df=filo_df,
            ban_df=ban_df,
            territory=territory,
            tile_households_generator=tile_households_generator,
            population_generator=population_generator,
        )
    )
    return (
        gpd.GeoDataFrame(data=households, geometry="geometry", crs=territory_crs(territory)),
        gpd.GeoDataFrame(
            data=[ind for hh in households for ind in population_generator(hh)],
            geometry="geometry",
            crs=territory_crs(territory),
        ),
    )
