# %%
# 1- fonctions pour générer la base de ménages carreau par carreau
from typing import Dict, List, Tuple
from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import re
import time
from collections.abc import Generator
from popdbgen import DATA_DIR, get_FILO_filename, download_extract_FILO, refine_FILO, load_BAN, merge_FILO_BAN


MIN_HOUSEHOLD_SIZE = 1
MAX_HOUSEHOLD_SIZE = 5
ADULT_AGE_COLUMNS_INT: list[str] = ['ind_18_24i', 'ind_25_39i', 'ind_40_54i', 'ind_55_64i', 'ind_65_79i', 'ind_80pi', 'ind_inci']
MINOR_AGE_COLUMNS_INT: list[str] = ["ind_0_3i", "ind_4_5i", "ind_6_10i", "ind_11_17i"]

AGES = {'CATAGE' : ADULT_AGE_COLUMNS_INT + MINOR_AGE_COLUMNS_INT}
AGES['LIM'] = [re.findall(r'\d+', cat) if cat != 'ind_inci' else ['18', '80'] for cat in AGES['CATAGE']]
AGES['INF'] = [int(lim[0]) for lim in AGES['LIM']]
AGES['SUP'] = [int(lim[1]) if len(lim) == 2 else 105 for lim in AGES['LIM']]

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
    nb_minors = int(sum(tile[MINOR_AGE_COLUMNS_INT]))
    nb_single_parent = int(tile['men_fmpi'])
    nb_single_parent = nb_single_parent if nb_minors >= nb_single_parent else nb_minors

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

def draw_adresses(tile: pd.Series, addresses: pd.DataFrame) -> List[dict]:
    """Tire un ensemble d'adresses pour chacun des ménages du carreau.

    Args:
        tile (pd.Series): informations sur le carreau
        addresses (pd.DataFrame): adresses contenues dans le carreau

    Returns:
        pd.DataFrame: Coordonnées x, y  des adresses tirées pour les ménages du carreau.
        Contient autant de lignes que le carreau contient de ménages.
    """
    if tile['meni'] == 0:
        return []
    # Si aucune adresses n'est disponible, des points fictifs sont créés au sein du carreau
    if addresses.empty:
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


def generate_households(tile: pd.Series, addresses: pd.DataFrame) -> Generator[dict]:
    """
    Génère une base de ménages d'un carreau
    """
    sizes = generate_household_sizes(tile)
    sizes = adjust_household_sizes(sizes, int(tile['indi']))
    adults = allocate_adults(tile, sizes)

    # Le niveau de vie des individus dans le ménage
    # On répartit le total des niveaux de vie entre les ménages
    # Les niveaux de vie des individus d'un même ménage sont identiques
    parts = np.random.uniform(0, 1, len(sizes)) #tirage uniforme potentiellement trop perturbateur.
    parts = parts/sum(parts)

    niveau_vie_ind_hh = [tile['ind_snv']*p/s for p, s in zip(parts, sizes)]

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
            "NIVEAU_VIE": niveau_vie_ind_hh,
            "x": addr['x'],
            "y": addr['y']
        }

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
# tile = carr200i.iloc[0]
# addresses = ban.loc[ban.tile_id == tile.tile_id]
# households_df = generate_households(tile, addresses)

# if validate_households(households_df, tile):
#     print("Génération des ménages cohérente avec les données du carreau")
# else:
#     print("Error: les données générées sont incohérentes avec les informations du carreau.")

# print(households_df)


# %%
# 4- Génération de la base d'individus à partir d'un carreau et des adresses
def generate_individuals(tile: pd.Series, addresses: pd.DataFrame):

    # Génération de la base de ménages
    hh = generate_households(tile, addresses)
    # Génération d'une base d'individus basée sur la base de ménages
    repeate_idmen = np.repeat(hh['IDMEN'], hh['TAILLE'])
    individual_id = np.concatenate([
        [idmen + '_' + str(i+1) for i in range(n)]
        for n, idmen in zip(hh['TAILLE'], hh['IDMEN'])
    ])
    statut = np.concatenate([
        np.concatenate([np.repeat('adulte', nb_adultes), np.repeat('mineur', nb_mineurs)])
        for nb_adultes, nb_mineurs in zip(hh['NB_ADULTES'], hh['NB_MINEURS'])
    ])

    # Ajout de l'âge
    age_adultes  = np.concatenate([np.repeat(cat, tile[cat]) for cat in ADULT_AGE_COLUMNS_INT])
    if (age_adultes.shape[0] - hh.NB_ADULTES.sum()) != 0:
        print(hh)
    np.random.shuffle(age_adultes)
    age_mineurs  = np.concatenate([np.repeat(cat, tile[cat]) for cat in MINOR_AGE_COLUMNS_INT])
    np.random.shuffle(age_mineurs)

    individuals_df = pd.DataFrame({'ID': individual_id, 'IDMEN': repeate_idmen, 'STATUT': statut, 'CATAGE': ''})
    individuals_df.loc[individuals_df['STATUT'] == 'adulte', 'CATAGE'] = age_adultes
    individuals_df.loc[individuals_df['STATUT'] == 'mineur', 'CATAGE'] = age_mineurs
    individuals_df = individuals_df.merge(pd.DataFrame.from_dict(AGES), on = "CATAGE")

    individuals_df['AGE'] = individuals_df.apply(lambda row: np.random.randint(row['INF'], row['SUP']+1), axis=1)
    individuals_df = individuals_df.drop(['INF', 'SUP', 'LIM'], axis=1)
    # Info sur les ménages
    individuals_df = individuals_df.merge(hh[['tile_id','IDMEN','TAILLE','NIVEAU_VIE', 'MONOPARENT','GRD_MENAGE','x','y']], on = 'IDMEN')
    return individuals_df


# %%
tile = carr200i.iloc[2]
addresses = ban.loc[ban.tile_id == tile.tile_id]
individuals_df = generate_individuals(tile, addresses)

# %%
# 4- Tests des fonctions de génération de la base de ménages


start_time = time.time()
individuals_df_list = []

for i in range(carr200i.shape[0]):
    print(i)
    tile = carr200i.iloc[i]
    addresses = ban.loc[ban.tile_id == tile.tile_id]
    individuals_df_list.append(generate_individuals(tile, addresses))

individuals_df = pd.concat(individuals_df_list)

end_time = time.time()

print(f"Temps de calcul : {end_time - start_time:.2f} secondes")
print(individuals_df.head())

# %%
