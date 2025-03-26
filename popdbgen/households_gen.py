import logging
import random
from collections.abc import Callable, Generator, Iterator
from itertools import batched
from typing import TypedDict, cast

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from .download_ban import load_BAN
from .download_filo import load_FILO
from .utils import (
    ADULT_AGE_COLUMNS,
    ADULT_AGE_LITERAL,
    ALL_AGE_COLUMNS,
    MINOR_AGE_COLUMNS,
    MINOR_AGE_LITERAL,
    HouseholdsFeature,
    PopulationFeature,
    TerritoryCode,
    age_categories,
    mkHouseholdsDataFrame,
    mkPopulationDataFrame,
)


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


class AlmostHouseholdsFeature(TypedDict):
    ID: str
    TILE_ID: str
    SIZE: int
    NB_ADULTS: int
    NB_MINORS: int
    GRD_MENAGE: bool
    MONOPARENT: bool
    ind_0_3: int
    ind_4_5: int
    ind_6_10: int
    ind_11_17: int
    ind_18_24: int
    ind_25_39: int
    ind_40_54: int
    ind_55_64: int
    ind_65_79: int
    ind_80p: int
    ind_inc: int


def emptyHousehold(tile_id, i, size) -> AlmostHouseholdsFeature:
    return AlmostHouseholdsFeature(
        ID=f"{tile_id}_{i+1}",
        TILE_ID=tile_id,
        SIZE=size,
        GRD_MENAGE=size >= 5,
        MONOPARENT=False,
        NB_ADULTS=1,
        NB_MINORS=0,
        ind_0_3=0,
        ind_4_5=0,
        ind_6_10=0,
        ind_11_17=0,
        ind_18_24=0,
        ind_25_39=0,
        ind_40_54=0,
        ind_55_64=0,
        ind_65_79=0,
        ind_80p=0,
        ind_inc=0,
    )


def get_households_with_ages(tile: pd.Series) -> list[AlmostHouseholdsFeature]:
    """
    Alloue un nombre d'adultes à chacun des ménages du carreau.

    Returns:
        list[HouseholdsFeature]: Liste des ménages générés avec un dictionnaire de features
    """
    sizes = generate_household_sizes(tile)
    if len(sizes) == 0:
        return []
    if sum(sizes) != tile.ind or len(sizes) != tile.men:
        raise Exception(f"[allocate_adults] TILE {tile.tile_id}: Incoherent household sizes!")

    # Lists of all age classes to dispatch among households, repeated as many times as they occur and shuffled
    adult_ages: list[ADULT_AGE_LITERAL] = [age_class for age_class in ADULT_AGE_COLUMNS for _ in range(tile[age_class])]
    minor_ages: list[MINOR_AGE_LITERAL] = [age_class for age_class in MINOR_AGE_COLUMNS for _ in range(tile[age_class])]
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

    households: list[AlmostHouseholdsFeature] = [emptyHousehold(tile.tile_id, i, size) for i, size in enumerate(sizes)]
    for hh in households:
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
        hh["MONOPARENT"] = hh["NB_ADULTS"] == 1 and hh["NB_MINORS"] > 0
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


def generate_tile_households(tile: pd.Series, addresses: pd.DataFrame) -> Generator[HouseholdsFeature]:
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
        res: HouseholdsFeature = cast(HouseholdsFeature, hh)
        # Note: This
        res["NIVEAU_VIE"] = tile.ind_snv * part / norm_parts / hh["SIZE"]
        res["geometry"] = addr
        yield res


def generate_population(hh: HouseholdsFeature) -> Generator[PopulationFeature]:
    """
    Génère une base d'individus d'un ménage donné

    Args:
        hh (dict): Information sur un ménage

    Returns:
        Generator[dict]: Base d'individus et leurs caractéristiques.
    """
    i = 0
    for age_cat in ALL_AGE_COLUMNS:
        adult, age_min, age_max = age_categories[age_cat]
        for _ in range(hh[age_cat]):
            yield PopulationFeature(
                ID=f"{hh["ID"]}_{i+1}",
                HOUSEHOLD_ID=hh["ID"],
                HOUSEHOLD_SIZE=hh["SIZE"],
                GRD_MENAGE=hh["GRD_MENAGE"],
                MONOPARENT=hh["MONOPARENT"],
                NIVEAU_VIE=hh["NIVEAU_VIE"],
                TILE_ID=hh["TILE_ID"],
                AGE_CAT=age_cat,
                AGE=np.random.randint(age_min, age_max + 1),
                ADULT=adult,
                STATUT="ADULT" if adult else "MINOR",
                geometry=hh["geometry"],
            )
            i += 1


def generate_households(
    territory: TerritoryCode = "france",
    filo_df: gpd.GeoDataFrame | None = None,
    ban_df: pd.DataFrame | None = None,
    tile_households_generator: Callable[
        [pd.Series, pd.DataFrame], Iterator[HouseholdsFeature]
    ] = generate_tile_households,
) -> Generator[HouseholdsFeature]:
    """
    Args:
        territory (TerritoryCode):
            A name of the territory to consider: 'france' (default), '974' or '972'.
        filo_df (gpd.GeoDataFrame, optional):
            FILO database. Will be (down)loaded if omitted.
        ban_df (pd.DataFrame, optional):
            BAN database. Will be (down)loaded if omitted.
        tile_household_generator (Callable[[pd.Series, pd.DataFrame], Generator[dict]], optional):
            Function generating household information from a tile aggregated details and a list of addresses.

    Returns:
        GeoDataFrame: A Generator for row dictionnaries representing households
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
    territory: TerritoryCode = "france",
    filo_df: gpd.GeoDataFrame | None = None,
    ban_df: pd.DataFrame | None = None,
    tile_households_generator: Callable[
        [pd.Series, pd.DataFrame], Iterator[HouseholdsFeature]
    ] = generate_tile_households,
) -> gpd.GeoDataFrame:
    """
    Args:
        territory (TerritoryCode):
            A name of the territory to consider: 'france' (default), '974' or '972'.
        filo_df (gpd.GeoDataFrame, optional):
            FILO database. Will be (down)loaded if omitted.
        ban_df (pd.DataFrame, optional):
            BAN database. Will be (down)loaded if omitted.
        tile_household_generator (Callable[[pd.Series, pd.DataFrame], Iterator[dict]], optional):
            Function generating household information from a tile aggregated details and a list of addresses.

    Returns:
        GeoDataFrame: A GeoDataFrame households database
    """
    logging.info("Generating households database...")
    households = generate_households(
        filo_df=filo_df, ban_df=ban_df, territory=territory, tile_households_generator=tile_households_generator
    )
    return mkHouseholdsDataFrame(list(households), territory)


def get_population_gdf(
    territory: TerritoryCode = "france",
    filo_df: gpd.GeoDataFrame | None = None,
    ban_df: pd.DataFrame | None = None,
    tile_households_generator: Callable[
        [pd.Series, pd.DataFrame], Iterator[HouseholdsFeature]
    ] = generate_tile_households,
    population_generator: Callable[[HouseholdsFeature], Iterator[PopulationFeature]] = generate_population,
) -> gpd.GeoDataFrame:
    """
    Args:
        territory (TerritoryCode):
            A name of the territory to consider: 'france' (default), '974' or '972'.
        filo_df (gpd.GeoDataFrame, optional):
            FILO database. Will be (down)loaded if omitted.
        ban_df (pd.DataFrame, optional):
            BAN database. Will be (down)loaded if omitted.
        tile_household_generator (Callable[[pd.Series, pd.DataFrame], Iterator[dict]], optional):
            Function generating household information from a tile aggregated details and a list of addresses.
        population_generator (Callable[[dict], Iterator[dict]], optional):
            Function generating population information from household details.

    Returns:
        GeoDataFrame: A GeoDataFrame population database
    """
    logging.info("Generating population database...")
    households = generate_households(
        filo_df=filo_df, ban_df=ban_df, territory=territory, tile_households_generator=tile_households_generator
    )
    return mkPopulationDataFrame([ind for hh in households for ind in population_generator(hh)], territory)


def get_households_population_gdf(
    territory: TerritoryCode = "france",
    filo_df: gpd.GeoDataFrame | None = None,
    ban_df: pd.DataFrame | None = None,
    tile_households_generator: Callable[
        [pd.Series, pd.DataFrame], Iterator[HouseholdsFeature]
    ] = generate_tile_households,
    population_generator: Callable[[HouseholdsFeature], Iterator[PopulationFeature]] = generate_population,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Args:
        territory (TerritoryCode):
            A name of the territory to consider: 'france' (default), '974' or '972'.
        filo_df (gpd.GeoDataFrame, optional):
            FILO database. Will be (down)loaded if omitted.
        ban_df (pd.DataFrame, optional):
            BAN database. Will be (down)loaded if omitted.
        tile_household_generator (Callable[[pd.Series, pd.DataFrame], Iterator[dict]], optional):
            Function generating household information from a tile aggregated details and a list of addresses.
        population_generator (Callable[[dict], Iterator[dict]], optional):
            Function generating population information from household details.

    Returns:
        tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
            A pair of GeoDataFrames containing the households and population databases in that order.
    """
    logging.info("Generating households and population databases...")
    households = list(
        generate_households(
            filo_df=filo_df, ban_df=ban_df, territory=territory, tile_households_generator=tile_households_generator
        )
    )
    return (
        mkHouseholdsDataFrame(households, territory),
        mkPopulationDataFrame([ind for hh in households for ind in population_generator(hh)], territory),
    )


def generate_batched_households(
    territory: TerritoryCode = "france",
    batch_size: int = 1000,
    filo_df: gpd.GeoDataFrame | None = None,
    ban_df: pd.DataFrame | None = None,
    tile_households_generator: Callable[
        [pd.Series, pd.DataFrame], Iterator[HouseholdsFeature]
    ] = generate_tile_households,
) -> Iterator[tuple[HouseholdsFeature, ...]]:
    return batched(
        generate_households(
            filo_df=filo_df, ban_df=ban_df, territory=territory, tile_households_generator=tile_households_generator
        ),
        batch_size,
    )


def get_batched_households_gdf(
    territory: TerritoryCode = "france",
    batch_size: int = 1000,
    filo_df: gpd.GeoDataFrame | None = None,
    ban_df: pd.DataFrame | None = None,
    tile_households_generator: Callable[
        [pd.Series, pd.DataFrame], Iterator[HouseholdsFeature]
    ] = generate_tile_households,
) -> Generator[gpd.GeoDataFrame]:
    """
    Args:
        territory (TerritoryCode):
            A name of the territory to consider: 'france' (default), '974' or '972'.
        filo_df (gpd.GeoDataFrame, optional):
            FILO database. Will be (down)loaded if omitted.
        ban_df (pd.DataFrame, optional):
            BAN database. Will be (down)loaded if omitted.
        tile_household_generator (Callable[[pd.Series, pd.DataFrame], Iterator[dict]], optional):
            Function generating household information from a tile aggregated details and a list of addresses.

    Returns:
        GeoDataFrame: A GeoDataFrame households database
    """
    logging.info("Generating households database...")
    for households_batch in generate_batched_households(
        batch_size=batch_size,
        filo_df=filo_df,
        ban_df=ban_df,
        territory=territory,
        tile_households_generator=tile_households_generator,
    ):
        yield mkHouseholdsDataFrame(households_batch, territory)


def get_batched_population_gdf(
    territory: TerritoryCode = "france",
    batch_size: int = 1000,
    filo_df: gpd.GeoDataFrame | None = None,
    ban_df: pd.DataFrame | None = None,
    tile_households_generator: Callable[
        [pd.Series, pd.DataFrame], Iterator[HouseholdsFeature]
    ] = generate_tile_households,
    population_generator: Callable[[HouseholdsFeature], Iterator[PopulationFeature]] = generate_population,
) -> Generator[gpd.GeoDataFrame]:
    """
    Args:
        territory (TerritoryCode):
            A name of the territory to consider: 'france' (default), '974' or '972'.
        filo_df (gpd.GeoDataFrame, optional):
            FILO database. Will be (down)loaded if omitted.
        ban_df (pd.DataFrame, optional):
            BAN database. Will be (down)loaded if omitted.
        tile_household_generator (Callable[[pd.Series, pd.DataFrame], Iterator[dict]], optional):
            Function generating household information from a tile aggregated details and a list of addresses.
        population_generator (Callable[[dict], Iterator[dict]], optional):
            Function generating population information from household details.

    Returns:
        GeoDataFrame: A GeoDataFrame population database
    """
    logging.info("Generating population database...")
    for households_batch in generate_batched_households(
        batch_size=batch_size,
        filo_df=filo_df,
        ban_df=ban_df,
        territory=territory,
        tile_households_generator=tile_households_generator,
    ):
        yield mkPopulationDataFrame([ind for hh in households_batch for ind in population_generator(hh)], territory)


def get_batched_households_population_gdf(
    territory: TerritoryCode = "france",
    batch_size: int = 1000,
    filo_df: gpd.GeoDataFrame | None = None,
    ban_df: pd.DataFrame | None = None,
    tile_households_generator: Callable[
        [pd.Series, pd.DataFrame], Iterator[HouseholdsFeature]
    ] = generate_tile_households,
    population_generator: Callable[[HouseholdsFeature], Iterator[PopulationFeature]] = generate_population,
) -> Generator[tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]]:
    """
    Args:
        territory (TerritoryCode):
            A name of the territory to consider: 'france' (default), '974' or '972'.
        filo_df (gpd.GeoDataFrame, optional):
            FILO database. Will be (down)loaded if omitted.
        ban_df (pd.DataFrame, optional):
            BAN database. Will be (down)loaded if omitted.
        tile_household_generator (Callable[[pd.Series, pd.DataFrame], Iterator[dict]], optional):
            Function generating household information from a tile aggregated details and a list of addresses.
        population_generator (Callable[[dict], Iterator[dict]], optional):
            Function generating population information from household details.

    Returns:
        tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
            A pair of GeoDataFrames containing the households and population databases in that order.
    """
    logging.info("Generating households and population databases...")
    for households_batch in generate_batched_households(
        batch_size=batch_size,
        filo_df=filo_df,
        ban_df=ban_df,
        territory=territory,
        tile_households_generator=tile_households_generator,
    ):
        yield (
            mkHouseholdsDataFrame(households_batch, territory),
            mkPopulationDataFrame([ind for hh in households_batch for ind in population_generator(hh)], territory),
        )
