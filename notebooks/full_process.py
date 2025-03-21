# %%
# 1- Imports
import time
from popdbgen import (
    DATA_DIR,
    load_FILO,
    load_BAN,
    territory_epsg,
    generate_households,
    get_households_gdf,
    get_population_gdf,
    get_households_population_gdf,
)
TERRITORY = "974"

# %%
# 2- Load FILO
start_time = time.perf_counter_ns()

filo = load_FILO(TERRITORY)

end_time = time.perf_counter_ns()
print(f"load_FILO: {(end_time - start_time)/1_000_000_000:.2f} seconds")

# %%
# 3- Load BAN
start_time = time.perf_counter_ns()

ban = load_BAN(TERRITORY)

end_time = time.perf_counter_ns()
print(f"load_BAN: {(end_time - start_time)/1_000_000_000:.2f} seconds")

# %%
# 3b- Debug
import pandas as pd
from popdbgen import download_BAN, load_raw_FILO, filo_crs, territory_crs
from pyproj import Transformer

FILO_CRS = filo_crs(TERRITORY)
BAN_CRS = territory_crs(TERRITORY)
FILO_TO_BAN = Transformer.from_crs(FILO_CRS, BAN_CRS)
BAN_TO_FILO = Transformer.from_crs(BAN_CRS, FILO_CRS)

ban_file = download_BAN(TERRITORY)

# %%
filo[:10000].tile_id.str.extract('200mN(.*)E(.*)').astype(float).describe()
# %%
ban[:10000].tile_id.str.extract('200mN(.*)E(.*)').astype(float).describe()

# %%
raw_ban = pd.read_csv(ban_file, sep=";")
raw_filo = load_raw_FILO(TERRITORY)


# %%
# 4- Generate households database
start_time = time.perf_counter_ns()

households, population = get_households_population_gdf(filo_df=filo, ban_df=ban)

end_time = time.perf_counter_ns()
print(f"Generate population and households: {(end_time - start_time)/1_000_000_000:.2f} seconds")

# %%
# 5- Export to GeoPackage
start_time = time.perf_counter_ns()

households.to_file(DATA_DIR / f"households_{TERRITORY}.gpkg", driver="GPKG")
population.to_file(DATA_DIR / f"population_{TERRITORY}.gpkg", driver="GPKG")

end_time = time.perf_counter_ns()
print(f"Export generated databases to GeoPackage: {(end_time - start_time)/1_000_000_000:.2f} seconds")


# %%
# 6- Plot refined FILO data
import matplotlib.pyplot as plt

fig, ax = plt.subplots(1, 1, figsize=(20, 20))
filo.plot(column="ind", ax=ax, legend=True, cmap="OrRd", legend_kwds={"label": "Population par carreaux"})
plt.title("Carte de la population par carreaux")
plt.show()

# %%
# 7- Plot households
fig, ax = plt.subplots(1, 1, figsize=(20, 20))
households.plot(markersize=1, ax=ax, legend=True, column="SIZE")
plt.title("Carte de la base de ménages générée")
plt.show()

# %%
# 7- Plot population
fig, ax = plt.subplots(1, 1, figsize=(20, 20))
population.plot(markersize=1, ax=ax, legend=True, column="AGE")
plt.title("Carte de la base de population générée")
plt.show()

# %%
