from flask import Flask, render_template, request, jsonify
from predict import predict_position, enregistrer_resultat
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

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Render utilise cette variable automatiquement
    app.run(host='0.0.0.0', port=port)
