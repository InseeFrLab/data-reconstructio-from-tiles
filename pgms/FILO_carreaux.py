import os
import zipfile

import py7zr
import requests

# URL du fichier à télécharger
url = "https://www.insee.fr/fr/statistiques/fichier/7655475/Filosofi2019_carreaux_200m_gpkg.zip"
# Répertoire pour enregistrer le fichier téléchargé
data_dir = "data"
# Chemin pour enregistrer le fichier zip téléchargé
zip_path = os.path.join(data_dir, "carreaux_200m.7z")

# Créer le répertoire data s'il n'existe pas
os.makedirs(data_dir, exist_ok=True)

# Télécharger le fichier
response = requests.get(url)
with open(zip_path, "wb") as file:
    file.write(response.content)

# Dézipper le fichier
with zipfile.ZipFile(zip_path, "r") as zip_ref:
    zip_ref.extractall(data_dir)

# Supprimer le fichier zip après extraction
os.remove(zip_path)

# Chemin pour enregistrer le fichier 7z téléchargé
seven_zip_path = os.path.join(data_dir, "Filosofi2019_carreaux_200m_gpkg.7z")

# Dézipper le fichier 7z
with py7zr.SevenZipFile(seven_zip_path, mode="r") as z:
    z.extractall(path=data_dir)

# Supprimer le fichier 7z après extraction
os.remove(seven_zip_path)

print("Téléchargement et extraction terminés.")
