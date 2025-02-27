import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import os
import sys

sys.path.append(os.path.dirname('pgms/'))
from fun_generer_base_indiv import *

np.random.seed(1703)

file_path = 'data/carreaux_200m_reun.gpkg'
carr200 = gpd.read_file(file_path)

fig, ax = plt.subplots(1, 1, figsize=(10, 10))
carr200.plot(column='ind', ax=ax, legend=True, cmap='OrRd', legend_kwds={'label': "Population par carreaux"})
plt.title('Carte de la population par carreaux')
plt.show()

# Coordonnées des points NE et SO
carr200['YNE'] = carr200['idcar_200m'].str.extract(r'200mN(.*?)E').astype(int)
carr200['XNE'] = carr200['idcar_200m'].str.extract(r'.*E(.*)').astype(int)
carr200['YSO'] = carr200['YNE']-200
carr200['XSO'] = carr200['XNE']-200

print(carr200[['idcar_200m', 'YNE', 'XNE', 'YSO', 'XSO']].head(10))

# Variables d'intérêt
# vérifier que les variables sont bien des entiers sinon arrondir aux entiers
(carr200['ind'] - np.floor(carr200['ind']) != 0).sum() == 0

def round_alea(x: np.array):
    xfl = np.floor(x)
    xdec = x - xfl
    xres = np.zeros(x.__len__())
    for i in range(xres.__len__()):
        xres[i] = xfl[i] + np.random.choice(np.array((0,1)), 1, p=[1-xdec[i], xdec[i]])
    return(xres.astype('int'))

carr200['indi'] = round_alea(carr200['ind'])
carr200['meni'] = round_alea(carr200['men'])
carr200['meni'] = carr200.meni.where(carr200.meni <= carr200.indi, carr200.meni -1)
carr200['meni'] = carr200.meni.where(carr200.men > 1, 1)
carr200['moins18i'] = round_alea(carr200.ind_0_3 + carr200.ind_4_5 + carr200.ind_6_10 + carr200.ind_11_17)
carr200['moins18i'] = carr200.moins18i.where(carr200.moins18i <= carr200.indi, carr200.moins18i -1)
carr200['plus18i'] = carr200.indi - carr200.moins18i

# print(carr200[['ind', 'indi', 'meni']])
sum(carr200['meni'] == 0)
print(f"Incohérence: {str(sum(carr200['meni'] > carr200.indi))}")
print(f"Différence entre les pop: {str(carr200['indi'].sum() - carr200['ind'].sum())}") 
print(f"Différence entre les men: {str(carr200['meni'].sum() - carr200['men'].sum())}") 


start_time = time.time()

individus_table = generer_table_individus(
    carreaux=carr200,
    id="idcar_200m",
    ind="indi",
    men="meni",
    moins18="moins18i",
    plus18="plus18i"
)

end_time = time.time()

print(f"Temps de calcul : {end_time - start_time:.2f} secondes")
print(f"Nombre total d'individus générés : {len(individus_table)}")
print(f"Nombre total de ménages générés : {len(individus_table)}")

# fusion pour récupérer les coordonnées des carreaux
individus_table = individus_table.merge(carr200[['idcar_200m', 'XNE', 'XSO', 'YNE', 'YSO']])
individus_table.columns

menages_table = individus_table[['IDMEN','idcar_200m', 'XNE', 'XSO', 'YNE', 'YSO']].drop_duplicates(inplace=False)
menages_table.columns
menages_table.shape[0] == carr200['meni'].sum()

# Tirage de coordonnées dans le carreau
menages_table['X_men'] = menages_table.apply(lambda row: np.random.randint(row['XSO'], row['XNE'] + 1), axis=1)
menages_table['Y_men'] = menages_table.apply(lambda row: np.random.randint(row['YSO'], row['YNE'] + 1), axis=1)

# Injection des coordonnées dans la table individuelle
individus_table2 = individus_table.merge(menages_table[['IDMEN', 'X_men', 'Y_men']], left_on="IDMEN", right_on="IDMEN")
individus_table2.columns

pd.set_option('display.max_columns', 8)
print(individus_table2.head())


# Create a GeoDataFrame from the individuals table
geometry = gpd.points_from_xy(individus_table2['X_men'], individus_table2['Y_men'])
individus_gdf = gpd.GeoDataFrame(individus_table2, geometry=geometry)

# Plot the density maps side by side
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))

# Plot the density map from the individuals table
individus_gdf.plot(ax=ax1, markersize=1, alpha=0.5)
ax1.set_title('Carte de densité de population (individus)')

# Plot the density map from the carr200 table without legend
carr200.plot(column='indi', ax=ax2, cmap='OrRd')
ax2.set_title('Carte de densité de population (carreaux)')

plt.show()


# Export
individus_table2.to_csv('data/individus_table2.csv', index=False)
individus_gdf.to_file('data/individus_gdf.gpkg', driver='GPKG')
