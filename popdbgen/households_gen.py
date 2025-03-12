import random
from collections.abc import Callable, Generator, Sequence

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from .download_ban import load_BAN
from .download_filo import ADULT_AGE_COLUMNS, ALL_AGE_COLUMNS, MINOR_AGE_COLUMNS, load_FILO


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


def allocate_ages(tile: pd.Series, sizes: Sequence[int]) -> list[dict]:
    """
    Alloue un nombre d'adultes à chacun des ménages du carreau
    """
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

    households_ages = [{c: 0 for c in ALL_AGE_COLUMNS} for _ in range(tile.men)]
    # Start with at least one adult per household (and no minor for now)
    for ages in households_ages:
        ages["plus18"] = 1
        ages["moins18"] = 0
        ages[adult_ages.pop()] += 1

    # Successively dispatch the remaining adult ages in eligible households
    while adult_ages:
        eligible_indices = [i for i, ages in enumerate(households_ages) if ages["plus18"] < sizes[i]]
        if not eligible_indices:
            break
        index = np.random.choice(eligible_indices)
        households_ages[index][adult_ages.pop()] += 1
        households_ages[index]["plus18"] += 1

    for i, ages in enumerate(households_ages):
        ages["moins18"] = sizes[i] - ages["plus18"]
        for _ in range(ages["moins18"]):
            ages[minor_ages.pop()] += 1

    return households_ages


def draw_adresses(tile: pd.Series, addresses: pd.DataFrame) -> list[Point]:
    """Tire un ensemble d'adresses pour chacun des ménages du carreau.

    Args:
        tile (pd.Series): informations sur le carreau
        addresses (pd.DataFrame): adresses contenues dans le carreau

    Returns:
        pd.DataFrame: Coordonnées x, y  des adresses tirées pour les ménages du carreau.
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


def generate_tile_households(tile: pd.Series, addresses: pd.DataFrame) -> Generator[dict]:
    """
    Génère une base de ménages d'un carreau
    """
    sizes = generate_household_sizes(tile)
    households_ages = allocate_ages(tile, sizes)

    # Le niveau de vie des individus dans le ménage
    # On répartit le total des niveaux de vie entre les ménages
    # Les niveaux de vie des individus d'un même ménage sont identiques
    parts = np.random.uniform(0, 1, len(sizes))  # tirage uniforme potentiellement trop perturbateur.
    parts = parts / sum(parts)

    niveau_vie_ind_hh = [tile.ind_snv * p / s for p, s in zip(parts, sizes, strict=True)]

    drawn_addresses = draw_adresses(tile, addresses)
    for i, (size, ages, nivvie, addr) in enumerate(
        zip(sizes, households_ages, niveau_vie_ind_hh, drawn_addresses, strict=True)
    ):
        yield {
            "IDMEN": f"{tile['tile_id']}_{i+1}",
            "TAILLE": size,
            "NB_ADULTES": ages["plus18"],
            "NB_MINEURS": ages["moins18"],
            "NIVEAU_VIE": nivvie,
            "MONOPARENT": ages["plus18"] == 1 and size > 1,
            "GRD_MENAGE": size >= 5,
            "tile_id": tile.tile_id,
            "geometry": addr,
        }


# Fonction de test
def test(reduce_f: Callable[[pd.Series, pd.DataFrame], pd.DataFrame]):
    # TODO
    # - Build dummy FILO tile Series and BAN addresses dataframe
    # - Call "reduce_f" on it
    # - Implement some sanity check on the output
    pass


def generate_households(
    tile_household_generator: Callable[[pd.Series, pd.DataFrame], Generator[dict]] = generate_tile_households,
    filo_df: gpd.GeoDataFrame | None = None,
    ban_df: pd.DataFrame | None = None,
    territory: str = "france",
) -> gpd.GeoDataFrame:
    """
    Args:
        tile_household_generator (Callable[[pd.Series, pd.DataFrame], Generator[dict]],optional):
            Function generating household information from a tile aggregated details and a list of addresses.
        filo_df (gpd.GeoDataFrame, optional):
            FILO database. Will be (down)loaded if omitted.
        ban_df (pd.DataFrame, optional):
            BAN database. Will be (down)loaded if omitted.
        territory (str, optional):
            A name of the territory to consider: 'france' (default), '974' or '972'.

    Returns:
        GeoDataFrame: Un GeoDataFrame contenant les points situés dans les polygones,
                      avec les colonnes x, y, geometry (points) et la colonne identifiant les polygones.
    """
    filo: pd.DataFrame = load_FILO(territory) if filo_df is None else filo_df
    ban: pd.DataFrame = load_BAN(territory) if ban_df is None else ban_df
    tiled_ban = ban.groupby("tile_id", sort=False)

    # Function to apply the tile_household_generator to a given row and the addresses matching it
    def generate_all_tile_households(tile: pd.Series) -> Generator[dict]:
        idcar = tile.tile_id
        if idcar in tiled_ban.groups:
            addresses = tiled_ban.get_group(idcar).sample(frac=1).reset_index(drop=True)
        else:
            addresses = pd.DataFrame(columns=ban.columns)
        return generate_tile_households(tile, addresses)

    return gpd.GeoDataFrame(
        [households for _, row in filo.iterrows() for households in generate_all_tile_households(row)],
        geometry="geometry",
    )
