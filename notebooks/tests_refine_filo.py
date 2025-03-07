# %%
from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time

from popdbgen import DATA_DIR, get_FILO_filename, download_extract_FILO, refine_FILO, load_BAN, merge_FILO_BAN

def load_FILO_without_refinement(territory: str = "france", dataDir: Path = DATA_DIR):
    download_extract_FILO()
    file_path = get_FILO_filename(territory, dataDir=dataDir)
    tiled_filo = gpd.read_file(file_path)
    return tiled_filo

np.random.seed(1703)

carr200 = load_FILO_without_refinement(territory = "reun")
ban = load_BAN(territory = "974")


# %%
start_time = time.time()

carr200i = refine_FILO(carr200)

end_time = time.time()

print(f"Temps de calcul : {end_time - start_time:.2f} secondes")

# %%


# %%
