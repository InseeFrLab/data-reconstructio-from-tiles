import gzip
import os
import shutil

import requests

# URL du fichier de la base d'adresses nationale
url = "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-france.csv.gz"

# Nom du dossier où le fichier sera stocké
data_folder = "data"

# Créer le dossier s'il n'existe pas
if not os.path.exists(data_folder):
    os.makedirs(data_folder)

# Chemin complet du fichier à télécharger
file_path = os.path.join(data_folder, "adresses.csv.gz")

# Télécharger le fichier
response = requests.get(url, stream=True)
if response.status_code == 200:
    with open(file_path, "wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)
    print(f"Fichier téléchargé avec succès et stocké dans {file_path}")
else:
    print(f"Échec du téléchargement. Statut de la réponse : {response.status_code}")

    # Chemin du fichier décompressé
    decompressed_file_path = os.path.join(data_folder, "adresses.csv")

    # Décompresser le fichier
    with gzip.open(file_path, "rb") as f_in, open(decompressed_file_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

    print(f"Fichier décompressé avec succès et stocké dans {decompressed_file_path}")
