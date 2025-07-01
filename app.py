import os
import datetime
from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

API_URL = "https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=50&lng=fr&gr=70&mode=4&country=96&getEmpty=true"

def fetch_matches():
    try:
        resp = requests.get(API_URL, timeout=5)
        data = resp.json()
        return data.get("Value", [])
    except Exception:
        return []

def format_match(match):
    date_str = datetime.datetime.fromtimestamp(match.get("S", 0)).strftime('%Y-%m-%d %H:%M') if match.get("S") else None
    return {
        "id": match.get("I"),
        "league": match.get("L"),
        "league_en": match.get("LE"),
        "home_team": match.get("O1"),
        "away_team": match.get("O2"),
        "date": date_str,
        "score": match.get("SC", {}).get("FS", {}),
        "odds": match.get("E", []),
        "home_img": match.get("O1IMG", []),
        "away_img": match.get("O2IMG", [])
    }

@app.route('/')
def home():
    return '/matches\n/leagues\n/match/<id>\n/predict (POST)'

@app.route('/matches', methods=['GET'])
def get_matches():
    matches = fetch_matches()
    return jsonify([format_match(m) for m in matches])

@app.route('/leagues', methods=['GET'])
def get_leagues():
    matches = fetch_matches()
    leagues = list({m.get("L") for m in matches if "L" in m})
    return jsonify(leagues)

@app.route('/match/<int:match_id>', methods=['GET'])
def get_match(match_id):
    matches = fetch_matches()
    match = next((m for m in matches if m.get("I") == match_id), None)
    return jsonify(format_match(match)) if match else ('', 404)

@app.route('/predict', methods=['POST'])
def predict():
    req = request.get_json()
    match_id = req.get('match_id')
    matches = fetch_matches()
    match = next((m for m in matches if m.get("I") == match_id), None)
    if not match or not match.get("E"):
        return jsonify({"error": "Match ou cotes non trouvés"}), 404
    odds = match["E"]
    min_odd = min(odds, key=lambda x: x.get("C", float('inf')))
    winner = match["O1"] if min_odd.get("T") == 1 else match["O2"] if min_odd.get("T") == 2 else "Nul"
    return jsonify({"prediction": winner, "best_odd": min_odd})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 
