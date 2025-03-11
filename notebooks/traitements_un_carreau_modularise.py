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
from popdbgen import DATA_DIR, get_FILO_filename, download_extract_FILO, refine_FILO, load_BAN, merge_FILO_BAN, generate_households, generate_individuals


# MIN_HOUSEHOLD_SIZE = 1
# MAX_HOUSEHOLD_SIZE = 5
# ADULT_AGE_COLUMNS_INT: list[str] = ['ind_18_24i', 'ind_25_39i', 'ind_40_54i', 'ind_55_64i', 'ind_65_79i', 'ind_80pi', 'ind_inci']
# MINOR_AGE_COLUMNS_INT: list[str] = ["ind_0_3i", "ind_4_5i", "ind_6_10i", "ind_11_17i"]

# AGES = {'CATAGE' : ADULT_AGE_COLUMNS_INT + MINOR_AGE_COLUMNS_INT}
# AGES['LIM'] = [re.findall(r'\d+', cat) if cat != 'ind_inci' else ['18', '80'] for cat in AGES['CATAGE']]
# AGES['INF'] = [int(lim[0]) for lim in AGES['LIM']]
# AGES['SUP'] = [int(lim[1]) if len(lim) == 2 else 105 for lim in AGES['LIM']]

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
# 2- Tests de la génération de la base de ménages

start_time = time.time()

np.random.seed(1234)
hh = []
for i in range(carr200i.shape[0]):
    tile = carr200i.iloc[i]
    addresses = ban.loc[ban.tile_id == tile.tile_id]
    hh.append(generate_households(tile, addresses))

end_time = time.time()
print(f"Temps de calcul : {end_time - start_time:.2f} secondes")

hhd = pd.concat(hh)

res=pd.concat([
    pd.DataFrame(hhd.groupby(['tile_id'])['NB_ADULTES'].sum().reset_index(name='n1')),
    pd.DataFrame(carr200i[['ind_18_24i', 'ind_25_39i', 'ind_40_54i', 'ind_55_64i', 'ind_65_79i', 'ind_80pi', 'ind_inci']].sum(axis=1).reset_index(name='n2'))
], axis = 1)

print(res.loc[res.n1 != res.n2]) #empty expected

# %%
# 3- Test de la génération de la base individus
start_time = time.time()
n = carr200i.shape[0]

np.random.seed(118218)
indiv = []
for i in range(n):
    # print(i)
    tile = carr200i.iloc[i]
    addresses = ban.loc[ban.tile_id == tile.tile_id]
    indiv.append(generate_individuals(tile, addresses))

end_time = time.time()
print(f"Temps de calcul : {end_time - start_time:.2f} secondes")

indivd = pd.concat(indiv)

print(indivd.shape[0] - carr200i.iloc[0:n].indi.sum())
print(indivd['IDMEN'].nunique() - carr200i.iloc[0:n].meni.sum())


ADULT_AGE_COLUMNS_INT: list[str] = ['ind_18_24i', 'ind_25_39i', 'ind_40_54i', 'ind_55_64i', 'ind_65_79i', 'ind_80pi', 'ind_inci']
MINOR_AGE_COLUMNS_INT: list[str] = ["ind_0_3i", "ind_4_5i", "ind_6_10i", "ind_11_17i"]

print(indivd["CATAGE"].value_counts())
print(carr200i[ADULT_AGE_COLUMNS_INT + MINOR_AGE_COLUMNS_INT].sum())
# %%
