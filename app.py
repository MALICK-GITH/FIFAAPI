# =====================
# Imports externes
# =====================
from flask import Flask, jsonify
import requests
import time
import os

# =====================
# Utils (fetcher.py)
# =====================
def fetch_json_data():
    url = "https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=50&lng=fr"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        log_request(url, response.status_code)
        return response.json()
    except requests.RequestException as e:
        log_request(url, "error")
        return {"error": str(e)}

def fetch_odds(sport_id=85):
    url = f"https://1xbet.com/LiveFeed/Get1x2_VZip?sports={sport_id}&count=50&lng=fr"
    try:
        response = requests.get(url)
        response.raise_for_status()
        log_request(url, response.status_code)
        return response.json()
    except requests.RequestException as e:
        log_request(url, "error")
        return {"error": str(e)}

def check_site_status():
    url = "https://1xbet.com"
    try:
        response = requests.get(url, timeout=5)
        return {"status": "online", "code": response.status_code}
    except requests.RequestException:
        return {"status": "offline", "code": None}

def log_request(endpoint, status):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Request to {endpoint} → Status: {status}")

def log_json_error(data, endpoint):
    print(f"[ERREUR STRUCTURE JSON] Endpoint: {endpoint} | Data reçue: {str(data)[:500]}")

# =====================
# Services (formatter.py, predictor.py, parser.py)
# =====================
def format_odds(odds):
    formatted = []
    for o in odds:
        formatted.append({
            "type": o.get("T"),
            "group": o.get("G"),
            "value": o.get("C"),
            "handicap": o.get("P", None),
            "outcome": o.get("O")
        })
    return formatted

def predict_best_odds(odds_list):
    if not odds_list:
        return None
    sorted_odds = sorted(odds_list, key=lambda o: o.get("C", 0), reverse=True)
    best = sorted_odds[0]
    return {
        "type": best.get("T"),
        "group": best.get("G"),
        "value": best.get("C"),
        "handicap": best.get("P", None)
    }

def extract_match_data(json_obj):
    matches = []
    for entry in json_obj.get("Value", []):
        match = {
            "event_id": entry.get("I"),
            "teams": {
                "team1": entry.get("O1"),
                "team2": entry.get("O2")
            },
            "odds": entry.get("E", []),
            "handicaps": entry.get("AE", []),
            "score": entry.get("SC", {}),
            "league": entry.get("L", ""),
            "country": entry.get("CO", ""),
            "status": entry.get("C", 0)
        }
        matches.append(match)
    return matches

# =====================
# Models (match.py)
# =====================
class Match:
    def __init__(self, entry):
        # Vérification de la structure minimale
        if not isinstance(entry, dict):
            raise ValueError("Entrée de match invalide : ce n'est pas un dictionnaire")
        self.event_id = entry.get("I", None)
        self.team1 = entry.get("O1", "Inconnu")
        self.team2 = entry.get("O2", "Inconnu")
        self.score_raw = entry.get("SC", {})
        self.odds_raw = entry.get("E", [])
        self.handicaps = entry.get("AE", [])
        self.league = entry.get("L", "")
        self.sport_id = entry.get("SP", None)
        self.country = entry.get("CO", "")
        self.status = entry.get("C", 0)
        # Traitements enrichis
        self.odds = format_odds(self.odds_raw)
        self.best_bet = predict_best_odds(self.odds_raw)
        self.score = self._parse_score(self.score_raw)

    def _parse_score(self, score_data):
        try:
            ts = score_data.get("TS", {})
            return {
                "team1": ts.get("O1", "0"),
                "team2": ts.get("O2", "0")
            }
        except Exception:
            return {"team1": "N/A", "team2": "N/A"}

    def get_teams(self):
        return f"{self.team1} vs {self.team2}"

    def is_live(self):
        return self.status == 1

    def summary(self):
        return {
            "event_id": self.event_id,
            "teams": self.get_teams(),
            "score": self.score,
            "league": self.league,
            "country": self.country,
            "is_live": self.is_live(),
            "best_bet": self.best_bet,
            "odds": self.odds
        }

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "team1": self.team1,
            "team2": self.team2,
            "score": self.score,
            "league": self.league,
            "sport_id": self.sport_id,
            "country": self.country,
            "handicaps": self.handicaps,
            "odds": self.odds,
            "best_bet": self.best_bet,
            "status": self.status
        }

# =====================
# Application Flask (fifa_api.py)
# =====================
app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "message": "🎮 FIFA Doublon Bot est actif",
        "api_endpoints": ["/matches", "/live", "/predict", "/status"]
    })

@app.route("/status")
def status():
    check = check_site_status()
    return jsonify(check)

@app.route("/matches")
def all_matches():
    data = fetch_json_data()
    if "error" in data:
        return jsonify({"error": data["error"]}), 500
    if "Value" not in data or not isinstance(data["Value"], list):
        log_json_error(data, "/matches")
        return jsonify({"error": "Structure JSON inattendue pour /matches"}), 500
    try:
        result = [Match(entry).summary() for entry in data["Value"]]
    except Exception as e:
        log_json_error(data, "/matches")
        return jsonify({"error": f"Erreur lors du traitement des matchs : {str(e)}"}), 500
    return jsonify(result)

@app.route("/live")
def live_matches():
    data = fetch_json_data()
    if "error" in data:
        return jsonify({"error": data["error"]}), 500
    if "Value" not in data or not isinstance(data["Value"], list):
        log_json_error(data, "/live")
        return jsonify({"error": "Structure JSON inattendue pour /live"}), 500
    live_games = []
    try:
        for entry in data["Value"]:
            match = Match(entry)
            if match.is_live():
                live_games.append(match.summary())
    except Exception as e:
        log_json_error(data, "/live")
        return jsonify({"error": f"Erreur lors du traitement des matchs en direct : {str(e)}"}), 500
    return jsonify(live_games)

@app.route("/predict")
def best_predictions():
    data = fetch_json_data()
    if "error" in data:
        return jsonify({"error": data["error"]}), 500
    if "Value" not in data or not isinstance(data["Value"], list):
        log_json_error(data, "/predict")
        return jsonify({"error": "Structure JSON inattendue pour /predict"}), 500
    predictions = []
    try:
        for entry in data["Value"]:
            match = Match(entry)
            if match.best_bet:
                predictions.append({
                    "match": match.get_teams(),
                    "prediction": match.best_bet
                })
    except Exception as e:
        log_json_error(data, "/predict")
        return jsonify({"error": f"Erreur lors du traitement des prédictions : {str(e)}"}), 500
    return jsonify(predictions)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port) 
