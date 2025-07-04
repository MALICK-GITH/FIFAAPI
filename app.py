from flask import Flask, render_template, request, jsonify
from predict import predict_position, enregistrer_resultat, charger_donnees, exporter_csv
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        billes = int(request.form['billes'])
        position = predict_position(billes)
        enregistrer_resultat(billes, position)
        return jsonify({'prediction': position})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/stats')
def stats():
    data = charger_donnees()
    positions = {"Gauche": 0, "Centre": 0, "Droite": 0}
    for partie in data["historique_parties"]:
        pos = partie["position_finale"]
        if pos in positions:
            positions[pos] += 1
    total = sum(positions.values())
    return jsonify({
        "total_parties": total,
        "répartition": positions
    })

@app.route('/export')
def export():
    try:
        exporter_csv()
        return jsonify({"message": "Export CSV réussi !"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
