# %%
import sys
import time
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pgms import DATA_DIR, generer_table_individus

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
carr200["indi"] = round_alea(carr200["ind"])
carr200["meni"] = np.maximum(1, np.minimum(carr200.indi, round_alea(carr200["men"])))
carr200["moins18i"] = np.minimum(
    round_alea(carr200.ind_0_3 + carr200.ind_4_5 + carr200.ind_6_10 + carr200.ind_11_17),
    carr200.indi
)
carr200["plus18i"] = carr200.indi - carr200.moins18i

def pp_difference(a,b):
    suma = a.sum()
    sumb = b.sum()
    return f"{suma - sumb} ({(suma - sumb)/max(suma,sumb):.2%})"
def pp_nb_difference(a,b):
    nbdiff = (a != b).sum()
    return f"{nbdiff} ({nbdiff/len(a):.2%})"
print(f"Population difference:", pp_difference(carr200['indi'], carr200['ind']))
print(f"Tiles with pop diff:", pp_nb_difference(carr200['indi'], carr200['ind']))
print(f"Housholds difference:", pp_difference(carr200['meni'], carr200['men']))
print(f"Tiles with hh diff:", pp_nb_difference(carr200['meni'], carr200['men']))


# %%
BAN_974_URL = "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-974.csv.gz"
raw_ban = pd.read_csv(BAN_974_URL, sep=";", usecols=["x","y"])
raw_ban["idcar_200m"] = \
    "CRS2975RES200mN" + \
    (200 * np.floor(raw_ban.y / 200).astype(int)).astype(str) + \
    "E" + \
    (200 * np.floor(raw_ban.x / 200).astype(int)).astype(str)

# Shuffle addresses among each tiles
ban = raw_ban.groupby('idcar_200m', group_keys=False).apply(lambda x: x.sample(frac=1)).reset_index(drop=True)
del raw_ban
# Precompute the number of addresses in each tile
nb_addr = ban.groupby('idcar_200m').size().reset_index(name='addr')

df = carr200.merge(nb_addr, on="idcar_200m", how="left").fillna(0)


# %%
print(f"Total number of households: { df.meni.sum() }")
print(f"Total number of addresses: { df.addr.sum() } ({ df.addr.sum() / df.meni.sum():.2%})")

no_addr = (df.addr == 0) & (df.meni > 0)
print(f"Tiles with >0 households but 0 address: { no_addr.sum() } ({ no_addr.sum() / len(df):.2%})")
print(f"Number of households on these tiles: {  df.meni[no_addr].sum() } ({ df.meni[no_addr].sum() / df.meni.sum():.2%})")

few_addr = df.addr.between(0, df.meni, inclusive='neither')
print(f"Other tiles with strictly more households than addresses: { few_addr.sum() } ({ few_addr.sum() / len(carr200):.2%})")
print(f"Number of extra households on these tiles:  { (df.meni[few_addr]-df.addr[few_addr]).sum() } ({ (df.meni[few_addr]-df.addr[few_addr]).sum() / df.meni.sum():.2%})")


# %% Generate extra artificial addresses to complete BAN on empty tiles

df_no_addr = df[no_addr]["idcar_200m"]
extra_ban = pd.DataFrame({
        "idcar_200m": df_no_addr,
        "x": df_no_addr.str.extract(r"200mN(.*?)E").astype(int)[0] + pd.Series(np.random.rand(no_addr.sum())*200, index=df_no_addr.index),
        "y": df_no_addr.str.extract(r".*E(.*)").astype(int)[0] + pd.Series(np.random.rand(no_addr.sum())*200, index=df_no_addr.index)
    })

ban = pd.concat([ban, extra_ban], ignore_index=True)
ban["id_addr"] = ban.groupby('idcar_200m').cumcount()

# %%
# Create a households database by duplicating each line of the tiled df by its number of households
households = df.loc[df.index.repeat(df.meni)]
# We have: len(households) == df.meni.sum()
households["id_addr"] = households.groupby('idcar_200m').cumcount() % households['addr']



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
