import geopandas as gpd
import matplotlib.pyplot as plt

file_path = 'data/carreaux_200m_reun.gpkg'
carr200 = gpd.read_file(file_path)

# Coordonnées des points NE et SO
carr200['YNE'] = carr200['idcar_200m'].str.extract(r'200mN(.*?)E').astype(int)
carr200['XNE'] = carr200['idcar_200m'].str.extract(r'.*E(.*)').astype(int)
carr200['YSO'] = carr200['YNE']-200
carr200['XSO'] = carr200['XNE']+200

print(carr200[['idcar_200m', 'YNE', 'XNE', 'YSO', 'XSO']].head(10))

# Carte de population
carr200['ind'] = carr200['ind'].astype(int)

fig, ax = plt.subplots(1, 1, figsize=(10, 10))
carr200.plot(column='ind', ax=ax, legend=True, cmap='OrRd', legend_kwds={'label': "Population par carreaux"})
plt.title('Carte de la population par carreaux')
plt.show()