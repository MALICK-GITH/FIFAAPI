from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

API_URL = "https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=50&lng=fr&gr=70&mode=4&country=96&getEmpty=true"

def fetch_matches():
    try:
        resp = requests.get(API_URL, timeout=5)
        data = resp.json()
        return data.get("Value", [])
    except Exception as e:
        return []

@app.route('/matches', methods=['GET'])
def get_matches():
    matches = fetch_matches()
    return jsonify(matches)

@app.route('/match/<int:match_id>', methods=['GET'])
def get_match(match_id):
    matches = fetch_matches()
    match = next((m for m in matches if m['I'] == match_id), None)
    return jsonify(match) if match else ('', 404)

@app.route('/leagues', methods=['GET'])
def get_leagues():
    matches = fetch_matches()
    leagues = {}
    for m in matches:
        if 'LI' in m and 'L' in m and 'LE' in m:
            leagues[m['LI']] = {
                "L": m["L"],
                "LE": m["LE"],
                "LI": m["LI"]
            }
    return jsonify(list(leagues.values()))

@app.route('/predict', methods=['POST'])
def predict():
    req = request.get_json()
    match_id = req.get('match_id')
    matches = fetch_matches()
    match = next((m for m in matches if m['I'] == match_id), None)
    if not match:
        return jsonify({"error": "Match non trouvé"}), 404
    if match.get('E'):
        min_odd = min(match['E'], key=lambda x: x['C'])
        winner = match['O1'] if min_odd['T'] == 1 else match['O2']
        return jsonify({"prediction": winner, "cote": min_odd['C']})
    return jsonify({"prediction": None})

if __name__ == '__main__':
    app.run(debug=True) 