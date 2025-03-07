# %%

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

MIN_HOUSEHOLD_SIZE = 1
MAX_HOUSEHOLD_SIZE = 5
ADULT_AGE_COLUMNS = ['ind_18_24', 'ind_25_39', 'ind_40_54', 'ind_55_64', 'ind_65_79', 'ind_80p', 'ind_inc']

def generate_household_sizes(tile: pd.Series) -> List[int]:
    """
    Initialise la liste de tailles des ménages en fonction du
    nombre de manages d'une personne et de ménages de 5 personnes ou plus.
    """
    nb_households = int(tile['men'])
    nb_1person = int(tile['men_1ind'])
    nb_5person_plus = int(tile['men_5ind'])

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
    nb_adults = int(sum(tile[ADULT_AGE_COLUMNS]))
    nb_single_parent = int(tile['men_fmp'])

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
    if tile.men == 0:
        return []
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
        adresses_indices = np.random.randint(addresses.shape[0], tile.men)
        drawn_addresses = addresses[adresses_indices]

    return(drawn_addresses)

def generate_households(tile: pd.Series, addresses: pd.DataFrame) -> pd.DataFrame:
    """
    Génère une base de ménages d'un carreau
    """
    total_individuals = int(tile['ind'])
    sizes = generate_household_sizes(tile)
    sizes = adjust_household_sizes(sizes, total_individuals)
    adults = allocate_adults(tile, sizes)

    households = []
    for i, (size, adult_count) in enumerate(zip(sizes, adults)):
        households.append({
            "IDMEN": f"{tile['idcar_200m']}_{i+1}",
            "TAILLE": size,
            "NB_ADULTES": adult_count,
            "NB_MINEURS": size - adult_count,
            "tile_id": tile['idcar_200m']
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
    total_individuals = int(tile['ind'])
    total_monoparents = int(tile['men_fmp'])
    total_gd_menages = int(tile['men_5ind'])
    total_adults = int(sum(tile[ADULT_AGE_COLUMNS]))
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

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from popdbgen import DATA_DIR, load_FILO, load_BAN, merge_FILO_BAN, round_alea

np.random.seed(1703)

carr200 = load_FILO(territory = "reun", check_coherence = True)
ban = load_BAN(territory = "974")




# %%

ADULT_AGE_COLUMNS: list[str] = ['ind_18_24', 'ind_25_39', 'ind_40_54', 'ind_55_64', 'ind_65_79', 'ind_80p', 'ind_inc']
MINOR_AGE_COLUMNS: list[str] = ['ind_0_3', 'ind_4_5', 'ind_6_10', 'ind_11_17']
HOUSEHOLD_COLUMNS: list[str] = ['men_1ind', 'men_5ind', 'men_prop', 'men_fmp', 'men_coll', 'men_mais']

def name_integer_column(names: list[str]):
    return [s + "i" for s in names]

# les variables individus (âge):
# arrondir aléatoirement tous les comptages
# mise en cohérence:
# somme des âges adultes int est nécessairement >= meni : si pas le cas mettre tirer aléatoirement des catéories d'âges pour les gonfler
# somme des âges a
# somme des âges int = indi:
# si pas le cas et si somme des âges adultes > alors réduire les comptages de certaines catégories
# (aléa uniforme ou aléa en fonction des probas du premier arrondi aléatoire)

carr200i = carr200[ADULT_AGE_COLUMNS + MINOR_AGE_COLUMNS + HOUSEHOLD_COLUMNS].apply(round_alea)
carr200i.columns = name_integer_column(carr200i.columns)
carr200i = pd.concat([carr200[['tile_id','indi','meni','plus18i','moins18i']], carr200i], axis=1)

carr200i["inda"] = carr200i[name_integer_column(ADULT_AGE_COLUMNS + MINOR_AGE_COLUMNS)].sum(axis=1)
carr200i["diff_ind"] = carr200i.indi - carr200i.inda
carr200i["men_adult_inconsist"] = carr200i.meni > carr200i[name_integer_column(ADULT_AGE_COLUMNS)].sum(axis=1)

print(f"Somme des écarts absolus des comptages d'individus {str(carr200i.diff_ind.abs().sum())}")
print(f"Nb de carreaux avec des écarts dans les comptages d'individus {str(sum(carr200i.diff_ind.abs() > 0 ))}")
print(f"Nb de carreaux avec un nb d'adultes insuffisants {str(sum(carr200i.men_adult_inconsist))}")

carr200i[['indi','inda','diff_ind','men_adult_inconsist']].head(10)

# %%
# Gestion d'incohérences des comptages
carr200j = carr200i.copy(deep=True)

for i, row in carr200j.iterrows():
    if row["diff_ind"] == 0 and row["men_adult_inconsist"] == False:
        continue

    # Gestion de la cohérence des âges des individus avec le nb d'individus
    diff = row["diff_ind"]
    if diff > 0: # indi > inda => ajouter des individus dans certaines catégories d'âge
        row["ind_inci"] += diff
    elif diff < 0: # indi < inda => retirer des individus dans certaines catégories d'âge (en priorité la catégorie inconnue)
        inci = row["ind_inci"]
        if inci > 0:
            new_inci = np.maximum(0, inci + diff)
            row["ind_inci"] = new_inci
            diff += (inci - new_inci)

        while diff != 0:
            if sum(row[name_integer_column(ADULT_AGE_COLUMNS)]) > row.meni:
                eligible_categories = [s for s in name_integer_column(ADULT_AGE_COLUMNS + MINOR_AGE_COLUMNS) if s != "ind_inci" and row[s] > 0]
            else:
                eligible_categories = [s for s in name_integer_column(MINOR_AGE_COLUMNS) if s != "ind_inci" and row[s] > 0]

            if diff > 0:
                raise Exception("Le code est absurde !")
            else:
                drawn_cat = np.random.choice(eligible_categories)
                row[drawn_cat] -= 1
                diff += 1

    # Gestion des incohérences résiduelles entre nb d'adultes et nb de ménages
    diff = row.meni - sum(row[name_integer_column(ADULT_AGE_COLUMNS)])
    while diff > 0:
        eligible_categories = [s for s in name_integer_column(MINOR_AGE_COLUMNS) if row[s] > 0]
        drawn_cat = np.random.choice(eligible_categories)
        row[drawn_cat] -=1
        row["ind_inci"] +=1
        diff -= 1

    carr200j.iloc[i] = row

carr200j["plus18i"] = carr200j[name_integer_column(ADULT_AGE_COLUMNS)].sum(axis=1)
carr200j["moins18i"] = carr200j[name_integer_column(MINOR_AGE_COLUMNS)].sum(axis=1)
carr200j["inda"] = carr200j["plus18i"] + carr200j["moins18i"]
carr200j["diff_ind"] = carr200j.indi - carr200j.inda

print(f"Somme des écarts absolus des comptages d'individus {str(carr200j.diff_ind.abs().sum())}")
print(f"Nb de carreaux avec des écarts dans les comptages d'individus {str(sum(carr200j.diff_ind.abs() > 0 ))}")
print(f"Nb de carreaux avec un nb d'adultes insuffisants {str(sum(carr200j.meni > carr200j[name_integer_column(ADULT_AGE_COLUMNS)].sum(axis=1)))}")



# %%
# Gestion des incohérences résiduelles entre nb d'adultes et nb de ménages
# Il y a incohérence qd meni > nb adultes
for i, row in carr200j.iterrows():
    diff = row.meni - sum(row[name_integer_column(ADULT_AGE_COLUMNS)])
    while diff > 0:
        eligible_categories = [s for s in name_integer_column(MINOR_AGE_COLUMNS) if row[s] > 0]
        drawn_cat = np.random.choice(eligible_categories)
        carr200j.loc[i, drawn_cat] -=1
        carr200j.loc[i, "ind_inci"] +=1
        diff -= 1

print(f"Nb de carreaux avec un nb d'adultes insuffisants {str(sum(carr200j.meni > carr200j[name_integer_column(ADULT_AGE_COLUMNS)].sum(axis=1)))}")


# %%
pbs = carr200j.loc[carr200j['diff_ind'] != 0]
pbs[['indi','inda','diff_ind']].head(10)

carr200i.iloc[24][['indi','inda','diff_ind']]

# %%


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

adresses = pd.DataFrame({"x": [], "y": []})
households_df = generate_households(mon_carreau, adresses)

if validate_households(households_df, mon_carreau):
    print("Génération des ménages cohérente avec les données du carreau")
else:
    print("Error: les données générées sont incohérentes avec les informations du carreau.")

print(households_df)
