import json
import random
from datetime import datetime
import pandas as pd

def charger_donnees(path="historique.json"):
    try:
        with open(path, "r") as fichier:
            return json.load(fichier)
    except FileNotFoundError:
        return {"historique_parties": []}

def predict_position(billes):
    base = {1: ["Gauche", "Centre", "Droite"], 2: ["Gauche", "Droite"]}
    return random.choice(base[billes])

def enregistrer_resultat(billes, position, path="historique.json"):
    data = charger_donnees(path)
    partie = {
        "id": len(data["historique_parties"]) + 1,
        "billes": billes,
        "position_finale": position,
        "timestamp": datetime.now().isoformat()
    }
    data["historique_parties"].append(partie)
    with open(path, "w") as fichier:
        json.dump(data, fichier, indent=4)

def exporter_csv(path_json="historique.json", path_csv="historique.csv"):
    data = charger_donnees(path_json)
    df = pd.DataFrame(data["historique_parties"])
    df.to_csv(path_csv, index=False, encoding="utf-8")
