from flask import Flask, render_template, request, jsonify
from predict import predict_position, enregistrer_resultat

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    billes = int(request.form['billes'])
    position = predict_position(billes)
    enregistrer_resultat(billes, position)
    return jsonify({'prediction': position})

if __name__ == '__main__':
    app.run(debug=True)
