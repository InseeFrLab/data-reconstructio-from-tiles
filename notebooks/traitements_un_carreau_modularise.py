# %% 

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

MIN_HOUSEHOLD_SIZE = 1
MAX_HOUSEHOLD_SIZE = 5
ADULT_AGE_COLUMNS = ['ind_18_24', 'ind_25_39', 'ind_40_54', 'ind_55_64', 'ind_65_79', 'ind_80p', 'ind_inc']

def generate_household_sizes(carreau: pd.Series) -> List[int]:
    """
    Initialise la liste de tailles des ménages en fonction du 
    nombre de manages d'une personne et de ménages de 5 personnes ou plus.
    """
    nb_households = int(carreau['men'])
    nb_1person = int(carreau['men_1ind'])
    nb_5person_plus = int(carreau['men_5ind'])
    
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

def allocate_adults(carreau: pd.Series, sizes: List[int]) -> List[int]:
    """
    Alloue un nombre d'adultes à chacun des ménages du carreau
    """
    nb_adults = int(sum(carreau[ADULT_AGE_COLUMNS]))
    nb_single_parent = int(carreau['men_fmp'])
    
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

def generate_households(carreau: pd.Series) -> pd.DataFrame:
    """
    Génère une base de ménages d'un carreau
    """
    total_individuals = int(carreau['ind'])
    sizes = generate_household_sizes(carreau)
    sizes = adjust_household_sizes(sizes, total_individuals)
    adults = allocate_adults(carreau, sizes)
    
    households = []
    for i, (size, adult_count) in enumerate(zip(sizes, adults)):
        households.append({
            "IDMEN": f"{carreau['idcar_200m']}_{i+1}",
            "TAILLE": size,
            "NB_ADULTES": adult_count,
            "NB_MINEURS": size - adult_count,
            "id_carr200": carreau['idcar_200m']
        })
    households_df = pd.DataFrame(households)
    households_df["MONOPARENT"] = (households_df["NB_ADULTES"] == 1) * (households_df["NB_MINEURS"] > 0)
    households_df["GRD_MENAGE"] = households_df["TAILLE"] >= 5
    
    return households_df

def validate_households(households: pd.DataFrame, carreau: pd.Series) -> bool:
    """
    Teste la cohérence d'une base de ménages générée sur un carreau avec les informations
    du carreau lui-même.
    """
    total_individuals = int(carreau['ind'])
    total_monoparents = int(carreau['men_fmp'])
    total_gd_menages = int(carreau['men_5ind'])
    total_adults = int(sum(carreau[ADULT_AGE_COLUMNS]))
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
# Préparation d'un carreau
import sys
import time
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from pgms.utils import DATA_DIR

file_path = DATA_DIR / "carreaux_200m_reun.gpkg"

np.random.seed(1703)

BAN_974_URL = "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-974.csv.gz"

# ETAPE 1: base individuelle à partir des carreaux
file_path = "../data/carreaux_200m_reun.gpkg"
carr200 = gpd.read_file(file_path)

mon_carreau = carr200.iloc[0]
mon_carreau[[
    'ind','men','men_1ind','men_5ind',
    'men_prop','men_fmp','men_coll', 'men_mais',
    'ind_0_3', 'ind_4_5', 'ind_6_10', 'ind_11_17',
    'ind_18_24', 'ind_25_39', 'ind_40_54', 'ind_55_64', 'ind_65_79', 'ind_80p', 'ind_inc'
]] = mon_carreau[[
    'ind','men','men_1ind','men_5ind',
    'men_prop','men_fmp','men_coll', 'men_mais',
    'ind_0_3', 'ind_4_5', 'ind_6_10', 'ind_11_17',
    'ind_18_24', 'ind_25_39', 'ind_40_54', 'ind_55_64', 'ind_65_79', 'ind_80p', 'ind_inc'
]].apply(np.floor)

mon_carreau.ind_25_39 = 5
mon_carreau.ind_65_79 = 6
mon_carreau.ind_80p = 1
mon_carreau.ind_11_17 = 2 
 # %%

households_df = generate_households(mon_carreau)

if validate_households(households_df, mon_carreau):
    print("Génération des ménages cohérente avec les données du carreau")
else:
    print("Error: les données générées sont incohérentes avec les informations du carreau.")

print(households_df)

# %%
