from collections.abc import Generator, Sequence

import numpy as np
import pandas as pd

from .download_filo import ADULT_AGE_COLUMNS


def generate_household_sizes(tile: pd.Series) -> list[int]:
    """
    Initialise la liste de tailles des ménages en fonction du
    nombre de ménages d'une personne et de ménages de 5 personnes ou plus.
    """
    sizes: list[int] = [1] * tile.men_1ind + [5] * tile.men_5ind + [2] * (tile.men - tile.men_1ind - tile.men_5ind)
    remaining_ind = tile.ind - sum(sizes)

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

    return sizes


def allocate_adults(tile: pd.Series, sizes: Sequence[int]) -> list[int]:
    """
    Alloue un nombre d'adultes à chacun des ménages du carreau
    """
    if len(sizes) == 0:
        return []
    nb_adults = sum(tile[ADULT_AGE_COLUMNS])
    nb_single_parent = tile.men_fmp

    # Tous les ménages ont au moins un adulte
    adults = [1] * len(sizes)

    # Tirage des ménages monoparentaux (1 adulte, plusieurs individus)
    multi_person_indices = [i for i, size in enumerate(sizes) if size > 1]
    if multi_person_indices:
        single_parent_indices = set(np.random.choice(multi_person_indices, nb_single_parent, replace=False))
        # Pour les autres ménages de 2 personnes au moins, on ajoute un second adulte
        for i in multi_person_indices:
            if i not in single_parent_indices and adults[i] < sizes[i]:
                adults[i] += 1

    # Distribue les adultes restants dans les ménages éligibles
    remaining_adults = nb_adults - sum(adults)
    while remaining_adults > 0:
        eligible_indices = [
            i
            for i, (size, adult) in enumerate(zip(sizes, adults, strict=True))
            if adult < size and i not in single_parent_indices
        ]
        if not eligible_indices:
            break
        index = np.random.choice(eligible_indices)
        adults[index] += 1
        remaining_adults -= 1

    return adults


def draw_adresses(tile: pd.Series, addresses: pd.DataFrame) -> list[dict]:
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
            {"x": np.random.uniform(tile.XSO, tile.XNE + 1), "y": np.random.uniform(tile.YSO, tile.YNE + 1)}
            for _ in range(tile.men)
        ]
    else:
        # Tirage des adresses:
        # Possibilité de tirer plusieurs fois la même adresse.
        return [
            {"x": addresses.x[i], "y": addresses.y[i]}
            for i in np.random.randint(low=addresses.shape[0], high=None, size=tile.men)
        ]


def generate_households(tile: pd.Series, addresses: pd.DataFrame) -> Generator[dict]:
    """
    Génère une base de ménages d'un carreau
    """
    sizes = generate_household_sizes(tile)
    adults = allocate_adults(tile, sizes)

    drawn_addresses = draw_adresses(tile, addresses)
    if len(drawn_addresses) != len(adults):
        print(drawn_addresses)
        print(tile.T)
        print(adults)
        raise Exception("Test")
    for i, (size, adult_count, addr) in enumerate(zip(sizes, adults, drawn_addresses, strict=True)):
        yield {
            "IDMEN": f"{tile['tile_id']}_{i+1}",
            "TAILLE": size,
            "NB_ADULTES": adult_count,
            "NB_MINEURS": size - adult_count,
            "MONOPARENT": adult_count == 1 and size > adult_count,
            "GRD_MENAGE": size >= 5,
            "tile_id": tile.tile_id,
            "x": addr["x"],
            "y": addr["y"],
        }
