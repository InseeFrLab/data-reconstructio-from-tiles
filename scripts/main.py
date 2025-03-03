import time

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pgms import DATA_DIR, generer_table_individus, intersect_ban_avec_carreaux

BAN_974_URL = "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-974.csv.gz"

# ETAPE 1: base individuelle à partir des carreaux
default_file_path = DATA_DIR / "carreaux_200m_reun.gpkg"


def round_alea(x: pd.Series):
    xfl = np.floor(x)
    xdec = x - xfl
    xres = np.zeros(len(x))
    for i in range(len(xres)):
        xres[i] = xfl[i] + np.random.choice(np.array((0, 1)), 1, p=[1 - xdec[i], xdec[i]])
    return xres.astype("int")


def main(file_path=default_file_path):
    np.random.seed(1703)

    carr200 = gpd.read_file(file_path)

    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    carr200.plot(column="ind", ax=ax, legend=True, cmap="OrRd", legend_kwds={"label": "Population par carreaux"})
    plt.title("Carte de la population par carreaux")
    plt.show()

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

    carr200["indi"] = round_alea(carr200["ind"])
    carr200["meni"] = round_alea(carr200["men"])
    carr200["plus18i"] = round_alea(
        carr200.ind_18_24
        + carr200.ind_25_39
        + carr200.ind_40_54
        + carr200.ind_55_64
        + carr200.ind_65_79
        + carr200.ind_80p
    )
    carr200["plus18i"] = carr200.plus18i.where(carr200.plus18i > 0, 1)
    carr200["plus18i"] = carr200.plus18i.where(carr200.plus18i <= carr200.indi, carr200.plus18i - 1)
    carr200["moins18i"] = carr200.indi - carr200.plus18i
    # carr200["meni"] = carr200.meni.where(carr200.meni <= carr200.plus18i, carr200.meni - 1)
    carr200["meni"] = carr200.meni.where(carr200.meni > 1, 1)
    # print(carr200[['ind', 'indi', 'meni']])
    # sum(carr200['meni'] == 0)
    print(f"Incohérence: {str(sum(carr200.meni > carr200.plus18i))}")
    print(f"Différence entre les pop: {str(carr200['indi'].sum() - carr200['ind'].sum())}")
    print(f"Différence entre les men: {str(carr200['meni'].sum() - carr200['men'].sum())}")

    start_time = time.time()

    individus_table = generer_table_individus(
        carreaux=carr200, id="idcar_200m", ind="indi", men="meni", moins18="moins18i", plus18="plus18i"
    )

    end_time = time.time()

    print(f"Temps de calcul pour la génération des individus : {end_time - start_time:.2f} secondes")
    print(f"Nombre total d'individus générés : {len(individus_table)}")

    start_time = time.time()

    individus_table = generer_table_individus(
        carreaux=carr200, id="idcar_200m", ind="indi", men="meni", moins18="moins18i", plus18="plus18i"
    )

    end_time = time.time()

    print(f"Temps de calcul : {end_time - start_time:.2f} secondes")
    print(f"Nombre total d'individus générés : {len(individus_table)}")
    print(f"Nombre total de ménages générés : {len(individus_table)}")

    # fusion pour récupérer les coordonnées des carreaux
    individus_table = individus_table.merge(carr200[["idcar_200m", "XNE", "XSO", "YNE", "YSO"]])
    # individus_table.columns

    # menages_table = individus_table[["IDMEN", "idcar_200m", "XNE", "XSO", "YNE", "YSO"]].drop_duplicates()
    # menages_table.columns
    # menages_table.shape[0] == carr200["meni"].sum()

    ban = pd.read_csv(BAN_974_URL, sep=";")

    start_time = time.time()

    ban_carr = intersect_ban_avec_carreaux(ban, carr200, "idcar_200m")
    ban_carr = ban_carr.merge(carr200[["idcar_200m", "meni"]], right_on="idcar_200m", left_on="idcar_200m")
    echantillon_points = (
        ban_carr.groupby("idcar_200m")
        .apply(lambda group: group.sample(n=group["meni"].iloc[0], replace=True, random_state=42))
        .reset_index(drop=True)
    )

    end_time = time.time()

    print(f"Temps de calcul pour la création des échantillons de points: {end_time - start_time:.2f} secondes")

    echantillon_points["IDMEN"] = (
        echantillon_points["idcar_200m"].astype(str)
        + "_"
        + (echantillon_points.groupby("idcar_200m").cumcount() + 1).astype(str)
    )

    print(f"Ecart du nombre de ménages: {echantillon_points.shape[0] - sum(carr200.meni):.2f} secondes")

    individus_table2 = individus_table[["idcar_200m", "IDMEN", "ID", "ADULTE"]].merge(
        echantillon_points, right_on=["idcar_200m", "IDMEN"], left_on=["idcar_200m", "IDMEN"]
    )

    pd.set_option("display.max_columns", 8)
    print(individus_table2.head())

    geometry = gpd.points_from_xy(individus_table2["x"], individus_table2["y"])
    individus_gdf = gpd.GeoDataFrame(individus_table2, geometry=geometry)

    # Plot the density maps side by side
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))

    # Plot the density map from the individuals table
    individus_gdf.plot(ax=ax1, markersize=0.2, alpha=0.5)
    ax1.set_title("Carte de densité de population (individus)")

    # Plot the density map from the carr200 table without legend
    carr200.plot(column="indi", ax=ax2, cmap="OrRd")
    ax2.set_title("Carte de densité de population (carreaux)")

    plt.show()

    # Export
    individus_table2.to_csv("data/individus_table2.csv", index=False)
    individus_gdf.to_file("data/individus_gdf.gpkg", driver="GPKG")


if __name__ == "__main__":
    main()
