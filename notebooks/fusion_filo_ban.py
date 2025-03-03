# %%
import sys
import time
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from pgms.fun_generer_base_indiv import generer_table_individus
from pgms.fun_fusionner_ban_filo import intersect_ban_avec_carreaux
from pgms.utils import DATA_DIR

file_path = DATA_DIR / "carreaux_200m_reun.gpkg"

np.random.seed(1703)

BAN_974_URL = "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-974.csv.gz"

# ETAPE 1: base individuelle à partir des carreaux
#file_path = "../data//carreaux_200m_reun.gpkg"
carr200 = gpd.read_file(file_path)

# Coordonnées des points NE et SO - le point de référence est le point en bas à gauche
carr200["YSO"] = carr200["idcar_200m"].str.extract(r"200mN(.*?)E").astype(int)
carr200["XSO"] = carr200["idcar_200m"].str.extract(r".*E(.*)").astype(int)
carr200["YNE"] = carr200["YSO"] + 200
carr200["XNE"] = carr200["XSO"] + 200

print(carr200[["idcar_200m", "YNE", "XNE", "YSO", "XSO"]].head(10))

# Variables d'intérêt
# vérifier que les variables sont bien des entiers sinon arrondir aux entiers
non_integer_ind_count = (carr200["ind"] - np.floor(carr200["ind"]) != 0).sum()
print(f"Number of non integer individual count (should be 0): {non_integer_ind_count}")

def round_alea(x: pd.Series):
    xfl = np.floor(x)
    xdec = x - xfl
    xres = np.zeros(len(x))
    for i in range(len(xres)):
        xres[i] = xfl[i] + np.random.choice(np.array((0, 1)), 1, p=[1 - xdec[i], xdec[i]])
    return xres.astype("int")

carr200["indi"] = round_alea(carr200["ind"])
carr200["meni"] = round_alea(carr200["men"])
carr200["meni"] = carr200.meni.where(carr200.meni <= carr200.indi, carr200.meni - 1)
carr200["meni"] = carr200.meni.where(carr200.men > 1, 1)
carr200["moins18i"] = round_alea(carr200.ind_0_3 + carr200.ind_4_5 + carr200.ind_6_10 + carr200.ind_11_17)
carr200["moins18i"] = carr200.moins18i.where(carr200.moins18i <= carr200.indi, carr200.moins18i - 1)
carr200["plus18i"] = carr200.indi - carr200.moins18i

# print(carr200[['ind', 'indi', 'meni']])
# sum(carr200['meni'] == 0)
print(f"Incohérence: {str(sum(carr200.meni > carr200.indi))}")
print(f"Différence entre les pop: {str(carr200['indi'].sum() - carr200['ind'].sum())}")
print(f"Différence entre les men: {str(carr200['meni'].sum() - carr200['men'].sum())}")

start_time = time.time()

individus_table = generer_table_individus(
    carreaux=carr200, id="idcar_200m", ind="indi", men="meni", moins18="moins18i", plus18="plus18i"
)

end_time = time.time()

print(f"Temps de calcul : {end_time - start_time:.2f} secondes")
print(f"Nombre total d'individus à générer : {str(carr200['indi'].sum())}")
print(f"Nombre total d'individus générés : {individus_table.shape[0]}")

start_time = time.time()

individus_table = generer_table_individus(
    carreaux=carr200, id="idcar_200m", ind="indi", men="meni", moins18="moins18i", plus18="plus18i"
)

end_time = time.time()

print(f"Temps de calcul : {end_time - start_time:.2f} secondes")
print(f"Nombre total de ménages à générer : {str(carr200['meni'].sum())}")
print(f"Nombre total de ménages générés : {individus_table.IDMEN.nunique()}")

# Test : il y a au moins un adulte dans chacun des ménages
adultes_par_menages = individus_table.groupby(['IDMEN', 'ADULTE']).size().reset_index(name='n')
adultes_par_menages['n_ind'] = adultes_par_menages.groupby('IDMEN')['n'].transform('sum')
adultes_par_menages['part'] = adultes_par_menages.n/adultes_par_menages.n_ind
menages_pbtiques = adultes_par_menages[
    (adultes_par_menages['ADULTE'] == False) &
    (adultes_par_menages['part'] >= 1)
]
menages_pbtiques.shape[0] == 0 # True attendu

# fusion pour récupérer les coordonnées des carreaux
individus_table = individus_table.merge(carr200[["idcar_200m", "XNE", "XSO", "YNE", "YSO"]])
# individus_table.columns

menages_table = individus_table[["IDMEN", "idcar_200m", "XNE", "XSO", "YNE", "YSO"]].drop_duplicates(inplace=False)
# menages_table.columns
# menages_table.shape[0] == carr200["meni"].sum()

# %%
ban = pd.read_csv(BAN_974_URL, sep=";")

ban_carr = intersect_ban_avec_carreaux(
    ban,
    carr200,
    "idcar_200m"
)
ban_carr = ban_carr.merge(
    carr200[['idcar_200m','meni']],
    right_on='idcar_200m', left_on='idcar_200m'
)

echantillon_points = (
    ban_carr.groupby('idcar_200m')
    .apply(lambda group: group.sample(n=group['meni'].iloc[0], replace=True, random_state=42))
    .reset_index(drop=True)
)
echantillon_points['IDMEN'] = (
    echantillon_points['idcar_200m'].astype(str) + "_" +
    (echantillon_points.groupby('idcar_200m').cumcount()+1).astype(str)
)
# %%
echantillon_points.columns
# %%
echantillon_points.shape
# %%

# %%
print(echantillon_points.shape[0] - sum(carr200.meni))
# %%
echantillon_points.head(n=20)
# %%
individus_table2 = individus_table[['idcar_200m','IDMEN','ID','ADULTE']].merge(
    echantillon_points,
    right_on=['idcar_200m','IDMEN'],
    left_on=['idcar_200m','IDMEN']
)
# %%
individus_table2.shape
# %%
individus_table2.columns
# %%
individus_table2.head(n=20)
# %%
sum(pd.isna(individus_table2.IDMEN))
# %%
