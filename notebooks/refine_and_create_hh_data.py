# %%

# 1- fonctions pour générer la base de ménages carreau par carreau
from typing import Dict, List, Tuple
from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time

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

def adjust_household_sizes(sizes: List[int], total_individuals: int) -> List[int]:
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
    while missing_individuals > 0:
        index = np.random.choice(adjustable_indices)
        sizes[index] += 1
        missing_individuals -= 1

    return sizes

def allocate_adults(tile: pd.Series, sizes: List[int]) -> List[int]:
    """
    Alloue un nombre d'adultes à chacun des ménages du carreau
    """
    nb_adults = int(sum(tile[ADULT_AGE_COLUMNS_INT]))
    nb_single_parent = int(tile['men_fmpi'])

    # Tous les ménages ont au moins un adulte
    adults = [1] * len(sizes)
    multi_person_indices = [i for i, size in enumerate(sizes) if size > 1]

    # Tirage des ménages monoparentaux (1 adulte, plusieurs individus)
    single_parent_indices = np.random.choice(multi_person_indices, nb_single_parent, replace=False)

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

def draw_adresses(tile: pd.Series, addresses: pd.DataFrame) -> pd.DataFrame:
    """Tire un ensemble d'adresses pour chacun des ménages du carreau.

    Args:
        tile (pd.Series): informations sur le carreau
        addresses (pd.DataFrame): adresses contenues dans le carreau

    Returns:
        pd.DataFrame: Coordonnées x, y  des adresses tirées pour les ménages du carreau.
        Contient autant de lignes que le carreau contient de ménages.
    """
    if tile['meni'] == 0:
        return None
    # Si aucune adresses n'est disponible, des points fictifs sont créés au sein du carreau
    if addresses.empty:
        drawn_addresses = pd.DataFrame(
            [
                {
                    "x": np.random.randint(tile.XSO, tile.XNE+1, adresses.shape[0]),
                    "y": np.random.randint(tile.YSO, tile.YNE+1, adresses.shape[0]),
                    "tile_id": tile.tile_id,
                }
            ]
        )
    else:
        # Tirage des adresses:
        # Possibilité de tirer plusieurs fois la même adresse.
        adresses_indices = np.random.randint(low=addresses.shape[0], high=None, size=tile['meni'])
        drawn_addresses = addresses.iloc[adresses_indices]

    return(drawn_addresses)

def generate_households(tile: pd.Series, addresses: pd.DataFrame) -> pd.DataFrame:
    """
    Génère une base de ménages d'un carreau
    """
    total_individuals = int(tile['indi'])
    sizes = generate_household_sizes(tile)
    sizes = adjust_household_sizes(sizes, total_individuals)
    adults = allocate_adults(tile, sizes)

    households = []
    for i, (size, adult_count) in enumerate(zip(sizes, adults)):
        households.append({
            "IDMEN": f"{tile['tile_id']}_{i+1}",
            "TAILLE": size,
            "NB_ADULTES": adult_count,
            "NB_MINEURS": size - adult_count,
            "tile_id": tile['tile_id']
        })
    households_df = pd.DataFrame(households)
    households_df["MONOPARENT"] = (households_df["NB_ADULTES"] == 1) * (households_df["NB_MINEURS"] > 0)
    households_df["GRD_MENAGE"] = households_df["TAILLE"] >= 5

    drawn_addresses = draw_adresses(tile, addresses)

    households_df = pd.concat([households_df.reset_index(drop=True), drawn_addresses[['x','y']].reset_index(drop=True)], axis=1)

    return households_df

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

# %%
# 2- Préparation des données en appelant la fonction refine_FILO
from popdbgen import DATA_DIR, get_FILO_filename, download_extract_FILO, refine_FILO, load_BAN, merge_FILO_BAN

def load_FILO_without_refinement(territory: str = "france", dataDir: Path = DATA_DIR):
    download_extract_FILO()
    file_path = get_FILO_filename(territory, dataDir=dataDir)
    tiled_filo = gpd.read_file(file_path)
    return tiled_filo

np.random.seed(1703)

carr200 = load_FILO_without_refinement(territory = "reun")
ban = load_BAN(territory = "974")

start_time = time.time()

carr200i = refine_FILO(carr200)

end_time = time.time()

print(f"Temps de calcul : {end_time - start_time:.2f} secondes")

# %%
# 3- Tests des fonctions de génération de la base de ménages sur un seul carreau
tile = carr200i.iloc[0]
addresses = ban.loc[ban.tile_id == tile.tile_id]
households_df = generate_households(tile, addresses)

if validate_households(households_df, tile):
    print("Génération des ménages cohérente avec les données du carreau")
else:
    print("Error: les données générées sont incohérentes avec les informations du carreau.")

print(households_df)

# %%
# 4- Tests des fonctions de génération de la base de ménages
tile = carr200i.iloc[0]
addresses = ban.loc[ban.tile_id == tile.tile_id]
households_df = generate_households(tile, addresses)

if validate_households(households_df, tile):
    print("Génération des ménages cohérente avec les données du carreau")
else:
    print("Error: les données générées sont incohérentes avec les informations du carreau.")

print(households_df)
