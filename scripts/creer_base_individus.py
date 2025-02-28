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
from pgms.utils import DATA_DIR

file_path = DATA_DIR / "carreaux_200m_reun.gpkg"

np.random.seed(1703)


def round_alea(x: pd.Series):
    xfl = np.floor(x).astype("int")
    return xfl + (np.random.rand(x.size) < x - xfl)


# %%
carr200 = gpd.read_file(file_path)


# %%
fig, ax = plt.subplots(1, 1, figsize=(10, 10))
carr200.plot(column="ind", ax=ax, legend=True, cmap="OrRd", legend_kwds={"label": "Population par carreau"})
plt.title("Carte de la population par carreaux")


# %%
# Coordonnées des points NE et SO
carr200["YNE"] = carr200["idcar_200m"].str.extract(r"200mN(.*?)E").astype(int)
carr200["XNE"] = carr200["idcar_200m"].str.extract(r".*E(.*)").astype(int)
carr200["YSO"] = carr200["YNE"] - 200
carr200["XSO"] = carr200["XNE"] - 200

carr200[["idcar_200m", "YNE", "XNE", "YSO", "XSO", "ind"]]


# %%
(carr200[["ind"]] - np.floor(carr200[["ind"]])).hist()
# NOTE : La pop de plusieurs carreaux a un partie décimale égale à 0.5
# (Points de population qui tombe à la frontière peut-être...)

# Variables d'intérêt
# vérifier que les variables sont bien des entiers sinon arrondir aux entiers
non_integer_ind_count = (carr200["ind"] - np.floor(carr200["ind"]) != 0).sum()
print(f"Number of non integer individual count (should be 0): {non_integer_ind_count}")


# %%
carr200[["ind"]].apply(np.floor).hist(bins=50)


# %%
carr200["indi"] = round_alea(carr200["ind"])
carr200["meni"] = np.maximum(1, np.minimum(carr200.indi, round_alea(carr200["men"])))
carr200["moins18i"] = np.minimum(
    round_alea(carr200.ind_0_3 + carr200.ind_4_5 + carr200.ind_6_10 + carr200.ind_11_17), carr200.indi
)
carr200["plus18i"] = carr200.indi - carr200.moins18i

# print(carr200[['ind', 'indi', 'meni']])
sum(carr200["meni"] == 0)
print(f"Incohérence: {str(sum(carr200['meni'] > carr200.indi))}")
print(f"Différence entre les pop: {str(carr200['indi'].sum() - carr200['ind'].sum())}")
print(f"Différence entre les men: {str(carr200['meni'].sum() - carr200['men'].sum())}")


# %%

BAN_974_URL = "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-974.csv.gz"
ban = pd.read_csv(BAN_974_URL, sep=";")


# %%
ban["XNE"] = 200 * np.floor(ban.x / 200).astype(int)
ban["YNE"] = 200 * np.floor(ban.y / 200).astype(int)
ban["idcar_200m"] = ban.apply(lambda row: f"CRS2975RES200mN{row['YNE']}E{row['XNE']}", axis=1)


# %%
# Perform an outer merge to identify common and unique values
merged = ban.merge(carr200, on="idcar_200m", how="outer", indicator=True)

# Count occurrences
print(f"BAN adresses that do not fit in a tile: {(merged['_merge'] == 'left_only').sum()}")
print(f"Tiles with not BAN adress: {(merged['_merge'] == 'right_only').sum()}")
print(f"Adresses with a tile: {(merged['_merge'] == 'both').sum()}")

ban[["idcar_200m", "id"]].groupby("idcar_200m").count()["id"].hist()


# %%
start_time = time.time()

individus_table = generer_table_individus(
    carreaux=carr200, id="idcar_200m", ind="indi", men="meni", moins18="moins18i", plus18="plus18i"
)

end_time = time.time()

print(f"Temps de calcul : {end_time - start_time:.2f} secondes")
print(f"Nombre total d'individus générés : {len(individus_table)}")
print(f"Nombre total de ménages générés : {len(individus_table)}")

# %%
# fusion pour récupérer les coordonnées des carreaux
individus_table = individus_table.merge(carr200[["idcar_200m", "XNE", "XSO", "YNE", "YSO"]])
# individus_table.columns

menages_table = individus_table[["IDMEN", "idcar_200m", "XNE", "XSO", "YNE", "YSO"]].drop_duplicates(inplace=False)
# menages_table.columns
# menages_table.shape[0] == carr200["meni"].sum()

# Tirage de coordonnées dans le carreau
menages_table["X_men"] = menages_table.apply(lambda row: np.random.randint(row["XSO"], row["XNE"] + 1), axis=1)
menages_table["Y_men"] = menages_table.apply(lambda row: np.random.randint(row["YSO"], row["YNE"] + 1), axis=1)

# Injection des coordonnées dans la table individuelle
individus_table2 = individus_table.merge(menages_table[["IDMEN", "X_men", "Y_men"]], left_on="IDMEN", right_on="IDMEN")
# individus_table2.columns

pd.set_option("display.max_columns", 8)
print(individus_table2.head())

# Create a GeoDataFrame from the individuals table
geometry = gpd.points_from_xy(individus_table2["X_men"], individus_table2["Y_men"])
individus_gdf = gpd.GeoDataFrame(individus_table2, geometry=geometry)

# Plot the density maps side by side
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))

# Plot the density map from the individuals table
individus_gdf.plot(ax=ax1, markersize=1, alpha=0.5)
ax1.set_title("Carte de densité de population (individus)")

# Plot the density map from the carr200 table without legend
carr200.plot(column="indi", ax=ax2, cmap="OrRd")
ax2.set_title("Carte de densité de population (carreaux)")

plt.show()

# %% Export
individus_table2.to_csv(DATA_DIR / "individus_table2.csv", index=False)
individus_gdf.to_file(DATA_DIR / "individus_gdf.gpkg", driver="GPKG")
