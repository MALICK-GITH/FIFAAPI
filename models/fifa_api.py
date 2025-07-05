from flask import Flask, jsonify
from utils.fetcher import fetch_json_data, check_site_status
from models.match import Match

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

    result = [Match(entry).summary() for entry in data.get("Value", [])]
    return jsonify(result)

@app.route("/live")
def live_matches():
    data = fetch_json_data()
    if "error" in data:
        return jsonify({"error": data["error"]}), 500

    live_games = []
    for entry in data.get("Value", []):
        match = Match(entry)
        if match.is_live():
            live_games.append(match.summary())
    return jsonify(live_games)

@app.route("/predict")
def best_predictions():
    data = fetch_json_data()
    if "error" in data:
        return jsonify({"error": data["error"]}), 500

    predictions = []
    for entry in data.get("Value", []):
        match = Match(entry)
        if match.best_bet:
            predictions.append({
                "match": match.get_teams(),
                "prediction": match.best_bet
            })
    return jsonify(predictions)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
