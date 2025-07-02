from flask import Flask, request, render_template_string, jsonify
import requests
import os
import datetime
import json

app = Flask(__name__)

@app.route('/')
def home():
    try:
        selected_sport = request.args.get("sport", "").strip()
        selected_league = request.args.get("league", "").strip()
        selected_status = request.args.get("status", "").strip()
        source = request.args.get("source", "api").strip().lower()

        matches = []
        if source == "json":
            # Lecture du fichier local
            with open("Get1x2_VZip.json", "r", encoding="utf-8") as f:
                data_json = json.load(f)
                matches = data_json.get("Value", [])
        else:
            api_url = "https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=50&lng=fr&gr=70&mode=4&country=96&getEmpty=true"
            try:
                response = requests.get(api_url, timeout=5)
                matches = response.json().get("Value", [])
            except Exception as e:
                # Si l'API échoue, fallback sur le fichier local
                try:
                    with open("Get1x2_VZip.json", "r", encoding="utf-8") as f:
                        data_json = json.load(f)
                        matches = data_json.get("Value", [])
                except Exception as e2:
                    return f"Erreur lors de la récupération des données : {e} / {e2}"

        sports_detected = set()
        leagues_detected = set()
        data = []

        for match in matches:
            try:
                league = match.get("LE", "–")
                team1 = match.get("O1", "–")
                team2 = match.get("O2", "–")
                sport = detect_sport(league).strip()
                sports_detected.add(sport)
                leagues_detected.add(league)

                # --- Score ---
                score1 = match.get("SC", {}).get("FS", {}).get("S1")
                score2 = match.get("SC", {}).get("FS", {}).get("S2")
                try:
                    score1 = int(score1) if score1 is not None else 0
                except:
                    score1 = 0
                try:
                    score2 = int(score2) if score2 is not None else 0
                except:
                    score2 = 0

                # --- Minute ---
                minute = None
                # Prendre d'abord SC.TS (temps écoulé en secondes)
                sc = match.get("SC", {})
                if "TS" in sc and isinstance(sc["TS"], int):
                    minute = sc["TS"] // 60
                elif "ST" in sc and isinstance(sc["ST"], int):
                    minute = sc["ST"]
                elif "T" in match and isinstance(match["T"], int):
                    minute = match["T"] // 60

                # --- Statut ---
                tn = match.get("TN", "").lower()
                tns = match.get("TNS", "").lower()
                tt = match.get("SC", {}).get("TT")
                statut = "À venir"
                is_live = False
                is_finished = False
                is_upcoming = False
                if (minute is not None and minute > 0) or (score1 > 0 or score2 > 0):
                    statut = f"En cours ({minute}′)" if minute else "En cours"
                    is_live = True
                if ("terminé" in tn or "terminé" in tns) or (tt == 3):
                    statut = "Terminé"
                    is_live = False
                    is_finished = True
                if statut == "À venir":
                    is_upcoming = True

                if selected_sport and sport != selected_sport:
                    continue
                if selected_league and league != selected_league:
                    continue
                if selected_status == "live" and not is_live:
                    continue
                if selected_status == "finished" and not is_finished:
                    continue
                if selected_status == "upcoming" and not is_upcoming:
                    continue

                match_ts = match.get("S", 0)
                match_time = datetime.datetime.utcfromtimestamp(match_ts).strftime('%d/%m/%Y %H:%M') if match_ts else "–"

                # --- Cotes ---
                odds_data = []
                # 1. Chercher dans E (G=1)
                for o in match.get("E", []):
                    if o.get("G") == 1 and o.get("T") in [1, 2, 3] and o.get("C") is not None:
                        odds_data.append({
                            "type": {1: "1", 2: "2", 3: "X"}.get(o.get("T")),
                            "cote": o.get("C")
                        })
                # 2. Sinon, chercher dans AE
                if not odds_data:
                    for ae in match.get("AE", []):
                        if ae.get("G") == 1:
                            for o in ae.get("ME", []):
                                if o.get("T") in [1, 2, 3] and o.get("C") is not None:
                                    odds_data.append({
                                        "type": {1: "1", 2: "2", 3: "X"}.get(o.get("T")),
                                        "cote": o.get("C")
                                    })
                if not odds_data:
                    formatted_odds = ["Pas de cotes disponibles"]
                else:
                    formatted_odds = [f"{od['type']}: {od['cote']}" for od in odds_data]

                prediction = "–"
                if odds_data:
                    best = min(odds_data, key=lambda x: x["cote"])
                    prediction = {
                        "1": f"{team1} gagne",
                        "2": f"{team2} gagne",
                        "X": "Match nul"
                    }.get(best["type"], "–")

                # --- Météo ---
                meteo_data = match.get("MIS", [])
                temp = next((item["V"] for item in meteo_data if item.get("K") == 9), "–")
                humid = next((item["V"] for item in meteo_data if item.get("K") == 27), "–")

                data.append({
                    "team1": team1,
                    "team2": team2,
                    "score1": score1,
                    "score2": score2,
                    "league": league,
                    "sport": sport,
                    "status": statut,
                    "datetime": match_time,
                    "temp": temp,
                    "humid": humid,
                    "odds": formatted_odds,
                    "prediction": prediction,
                    "id": match.get("I", None)
                })
            except Exception as e:
                print(f"Erreur lors du traitement d'un match: {e}")
                continue

        # --- Pagination ---
        try:
            page = int(request.args.get('page', 1))
        except:
            page = 1
        per_page = 20
        total = len(data)
        total_pages = (total + per_page - 1) // per_page
        data_paginated = data[(page-1)*per_page:page*per_page]

        return render_template_string(TEMPLATE, data=data_paginated,
            sports=sorted(sports_detected),
            leagues=sorted(leagues_detected),
            selected_sport=selected_sport or "Tous",
            selected_league=selected_league or "Toutes",
            selected_status=selected_status or "Tous",
            page=page,
            total_pages=total_pages
        )

    except Exception as e:
        return f"Erreur : {e}"

def detect_sport(league_name):
    league = league_name.lower()
    if any(word in league for word in ["wta", "atp", "tennis"]):
        return "Tennis"
    elif any(word in league for word in ["basket", "nbl", "nba", "ipbl"]):
        return "Basketball"
    elif "hockey" in league:
        return "Hockey"
    elif any(word in league for word in ["tbl", "table"]):
        return "Table Basketball"
    elif "cricket" in league:
        return "Cricket"
    else:
        return "Football"

@app.route('/match/<int:match_id>')
def match_details(match_id):
    try:
        api_url = "https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=50&lng=fr&gr=70&mode=4&country=96&getEmpty=true"
        response = requests.get(api_url)
        matches = response.json().get("Value", [])
        match = next((m for m in matches if m.get("I") == match_id), None)
        if not match:
            return f"Aucun match trouvé pour l'identifiant {match_id}"
        team1 = match.get("O1", "–")
        team2 = match.get("O2", "–")
        league = match.get("LE", "–")
        sport = detect_sport(league)
        score1 = match.get("SC", {}).get("FS", {}).get("S1")
        score2 = match.get("SC", {}).get("FS", {}).get("S2")
        try:
            score1 = int(score1) if score1 is not None else 0
        except:
            score1 = 0
        try:
            score2 = int(score2) if score2 is not None else 0
        except:
            score2 = 0
        # Statistiques avancées
        stats = []
        st = match.get("SC", {}).get("ST", [])
        if st and isinstance(st, list) and len(st) > 0 and "Value" in st[0]:
            for stat in st[0]["Value"]:
                nom = stat.get("N", "?")
                s1 = stat.get("S1", "0")
                s2 = stat.get("S2", "0")
                stats.append({"nom": nom, "s1": s1, "s2": s2})
        # --- Options de paris (E et AE) ---
        options = []
        for o in match.get('E', []):
            if o.get('C') is not None:
                options.append({
                    'type': o.get('T'),
                    'groupe': o.get('G'),
                    'cote': o.get('C'),
                    'param': o.get('P', None)
                })
        for ae in match.get('AE', []):
            for o in ae.get('ME', []):
                if o.get('C') is not None:
                    options.append({
                        'type': o.get('T'),
                        'groupe': o.get('G'),
                        'cote': o.get('C'),
                        'param': o.get('P', None)
                    })
        # --- Robot FIFA : analyse sérieuse de la dispersion des cotes ---
        types = {}
        for opt in options:
            t = opt['type']
            if t not in types:
                types[t] = []
            types[t].append(opt['cote'])
        best_score = -1
        best_opt = None
        for opt in options:
            if 1.399 <= opt['cote'] <= 3:
                moyenne = sum(types[opt['type']]) / len(types[opt['type']])
                ecart_relatif = (moyenne - opt['cote']) / moyenne if moyenne > 0 else 0
                proba = 1 / opt['cote']
                score = proba * (1 + ecart_relatif)
                opt['proba'] = round(proba, 3)
                opt['score_robot'] = round(score, 3)
                opt['ecart_relatif'] = round(ecart_relatif, 3)
                if score > best_score:
                    best_score = score
                    best_opt = opt
            else:
                opt['proba'] = round(1 / opt['cote'], 3)
                opt['score_robot'] = None
                opt['ecart_relatif'] = None
        explication = "Le robot analyse la dispersion des cotes pour chaque type de pari. Une option avec une cote plus basse que la moyenne de son type est considérée comme plus fiable. Le score robotique combine la probabilité implicite et cet écart relatif."
        # HTML
        return f'''
        <!DOCTYPE html>
        <html><head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Détails du match</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ font-family: Arial; padding: 20px; background: #f4f4f4; }}
                .container {{ max-width: 900px; margin: auto; background: white; border-radius: 10px; box-shadow: 0 2px 8px #ccc; padding: 20px; }}
                h2 {{ text-align: center; }}
                .stats-table, .paris-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                .stats-table th, .stats-table td, .paris-table th, .paris-table td {{ border: 1px solid #ccc; padding: 8px; text-align: center; }}
                .back-btn {{ margin-bottom: 20px; display: inline-block; }}
                .robot-box {{ background: #eafaf1; border: 2px solid #27ae60; border-radius: 8px; padding: 16px; margin: 20px 0; font-size: 18px; }}
                .chart-switch {{ text-align:center; margin: 20px 0; }}
                .chart-switch button {{ padding: 8px 18px; margin: 0 8px; font-size: 16px; border: none; border-radius: 4px; background: #2c3e50; color: white; cursor: pointer; }}
                .chart-switch button.active {{ background: #27ae60; }}
            </style>
        </head><body>
            <div class="container">
                <a href="/" class="back-btn">&larr; Retour à la liste</a>
                <h2 id="teams">{team1} vs {team2}</h2>
                <p><b>Ligue :</b> <span id="league">{league}</span> | <b>Sport :</b> <span id="sport">{sport}</span></p>
                <p><b>Score :</b> <span id="score">{score1} - {score2}</span></p>
                <div class="robot-box" id="robot-box">
                    <b>🤖 Recommandation du robot FIFA :</b><br/>
                    {f"Option : <b>{best_opt['type']}</b> (groupe {best_opt['groupe']}, paramètre {best_opt['param']})<br/>Cote : <b>{best_opt['cote']}</b> | Probabilité estimée : <b>{best_opt['proba']*100:.1f}%</b> | Score robot : <b>{best_opt['score_robot']}</b>" if best_opt else "Aucune option optimale trouvée dans la fourchette 1,399 à 3."}
                    <br/><i>{explication}</i>
                </div>
                <h3>Toutes les options de paris disponibles</h3>
                <table class="paris-table" id="paris-table">
                    <tr><th>Option</th><th>Type (code)</th><th>Groupe</th><th>Paramètre</th><th>Cote</th><th>Probabilité (%)</th><th>Score robot</th><th>Écart relatif</th></tr>
                    {''.join(f'<tr><td>{traduire_option_pari(opt, team1, team2)}</td><td>{opt["type"]}</td><td>{opt["groupe"]}</td><td>{opt["param"]}</td><td>{opt["cote"]}</td><td>{opt["proba"]*100:.1f}</td><td>{opt["score_robot"] if opt["score_robot"] is not None else "-"}</td><td>{opt["ecart_relatif"] if opt["ecart_relatif"] is not None else "-"}</td></tr>' for opt in options)}
                </table>
                <h3>Statistiques principales</h3>
                <table class="stats-table" id="stats-table">
                    <tr><th>Statistique</th><th>{team1}</th><th>{team2}</th></tr>
                    {''.join(f'<tr><td>{s["nom"]}</td><td>{s["s1"]}</td><td>{s["s2"]}</td></tr>' for s in stats)}
                </table>
                <div class="chart-switch">
                    <button id="barBtn" class="active" onclick="showChart('bar')">Barres</button>
                    <button id="radarBtn" onclick="showChart('radar')">Radar</button>
                </div>
                <canvas id="statsChart" height="200"></canvas>
            </div>
            <script>
                const matchId = "{match_id}";
                let chart;
                function updateDetails() {{
                    fetch(`/api/match/${{matchId}}`)
                        .then(response => response.json())
                        .then(data => {{
                            document.getElementById('teams').textContent = data.equipes.domicile + ' vs ' + data.equipes.exterieur;
                            document.getElementById('league').textContent = data.championnat || '';
                            document.getElementById('sport').textContent = data.sportId || '';
                            document.getElementById('score').textContent = (data.score1 || 0) + ' - ' + (data.score2 || 0);
                            // Paris
                            let parisTable = document.getElementById('paris-table');
                            if (parisTable) {{
                                let rows = '<tr><th>Option</th><th>Type (code)</th><th>Groupe</th><th>Paramètre</th><th>Cote</th><th>Probabilité (%)</th><th>Score robot</th><th>Écart relatif</th></tr>';
                                (data.optionsParis || []).forEach(opt => {{
                                    rows += `<tr><td>${{opt.description || ''}}</td><td>${{opt.type}}</td><td>${{opt.groupe}}</td><td>${{opt.param}}</td><td>${{opt.valeur}}</td><td>${{opt.proba ? (opt.proba*100).toFixed(1) : '-'}}</td><td>${{opt.score_robot || '-'}}</td><td>${{opt.ecart_relatif || '-'}}</td></tr>`;
                                }});
                                parisTable.innerHTML = rows;
                            }}
                            // Stats
                            let statsTable = document.getElementById('stats-table');
                            if (statsTable) {{
                                let rows = `<tr><th>Statistique</th><th>${{data.equipes.domicile}}</th><th>${{data.equipes.exterieur}}</th></tr>`;
                                (data.stats || []).forEach(s => {{
                                    rows += `<tr><td>${{s.nom}}</td><td>${{s.domicile}}</td><td>${{s.exterieur}}</td></tr>`;
                                }});
                                statsTable.innerHTML = rows;
                            }}
                            // Graphique
                            const labels = (data.stats || []).map(s => s.nom);
                            const data1 = (data.stats || []).map(s => parseFloat(s.domicile) || 0);
                            const data2 = (data.stats || []).map(s => parseFloat(s.exterieur) || 0);
                            if(chart) chart.destroy();
                            chart = new Chart(document.getElementById('statsChart'), {{
                                type: 'bar',
                                data: {{
                                    labels: labels,
                                    datasets: [
                                        {{ label: data.equipes.domicile, data: data1, backgroundColor: 'rgba(44,62,80,0.7)', borderColor: 'rgba(44,62,80,1)', borderWidth: 2 }},
                                        {{ label: data.equipes.exterieur, data: data2, backgroundColor: 'rgba(39,174,96,0.7)', borderColor: 'rgba(39,174,96,1)', borderWidth: 2 }}
                                    ]
                                }},
                                options: {{
                                    responsive: true,
                                    plugins: {{ legend: {{ position: 'top' }} }},
                                    animation: {{ duration: 1200 }},
                                    scales: {{ y: {{ beginAtZero: true }} }}
                                }}
                            }});
                        }});
                }}
                setInterval(updateDetails, 5000);
                // Initialisation du graphique (barres par défaut)
                function showChart(type) {{
                    document.getElementById('barBtn').classList.toggle('active', type==='bar');
                    document.getElementById('radarBtn').classList.toggle('active', type==='radar');
                    if(chart) chart.destroy();
                    chart = new Chart(document.getElementById('statsChart'), {{
                        type: type,
                        data: {{
                            labels: {json.dumps([s['nom'] for s in stats])},
                            datasets: [
                                {{ label: '{team1}', data: {json.dumps([float(s['s1']) if str(s['s1']).replace('.', '', 1).isdigit() else 0 for s in stats])}, backgroundColor: type==='bar' ? 'rgba(44,62,80,0.7)' : 'rgba(44,62,80,0.4)', borderColor: 'rgba(44,62,80,1)', borderWidth: 2, fill: type==='radar' }},
                                {{ label: '{team2}', data: {json.dumps([float(s['s2']) if str(s['s2']).replace('.', '', 1).isdigit() else 0 for s in stats])}, backgroundColor: type==='bar' ? 'rgba(39,174,96,0.7)' : 'rgba(39,174,96,0.4)', borderColor: 'rgba(39,174,96,1)', borderWidth: 2, fill: type==='radar' }}
                            ]
                        }},
                        options: {{
                            responsive: true,
                            plugins: {{
                                legend: {{ position: 'top' }},
                                tooltip: {{ enabled: true }},
                                datalabels: {{
                                    display: true,
                                    color: '#222',
                                    font: {{ weight: 'bold' }},
                                    formatter: Math.round
                                }}
                            }},
                            animation: {{ duration: 1200 }},
                            scales: type==='bar' ? {{ y: {{ beginAtZero: true }} }} : {{}}
                        }}
                    }});
                }}
                // Affichage initial
                showChart('bar');
            </script>
        </body></html>
        '''
    except Exception as e:
        return f"Erreur lors de l'affichage des détails du match : {e}"

# --- FONCTIONS D'EXTRACTION ROBUSTES ---
def charger_donnees():
    """Récupère les données depuis l'API ou le fichier local en cas d'échec."""
    try:
        api_url = "https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=50&lng=fr&gr=70&mode=4&country=96&getEmpty=true"
        response = requests.get(api_url, timeout=5)
        return response.json()
    except Exception:
        with open("Get1x2_VZip.json", "r", encoding="utf-8") as f:
            return json.load(f)

def extraire_ligue(match):
    return {
        "id": match.get("LI"),
        "nom": match.get("LE"),
        "championnat": match.get("SN", match.get("SE", "")),
        "sportId": match.get("SI"),
        "zone": match.get("CN"),
        "langue": "fr"
    }

def extraire_match(match):
    league = match.get("LE", "–")
    team1 = match.get("O1", "–")
    team2 = match.get("O2", "–")
    sport = detect_sport(league).strip()
    # Score
    score1 = match.get("SC", {}).get("FS", {}).get("S1")
    score2 = match.get("SC", {}).get("FS", {}).get("S2")
    try:
        score1 = int(score1) if score1 is not None else 0
    except:
        score1 = 0
    try:
        score2 = int(score2) if score2 is not None else 0
    except:
        score2 = 0
    # Statut
    minute = None
    sc = match.get("SC", {})
    if "TS" in sc and isinstance(sc["TS"], int):
        minute = sc["TS"] // 60
    elif "ST" in sc and isinstance(sc["ST"], int):
        minute = sc["ST"]
    elif "T" in match and isinstance(match["T"], int):
        minute = match["T"] // 60
    tn = match.get("TN", "").lower()
    tns = match.get("TNS", "").lower()
    tt = match.get("SC", {}).get("TT")
    statut = "À venir"
    is_live = False
    is_finished = False
    is_upcoming = False
    if (minute is not None and minute > 0) or (score1 > 0 or score2 > 0):
        statut = f"En cours ({minute}′)" if minute else "En cours"
        is_live = True
    if ("terminé" in tn or "terminé" in tns) or (tt == 3):
        statut = "Terminé"
        is_live = False
        is_finished = True
    if statut == "À venir":
        is_upcoming = True
    match_ts = match.get("S", 0)
    match_time = datetime.datetime.utcfromtimestamp(match_ts).strftime('%d/%m/%Y %H:%M') if match_ts else "–"
    # Cotes
    odds_data = []
    for o in match.get("E", []):
        if o.get("G") == 1 and o.get("T") in [1, 2, 3] and o.get("C") is not None:
            odds_data.append({
                "type": {1: "1", 2: "2", 3: "X"}.get(o.get("T")),
                "cote": o.get("C")
            })
    if not odds_data:
        for ae in match.get("AE", []):
            if ae.get("G") == 1:
                for o in ae.get("ME", []):
                    if o.get("T") in [1, 2, 3] and o.get("C") is not None:
                        odds_data.append({
                            "type": {1: "1", 2: "2", 3: "X"}.get(o.get("T")),
                            "cote": o.get("C")
                        })
    if not odds_data:
        formatted_odds = ["Pas de cotes disponibles"]
    else:
        formatted_odds = [f"{od['type']}: {od['cote']}" for od in odds_data]
    prediction = "–"
    if odds_data:
        best = min(odds_data, key=lambda x: x["cote"])
        prediction = {
            "1": f"{team1} gagne",
            "2": f"{team2} gagne",
            "X": "Match nul"
        }.get(best["type"], "–")
    # Météo
    meteo_data = match.get("MIS", [])
    temp = next((item["V"] for item in meteo_data if item.get("K") == 9), "–")
    humid = next((item["V"] for item in meteo_data if item.get("K") == 27), "–")
    return {
        "team1": team1,
        "team2": team2,
        "score1": score1,
        "score2": score2,
        "league": league,
        "sport": sport,
        "status": statut,
        "datetime": match_time,
        "temp": temp,
        "humid": humid,
        "odds": formatted_odds,
        "prediction": prediction,
        "id": match.get("I", None)
    }

def get_ligues(data):
    ligues = {}
    for match in data.get('Value', []):
        ligue_id = match.get('LI')
        if ligue_id not in ligues:
            ligues[ligue_id] = extraire_ligue(match)
            ligues[ligue_id]['evenements'] = []
        ligues[ligue_id]['evenements'].append(match.get('I'))
    return ligues

def get_matchs(data):
    return [extraire_match(match) for match in data.get('Value', [])]

def get_equipes(data):
    equipes = {}
    for match in data.get('Value', []):
        for key in ['O1', 'O2']:
            nom = match.get(key)
            if nom and nom not in equipes:
                equipes[nom] = {
                    'nom': nom,
                    'id': match.get(f'{key}I'),
                    'img': match.get(f'{key}IMG', [""])[0] if match.get(f'{key}IMG') else ""
                }
    return equipes

def get_cotes(match):
    cotes = []
    for o in match.get("E", []):
        if o.get("C") is not None:
            cotes.append({
                "type": o.get("T"),
                "groupe": o.get("G"),
                "valeur": o.get("C"),
                "param": o.get("P", None)
            })
    return cotes

def get_stats(match):
    stats = []
    st = match.get("SC", {}).get("ST", [])
    if st and isinstance(st, list) and len(st) > 0 and "Value" in st[0]:
        for stat in st[0]["Value"]:
            stats.append({
                "nom": stat.get("N", "?"),
                "domicile": stat.get("S1", "0"),
                "exterieur": stat.get("S2", "0")
            })
    return stats

def get_meteo(match):
    meteo_data = match.get("MIS", [])
    temp = next((item["V"] for item in meteo_data if item.get("K") == 9), "–")
    humid = next((item["V"] for item in meteo_data if item.get("K") == 27), "–")
    return {"temperature": temp, "humidite": humid}

# --- ENDPOINTS API PUISSANTS ET SÉCURISÉS ---
@app.route('/api/ligues')
def api_ligues():
    """Retourne toutes les ligues structurées avec leurs matchs."""
    data = charger_donnees()
    return jsonify(list(get_ligues(data).values()))

@app.route('/api/matchs')
def api_matchs():
    """Retourne tous les matchs avec tous les détails utiles."""
    data = charger_donnees()
    return jsonify(get_matchs(data))

@app.route('/api/equipes')
def api_equipes():
    """Retourne toutes les équipes présentes dans les matchs."""
    data = charger_donnees()
    return jsonify(list(get_equipes(data).values()))

@app.route('/api/match/<int:match_id>')
def api_match_detail(match_id):
    """Retourne tous les détails d'un match donné."""
    data = charger_donnees()
    match = next((m for m in data.get('Value', []) if m.get('I') == match_id), None)
    if not match:
        return jsonify({"error": "Match introuvable"}), 404
    return jsonify(extraire_match(match))

@app.route('/api/match/<int:match_id>/stats')
def api_match_stats(match_id):
    """Retourne les statistiques avancées d'un match."""
    data = charger_donnees()
    match = next((m for m in data.get('Value', []) if m.get('I') == match_id), None)
    if not match:
        return jsonify({"error": "Match introuvable"}), 404
    return jsonify(get_stats(match))

@app.route('/api/match/<int:match_id>/cotes')
def api_match_cotes(match_id):
    """Retourne toutes les cotes d'un match."""
    data = charger_donnees()
    match = next((m for m in data.get('Value', []) if m.get('I') == match_id), None)
    if not match:
        return jsonify({"error": "Match introuvable"}), 404
    return jsonify(get_cotes(match))

@app.route('/api/match/<int:match_id>/meteo')
def api_match_meteo(match_id):
    """Retourne les infos météo d'un match."""
    data = charger_donnees()
    match = next((m for m in data.get('Value', []) if m.get('I') == match_id), None)
    if not match:
        return jsonify({"error": "Match introuvable"}), 404
    return jsonify(get_meteo(match))

# --- Fonction de traduction des options de pari ---
def traduire_option_pari(opt, team1, team2):
    t = opt.get('type')
    g = opt.get('groupe')
    param = opt.get('param')
    # 1N2 classique
    if t == 1:
        return f"Victoire {team1}"
    elif t == 2:
        return f"Victoire {team2}"
    elif t == 3 or t == 'X':
        return "Match nul"
    # Handicap
    elif g == 2:
        if t == 1:
            return f"{team1} gagne avec handicap {param}"
        elif t == 2:
            return f"{team2} gagne avec handicap {param}"
    # Over/Under
    elif g == 3:
        if t == 1:
            return f"Plus de {param} buts"
        elif t == 2:
            return f"Moins de {param} buts"
    # Autres cas
    return f"Type {t} (groupe {g}, param {param})"

TEMPLATE = """<!DOCTYPE html>
<html><head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Matchs en direct</title>
    <style>
        body { font-family: Arial; padding: 20px; background: #f4f4f4; }
        h2 { text-align: center; }
        form { text-align: center; margin-bottom: 20px; }
        select { padding: 8px; margin: 0 10px; font-size: 14px; }
        table { border-collapse: collapse; margin: auto; width: 98%; background: white; }
        th, td { padding: 10px; border: 1px solid #ccc; text-align: center; }
        th { background: #2c3e50; color: white; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .pagination { text-align: center; margin: 20px 0; }
        .pagination button { padding: 8px 16px; margin: 0 4px; font-size: 16px; border: none; background: #2c3e50; color: white; border-radius: 4px; cursor: pointer; }
        .pagination button:disabled { background: #ccc; cursor: not-allowed; }
        /* Responsive */
        @media (max-width: 800px) {
            table, thead, tbody, th, td, tr { display: block; }
            th { position: absolute; left: -9999px; top: -9999px; }
            tr { margin-bottom: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 6px #ccc; }
            td { border: none; border-bottom: 1px solid #eee; position: relative; padding-left: 50%; min-height: 40px; }
            td:before { position: absolute; top: 10px; left: 10px; width: 45%; white-space: nowrap; font-weight: bold; }
            td:nth-of-type(1):before { content: 'Équipe 1'; }
            td:nth-of-type(2):before { content: 'Score 1'; }
            td:nth-of-type(3):before { content: 'Score 2'; }
            td:nth-of-type(4):before { content: 'Équipe 2'; }
            td:nth-of-type(5):before { content: 'Sport'; }
            td:nth-of-type(6):before { content: 'Ligue'; }
            td:nth-of-type(7):before { content: 'Statut'; }
            td:nth-of-type(8):before { content: 'Date & Heure'; }
            td:nth-of-type(9):before { content: 'Température'; }
            td:nth-of-type(10):before { content: 'Humidité'; }
            td:nth-of-type(11):before { content: 'Cotes'; }
            td:nth-of-type(12):before { content: 'Prédiction'; }
        }
        /* Loader */
        #loader { display: none; position: fixed; left: 0; top: 0; width: 100vw; height: 100vh; background: rgba(255,255,255,0.7); z-index: 9999; justify-content: center; align-items: center; }
        #loader .spinner { border: 8px solid #f3f3f3; border-top: 8px solid #2c3e50; border-radius: 50%; width: 60px; height: 60px; animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
    </style>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            var forms = document.querySelectorAll('form');
            forms.forEach(function(form) {
                form.addEventListener('submit', function() {
                    document.getElementById('loader').style.display = 'flex';
                });
            });

            // --- Rafraîchissement automatique du tableau ---
            function updateTable() {
                fetch('/api/matchs')
                    .then(response => response.json())
                    .then(matches => {
                        console.log('Données reçues pour le tableau principal :', matches);
                        var tbody = document.querySelector('table tbody');
                        if (!tbody) return;
                        tbody.innerHTML = '';
                        matches.forEach(function(m) {
                            var row = document.createElement('tr');
                            row.innerHTML = `
                                <td>${m.team1 || ''}</td>
                                <td>${m.score1 !== undefined ? m.score1 : ''}</td>
                                <td>${m.score2 !== undefined ? m.score2 : ''}</td>
                                <td>${m.team2 || ''}</td>
                                <td>${m.sport || ''}</td>
                                <td>${m.league || ''}</td>
                                <td>${m.status || ''}</td>
                                <td>${m.datetime || ''}</td>
                                <td>${m.temp || ''}°C</td>
                                <td>${m.humid || ''}%</td>
                                <td>${Array.isArray(m.odds) ? m.odds.join(' | ') : m.odds}</td>
                                <td>${m.prediction || ''}</td>
                                <td>${m.id ? `<a href='/match/${m.id}'><button>Détails</button></a>` : '–'}</td>
                            `;
                            tbody.appendChild(row);
                        });
                    });
            }
            setInterval(updateTable, 5000);
        });
    </script>
</head><body>
    <div id="loader"><div class="spinner"></div></div>
    <h2>📊 Matchs en direct — {{ selected_sport }} / {{ selected_league }} / {{ selected_status }}</h2>

    <form method="get">
        <label>Sport :
            <select name="sport" onchange="this.form.submit()">
                <option value="">Tous</option>
                {% for s in sports %}
                    <option value="{{s}}" {% if s == selected_sport %}selected{% endif %}>{{s}}</option>
                {% endfor %}
            </select>
        </label>
        <label>Ligue :
            <select name="league" onchange="this.form.submit()">
                <option value="">Toutes</option>
                {% for l in leagues %}
                    <option value="{{l}}" {% if l == selected_league %}selected{% endif %}>{{l}}</option>
                {% endfor %}
            </select>
        </label>
        <label>Statut :
            <select name="status" onchange="this.form.submit()">
                <option value="">Tous</option>
                <option value="live" {% if selected_status == "live" %}selected{% endif %}>En direct</option>
                <option value="upcoming" {% if selected_status == "upcoming" %}selected{% endif %}>À venir</option>
                <option value="finished" {% if selected_status == "finished" %}selected{% endif %}>Terminé</option>
            </select>
        </label>
    </form>

    <div class="pagination">
        <form method="get" style="display:inline;">
            <input type="hidden" name="sport" value="{{ selected_sport if selected_sport != 'Tous' else '' }}">
            <input type="hidden" name="league" value="{{ selected_league if selected_league != 'Toutes' else '' }}">
            <input type="hidden" name="status" value="{{ selected_status if selected_status != 'Tous' else '' }}">
            <button type="submit" name="page" value="{{ page-1 }}" {% if page <= 1 %}disabled{% endif %}>Page précédente</button>
        </form>
        <span>Page {{ page }} / {{ total_pages }}</span>
        <form method="get" style="display:inline;">
            <input type="hidden" name="sport" value="{{ selected_sport if selected_sport != 'Tous' else '' }}">
            <input type="hidden" name="league" value="{{ selected_league if selected_league != 'Toutes' else '' }}">
            <input type="hidden" name="status" value="{{ selected_status if selected_status != 'Tous' else '' }}">
            <button type="submit" name="page" value="{{ page+1 }}" {% if page >= total_pages %}disabled{% endif %}>Page suivante</button>
        </form>
    </div>

    <table>
        <thead>
        <tr>
            <th>Équipe 1</th><th>Score 1</th><th>Score 2</th><th>Équipe 2</th>
            <th>Sport</th><th>Ligue</th><th>Statut</th><th>Date & Heure</th>
            <th>Température</th><th>Humidité</th><th>Cotes</th><th>Prédiction</th><th>Détails</th>
        </tr>
        </thead>
        <tbody>
        {% for m in data %}
        <tr>
            <td>{{m.team1}}</td><td>{{m.score1}}</td><td>{{m.score2}}</td><td>{{m.team2}}</td>
            <td>{{m.sport}}</td><td>{{m.league}}</td><td>{{m.status}}</td><td>{{m.datetime}}</td>
            <td>{{m.temp}}°C</td><td>{{m.humid}}%</td><td>{{m.odds|join(" | ")}}</td><td>{{m.prediction}}</td>
            <td>{% if m.id %}<a href="/match/{{m.id}}"><button>Détails</button></a>{% else %}–{% endif %}</td>
        </tr>
        {% endfor %}
        </tbody>
    </table>
</body></html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
