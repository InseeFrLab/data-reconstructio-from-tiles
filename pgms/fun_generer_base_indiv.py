import numpy as np
import pandas as pd


def generer_table_individus(
    carreaux: pd.DataFrame, id: str, ind: str, men: str, moins18: str, plus18: str
) -> pd.DataFrame:
    """
    Génère une table individuelle à partir d'une table carroyée.

    Arguments :
        carreaux (pd.DataFrame) : DataFrame contenant les données carroyées.
        id (str) : Nom de la variable identifiant chaque carreau.
        ind (str) : Nom de la variable indiquant le nombre total d'individus par carreau.
        men (str) : Nom de la variable indiquant le nombre de ménages par carreau.
        moins18 (str) : Nom de la variable indiquant le nombre d'individus de moins de 18 ans par carreau.
        plus18 (str) : Nom de la variable indiquant le nombre d'individus de 18 ans ou plus par carreau.

    Retourne :
        pd.DataFrame : Table individuelle contenant les colonnes suivantes :
            - ID : Identifiant unique pour chaque individu.
            - IDMEN : Identifiant du ménage auquel appartient l'individu.
            - ADULTE : Booléen indiquant si l'individu est adulte (True) ou non (False).
            - [id] : Identifiant du carreau repris depuis la table initiale.
    """
    # Vérification des contraintes
    if not all(carreaux[moins18] + carreaux[plus18] == carreaux[ind]):
        raise ValueError("Le total des individus (moins18 + plus18) ne correspond pas à la colonne ind.")

    if not all(carreaux[men] <= carreaux[ind]):
        raise ValueError("Le nb d'individus n'est pas systématiquement supérieur au nb de ménages")

    # Liste pour stocker les données individuelles
    individus_data = []

    # Boucle vectorisée sur chaque carreau
    for _, row in carreaux.iterrows():
        # Identifiants du carreau et nombre d'entités
        carreau_id = row[id]
        num_individus = row[ind]
        num_menages = row[men]
        num_moins18 = row[moins18]
        num_plus18 = row[plus18]

        # Générer les identifiants des ménages
        menage_ids = np.repeat(np.arange(1, num_menages + 1), num_individus // num_menages)

        # Compléter si le nombre d'individus n'est pas divisible par le nombre de ménages
        remaining = num_individus % num_menages
        if remaining > 0:
            menage_ids = np.append(menage_ids, np.random.choice(np.arange(1, num_menages + 1), remaining))

        # Mélanger les ménages pour éviter tout biais systématique
        np.random.shuffle(menage_ids)

        # Créer les indicateurs adultes (<18 ou >=18)
        adultes_flags = np.concatenate([np.zeros(num_moins18, dtype=bool), np.ones(num_plus18, dtype=bool)])

        # Mélanger les individus aléatoirement tout en respectant leur statut d'âge
        np.random.shuffle(adultes_flags)

        # Ajouter les données dans la liste finale
        for i in range(num_individus):
            individus_data.append(
                {
                    "ID": f"{carreau_id}_{i+1}",  # Identifiant unique de l'individu
                    "IDMEN": f"{carreau_id}_{menage_ids[i]}",  # Identifiant du ménage
                    "ADULTE": adultes_flags[i],  # Booléen adulte ou non
                    id: carreau_id,  # Identifiant du carreau
                }
            )

    # Convertir en DataFrame final
    individus_df = pd.DataFrame(individus_data)

    return individus_df
