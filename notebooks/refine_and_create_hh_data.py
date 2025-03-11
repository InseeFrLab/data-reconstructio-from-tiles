# %%
# 1- Imports
import geopandas as gpd
import pandas as pd
import time
from popdbgen import generate_households, load_FILO, load_BAN, merge_FILO_BAN


# %%
# Load FILO
start_time = time.perf_counter_ns()

filo: pd.DataFrame = load_FILO("974")

end_time = time.perf_counter_ns()
print(f"load_FILO: {(end_time - start_time)/1_000_000_000:.2f} seconds")

# %%
# Load BAN
start_time = time.perf_counter_ns()

ban: pd.DataFrame = load_BAN("974")

end_time = time.perf_counter_ns()
print(f"load_BAN: {(end_time - start_time)/1_000_000_000:.2f} seconds")

# %%
# Generate households database
start_time = time.perf_counter_ns()

full_hh_database: pd.DataFrame = merge_FILO_BAN(generate_households, filo_df=filo, ban_df=ban)

end_time = time.perf_counter_ns()
print(f"merge_FILO_BAN: {(end_time - start_time)/1_000_000_000:.2f} seconds")

# %%
