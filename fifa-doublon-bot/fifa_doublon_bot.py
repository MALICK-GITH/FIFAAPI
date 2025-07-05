import requests, time, json, sqlite3, schedule
from telegram import Bot
from datetime import datetime

# 🔧 Configuration
TOKEN = '8095305269:AAFBdRXSKqCLUP6s1pLXgFD794arKKqTqK8'
CHAT_ID = '7569017578'
API_URL = 'https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=50&lng=fr&gr=70&mode=4&country=96&getEmpty=true'
INTERVAL = 10800  # 3 heures en secondes
SCAN_FREQUENCY = 120  # toutes les 2 minutes

bot = Bot(token=TOKEN)

# 💾 Base SQLite
conn = sqlite3.connect('doublons.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS matchs (
    match_id TEXT PRIMARY KEY,
    equipe1 TEXT,
    equipe2 TEXT,
    ligue TEXT,
    timestamp INTEGER,
    score TEXT,
    suggestion TEXT
)''')
conn.commit()

match_cache = {}  # 🧠 Cache pour doublons

def get_score(match):
    fs = match.get("SC", {}).get("FS", {})
    return f"{fs.get('S1', '?')} - {fs.get('S2', '?')}" if fs else "Indisponible"

def parse_cotes(match):
    cote_o1 = cote_o2 = None
    for e in match.get("E", []):
        if e.get("G") == 2 and e.get("T") == 7:
            cote_o1 = e.get("C")
        elif e.get("G") == 2 and e.get("T") == 8:
            cote_o2 = e.get("C")
    if cote_o1 and cote_o2:
        return f"🟢 Tendance : {match['O1']} ({cote_o1})" if cote_o1 < cote_o2 else f"🔴 Tendance : {match['O2']} ({cote_o2})"
    return "⚠️ Cotes indisponibles"

def save_doublon(match, score, suggestion):
    key = f"{match['O1']}|{match['O2']}|{match['LI']}"
    cursor.execute("INSERT OR IGNORE INTO matchs VALUES (?, ?, ?, ?, ?, ?, ?)", (
        key, match['O1'], match['O2'], match['L'], match['S'], score, suggestion
    ))
    conn.commit()

def export_json():
    cursor.execute("SELECT * FROM matchs ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    with open("doublons_export.json", "w", encoding="utf-8") as f:
        json.dump([{
            "match_id": r[0],
            "equipe1": r[1],
            "equipe2": r[2],
            "ligue": r[3],
            "timestamp": r[4],
            "score": r[5],
            "suggestion": r[6]
        } for r in rows], f, indent=4)

def send_resume():
    cursor.execute("SELECT COUNT(*) FROM matchs")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT equipe1, equipe2, score FROM matchs ORDER BY timestamp DESC LIMIT 5")
    last = cursor.fetchall()
    msg = f"📊 *Résumé des doublons FIFA (3h)*\n🔢 Total : {total}\n\n"
    for e1, e2, sc in last:
        msg += f"• {e1} vs {e2} | Score : {sc}\n"
    bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

def detect_doublons():
    try:
        res = requests.get(API_URL)
        matches = res.json().get("Value", [])
        for match in matches:
            key = f"{match['O1']}|{match['O2']}|{match['LI']}"
            ts = match['S']
            score = get_score(match)
            if key in match_cache and abs(ts - match_cache[key]) < INTERVAL:
                time_str = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                suggestion = f"{parse_cotes(match)} | Score précédent : {score}"
                msg = f"*⚠️ Doublon FIFA détecté !*\n🏟️ *{match['O1']}* vs *{match['O2']}*\n🕒 {time_str}\n📊 {suggestion}\n\n💡 Parie stratégiquement."
                bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')
                save_doublon(match, score, suggestion)
            match_cache[key] = ts
    except Exception as e:
        bot.send_message(chat_id=CHAT_ID, text=f"❌ Erreur : {str(e)}")

# 🕒 Résumé toutes les 3h
schedule.every(3).hours.do(send_resume)

# 🔁 Boucle principale
while True:
    detect_doublons()
    export_json()
    schedule.run_pending()
    time.sleep(SCAN_FREQUENCY)
