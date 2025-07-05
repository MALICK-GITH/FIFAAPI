🎮 FIFA Doublon Bot — Prédictions & Nettoyage Automatisé
Un bot Telegram intelligent pour détecter les doublons et automatiser l'analyse des données FIFA. Construit avec amour, Python et une touche de magie API ⚡

📦 Fonctionnalités
📊 Détection automatique des doublons dans tes bases de données FIFA

🤖 Intégration fluide avec Telegram via python-telegram-bot

🧠 Structure modulaire et extensible

🚀 Déployable sur Render avec render.yaml

⚙️ Installation
bash
git clone https://github.com/MALICK-GITH/FIFAAPI.git
cd FIFAAPI/fifa-doublon-bot
pip install -r requirements.txt
python fifa_doublon_bot.py
🧰 Technologies
Python 🐍

SQLite3 🗃️

Telegram Bot API 🔗

Flask 🌐 (à venir)

Render ✨ (déploiement cloud)

📁 Structure du projet
FIFAAPI/
├── fifa-doublon-bot/
│   ├── fifa_doublon_bot.py
│   ├── requirements.txt
│   └── doublons.db
├── render.yaml
└── README.md
🚀 Déploiement sur Render
Assure-toi que render.yaml est bien configuré :

yaml
buildCommand: "pip install -r fifa-doublon-bot/requirements.txt"
startCommand: "python fifa-doublon-bot/fifa_doublon_bot.py"
Puis push sur GitHub et lance le build via le dashboard Render.

📞 Contact & communauté
📺 YouTube : https://youtube.com/@hacktutoinformatique?si=CS8TuuKo2zDzIBz7 📢 Telegram : https://t.me/SOLITAIREHACK
