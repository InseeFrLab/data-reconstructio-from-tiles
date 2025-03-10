# %%

# 1- fonctions pour générer la base de ménages carreau par carreau
from typing import Dict, List, Tuple
from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time
from collections.abc import Generator
from popdbgen import DATA_DIR, get_FILO_filename, download_extract_FILO, refine_FILO, load_FILO, load_BAN, merge_FILO_BAN


MIN_HOUSEHOLD_SIZE = 1
MAX_HOUSEHOLD_SIZE = 5
ADULT_AGE_COLUMNS_INT = ['ind_18_24i', 'ind_25_39i', 'ind_40_54i', 'ind_55_64i', 'ind_65_79i', 'ind_80pi', 'ind_inci']

def generate_household_sizes(tile: pd.Series) -> List[int]:
    """
    Initialise la liste de tailles des ménages en fonction du
    nombre de ménages d'une personne et de ménages de 5 personnes ou plus.
    """
    nb_households = int(tile['meni'])
    nb_1person = int(tile['men_1indi'])
    nb_5person_plus = int(tile['men_5indi'])

    sizes = [MIN_HOUSEHOLD_SIZE] * nb_1person + [MAX_HOUSEHOLD_SIZE] * nb_5person_plus
    sizes += [2] * (nb_households - len(sizes))

    return sizes

def adjust_household_sizes(sizes: list[int], total_individuals: int) -> List[int]:
    """
    Met à jour la liste des tailles des ménages en fonction du nombre d'individus dans
    le carreau.
    """
    missing_individuals = total_individuals - sum(sizes)
    adjustable_indices = [i for i, size in enumerate(sizes) if MIN_HOUSEHOLD_SIZE < size < MAX_HOUSEHOLD_SIZE-1]

    # Les individus viennent compléter les ménages de taille intermédiaire
    while missing_individuals > 0 and adjustable_indices:
        index = np.random.choice(adjustable_indices)
        sizes[index] += 1
        missing_individuals -= 1
        if sizes[index] == MAX_HOUSEHOLD_SIZE-1:
            adjustable_indices.remove(index)

    # Ajuste la taille des ménages de 5 personnes ou plus s'il reste des individus à placer
    adjustable_indices = [i for i, size in enumerate(sizes) if size >= MAX_HOUSEHOLD_SIZE]
    while missing_individuals > 0 and adjustable_indices:
        index = np.random.choice(adjustable_indices)
        sizes[index] += 1
        missing_individuals -= 1

    return sizes

def allocate_adults(tile: pd.Series, sizes: List[int]) -> List[int]:
    """
    Alloue un nombre d'adultes à chacun des ménages du carreau
    """
    if len(sizes) == 0:
        return []
    nb_adults = int(sum(tile[ADULT_AGE_COLUMNS_INT]))
    nb_single_parent = tile.men_fmpi

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
        eligible_indices = [i for i, (size, adult) in enumerate(zip(sizes, adults)) if adult < size and i not in single_parent_indices]
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
    if tile.meni == 0:
        return []
    elif addresses.empty:
        return [
            {
                "x": np.random.uniform(tile.XSO, tile.XNE+1),
                "y": np.random.uniform(tile.YSO, tile.YNE+1)
            }
            for _ in range(tile.meni)
        ]
    else:
        # Tirage des adresses:
        # Possibilité de tirer plusieurs fois la même adresse.
        return [
            {
                "x": addresses.x[i],
                "y": addresses.y[i]
            }
            for i in np.random.randint(low=addresses.shape[0], high=None, size=tile.meni)
        ]


# %%
filo: pd.DataFrame = load_FILO("974")
ban: pd.DataFrame = load_BAN("974")

# %%
def generate_households(tile: pd.Series, addresses: pd.DataFrame) -> Generator[dict]:
    """
    Génère une base de ménages d'un carreau
    """
    sizes = generate_household_sizes(tile)
    sizes = adjust_household_sizes(sizes, tile.indi)
    adults = allocate_adults(tile, sizes)

    drawn_addresses = draw_adresses(tile, addresses)
    for i, (size, adult_count, addr) in enumerate(zip(sizes, adults, drawn_addresses)):
        yield {
            "IDMEN": f"{tile['tile_id']}_{i+1}",
            "TAILLE": size,
            "NB_ADULTES": adult_count,
            "NB_MINEURS": size - adult_count,
            "tile_id": tile['tile_id'],
            "MONOPARENT": adult_count == 1 and size > adult_count,
            "GRD_MENAGE": size >= 5,
            "x": addr['x'],
            "y": addr['y']
        }


full_hh_database = merge_FILO_BAN(generate_households, filo_df=filo, ban_df=ban)





# %%

def validate_households(households: pd.DataFrame, tile: pd.Series) -> bool:
    """
    Teste la cohérence d'une base de ménages générée sur un carreau avec les informations
    du carreau lui-même.
    """
    total_individuals = int(tile['indi'])
    total_monoparents = int(tile['men_fmpi'])
    total_gd_menages = int(tile['men_5indi'])
    total_adults = int(sum(tile[ADULT_AGE_COLUMNS_INT]))
    total_minors = total_individuals - total_adults

    checks = {
        "TAILLE": households['TAILLE'].sum() == total_individuals,
        "NB_ADULTES": households['NB_ADULTES'].sum() == total_adults,
        "NB_MINEURS": households['NB_MINEURS'].sum() == total_minors,
        "MONOPARENT": households['MONOPARENT'].sum() == total_monoparents,
        "GRD_MENAGE": households['GRD_MENAGE'].sum() == total_gd_menages
    }

    return all(checks.values())
