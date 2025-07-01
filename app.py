import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import logging
from datetime import datetime
import asyncio
import random

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8038812221:AAFt5ghu1jep8qMyBMXP0-SSPBMjSrNdWmk"

# Pagination : nombre de matchs par page
MATCHS_PAR_PAGE = 5

# Langues supportées
LANGS = {
    'fr': {
        'start': "👋 Salut ! Je suis ton bot des cotes en direct pour le <b>FIFA virtuel</b> !\n\n"
                 "⚡️ Seuls les matchs de FIFA virtuel (e-sport) sont affichés.\n\n"
                 "Utilise /matchs pour voir les matchs en cours avec leurs scores, cotes et statistiques.\n\n"
                 "<b>Commandes principales :</b>\n/start - Message de bienvenue\n/matchs [page] [compétition] - Affiche les matchs en direct\n/lang [fr|en] - Change la langue\n/help - Affiche cette aide\n/abonner [équipe|compétition] - Reçois des notifications de buts\n/desabonner [équipe|compétition] - Arrête les notifications\n/mesabos - Liste tes abonnements\n\n<b>NOUVEAU :</b>\n/predire [équipe1] [équipe2] - Obtiens une prédiction intelligente basée sur l'historique des confrontations et la forme récente (ex: /predire PSG Marseille)",
        'help': "<b>Commandes disponibles :</b>\n\n/start - Message de bienvenue\n/matchs [page] [compétition] - Affiche les matchs en direct (ex: /matchs 2 Ligue 1)\n/lang [fr|en] - Change la langue\n/abonner [équipe|compétition] - Reçois des notifications de buts pour une équipe ou une compétition (ex: /abonner PSG)\n/desabonner [équipe|compétition] - Arrête les notifications pour une équipe ou une compétition\n/mesabos - Affiche la liste de tes abonnements\n/help - Affiche cette aide\n\n<b>Prédiction IA :</b>\n/predire [équipe1] [équipe2] - Obtiens une prédiction intelligente basée sur :\n- Les 5 dernières confrontations directes entre les deux équipes\n- La forme récente (5 derniers matchs) de chaque équipe, tous adversaires confondus\n\nExemple : /predire PSG Marseille\n\nLa prédiction combine ces éléments pour donner un résultat plus fiable (V = victoire, N = nul, D = défaite).",
        'no_match': "❌ Aucun match trouvé pour le moment. Réessaie plus tard.",
        'matches_title': "\U0001F3C6 <b>Matchs en direct</b> :\n\n",
        'competition': "\u2B50 Compétition",
        'time': "\u23F0 Heure",
        'score': "\U0001F522 Score",
        'odds': "\U0001F4B0 Cotes principales",
        'stats': "\U0001F4CA <u>Statistiques principales</u> :",
        'page': "Page",
        'no_odds': "Aucune cote disponible",
        'lang_set': "Langue changée en français !",
        'usage': "Utilisation : /matchs [page] [compétition]"
    },
    'en': {
        'start': "👋 Hi! I'm your live odds bot!\n\nUse /matchs to see live matches with scores, odds and stats.\n\n<b>Main commands:</b>\n/start - Welcome message\n/matchs [page] [competition] - Show live matches\n/lang [fr|en] - Change language\n/help - Show this help\n/abonner [team|competition] - Get goal notifications\n/desabonner [team|competition] - Stop notifications\n/mesabos - List your subscriptions",
        'help': "<b>Available commands:</b>\n\n/start - Welcome message\n/matchs [page] [competition] - Show live matches (ex: /matchs 2 Premier League)\n/lang [fr|en] - Change language\n/abonner [team|competition] - Get goal notifications for a team or competition (ex: /abonner PSG)\n/desabonner [team|competition] - Stop notifications for a team or competition\n/mesabos - Show your subscriptions\n/help - Show this help",
        'no_match': "❌ No matches found at the moment. Try again later.",
        'matches_title': "\U0001F3C6 <b>Live matches</b> :\n\n",
        'competition': "\u2B50 Competition",
        'time': "\u23F0 Time",
        'score': "\U0001F522 Score",
        'odds': "\U0001F4B0 Main odds",
        'stats': "\U0001F4CA <u>Main stats</u> :",
        'page': "Page",
        'no_odds': "No odds available",
        'lang_set': "Language set to English!",
        'usage': "Usage: /matchs [page] [competition]"
    }
}

# Stocke la langue de chaque utilisateur
user_lang = {}
# Stocke les scores précédents pour la détection de buts
previous_scores = {}
# Stocke les utilisateurs ayant interagi avec le bot
users_interested = set()
# Stocke les abonnements des utilisateurs : {user_id: set(noms)}
user_subs = {}

def get_lang(user_id):
    return user_lang.get(user_id, 'fr')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users_interested.add(update.effective_user.id)
    lang = get_lang(update.effective_user.id)
    await send_long_message(context.bot, update.message.chat_id, LANGS[lang]['start'])

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users_interested.add(update.effective_user.id)
    lang = get_lang(update.effective_user.id)
    await send_long_message(context.bot, update.message.chat_id, LANGS[lang]['help'], parse_mode="HTML")

async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users_interested.add(update.effective_user.id)
    if context.args and context.args[0] in LANGS:
        user_lang[update.effective_user.id] = context.args[0]
        await send_long_message(context.bot, update.message.chat_id, LANGS[context.args[0]]['lang_set'])
    else:
        await send_long_message(context.bot, update.message.chat_id, "/lang fr ou /lang en")

def fetch_matches():
    url = "https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=50&lng=fr&gr=70&mode=4&country=96&getEmpty=true"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("Value", [])
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des matchs : {e}")
        return []

def format_score(score_dict):
    if not score_dict:
        return "Non disponible"
    home = score_dict.get("1", 0)
    away = score_dict.get("2", 0)
    return f"{home} - {away}"

def format_odds(match):
    odds = match.get("E", [])
    if not odds:
        return None
    main_odds = []
    for o in odds:
        if o.get("T") == 1:  # Type 1 = 1X2
            cotes = o.get("C", [])
            if not isinstance(cotes, list):
                continue  # Ignore si ce n'est pas une liste
            for v in cotes:
                nom = v.get("N")
                cote = v.get("V")
                if nom and cote:
                    main_odds.append(f"{nom}: <b>{cote}</b>")
    return " | ".join(main_odds) if main_odds else None

# Ajout d'une fonction pour détecter le sport
SPORTS_EMOJIS = {
    'football': '⚽',
    'tennis': '🎾',
    'volleyball': '🏐',
    'cricket': '🏏',
    'basketball': '🏀',
    'hockey': '🏒',
    'default': '🏆'
}

def detect_sport(ligue, heure):
    l = ligue.lower()
    h = str(heure).lower()
    if 'foot' in l or 'foot' in h:
        return 'football'
    if 'tennis' in l or 'tennis' in h:
        return 'tennis'
    if 'volley' in l or 'volley' in h:
        return 'volleyball'
    if 'cricket' in l or 'cricket' in h:
        return 'cricket'
    if 'basket' in l or 'basket' in h:
        return 'basketball'
    if 'hockey' in l or 'hockey' in h:
        return 'hockey'
    return 'default'

def format_heure(se, stats, score):
    # se peut être un dict, une string, ou absent
    if isinstance(se, dict):
        heure = se.get("S")
    else:
        heure = se if se else None
    # Si heure ressemble à une date/heure, tente de la parser
    if heure:
        try:
            # Exemple de format possible : '2024-06-20T18:00:00Z'
            dt = datetime.fromisoformat(heure.replace('Z', '+00:00'))
            return dt.strftime('%d/%m %H:%M')
        except Exception:
            # Si ce n'est pas une date, retourne la valeur brute
            return heure
    # Si stats ou score sont présents, on suppose que c'est en cours
    if stats or score:
        return "En cours"
    return "Heure non précisée"

# Ajout des statuts possibles
STATUTS = ["en_cours", "a_venir", "termine"]
STATUTS_LABELS = {
    "en_cours": "En cours",
    "a_venir": "À venir",
    "termine": "Terminé"
}

# Fonction pour déterminer le statut d'un match
def get_statut_match(heure, stats, score):
    if heure and ("en cours" in heure.lower() or "live" in heure.lower()):
        return "en_cours"
    if stats or score:
        return "en_cours"
    if heure and ("termine" in heure.lower() or "fin" in heure.lower()):
        return "termine"
    return "a_venir"

# Fonction pour extraire la liste des sports et compétitions présents dans les matchs
def extraire_sports_competitions(matchs):
    sports = set()
    competitions = set()
    for match in matchs:
        ligue = match.get("L") or "Compétition non renseignée"
        se = match.get("SE", {})
        stats = match.get("SC", {}).get("ST", [])
        score = match.get("SC", {}).get("FS", {})
        heure_affichee = format_heure(se, stats, score)
        sport = detect_sport(ligue, heure_affichee)
        sports.add(sport)
        competitions.add(ligue)
    return sorted(sports), sorted(competitions)

# Fonction utilitaire pour découper les messages trop longs
async def send_long_message(bot, chat_id, text, **kwargs):
    max_len = 4096
    for i in range(0, len(text), max_len):
        await bot.send_message(chat_id=chat_id, text=text[i:i+max_len], **kwargs)

# Fonction utilitaire pour découper une liste en sous-listes de taille n
def chunk_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# Fonction utilitaire pour envoyer un message HTML long sans dépasser 4096 caractères, en découpant à la fin d'une ligne
async def send_html_long_message(bot, chat_id, text, **kwargs):
    MAX_LEN = 4096
    lines = text.split('\n')
    part = ''
    for line in lines:
        if len(part) + len(line) + 1 > MAX_LEN:
            await bot.send_message(chat_id=chat_id, text=part, **kwargs)
            part = ''
        part += line + '\n'
    if part.strip():
        await bot.send_message(chat_id=chat_id, text=part, **kwargs)

def label_cote(t, g, p=None, sport="football"):
    # 1X2
    if g == 1:
        if t == 1:
            return "Victoire équipe 1"
        elif t == 2:
            return "Match nul"
        elif t == 3:
            return "Victoire équipe 2"
    # Handicap
    if g == 2:
        if t == 7:
            return f"Handicap équipe 1 (écart {p})"
        elif t == 8:
            return f"Handicap équipe 2 (écart {p})"
    # Over/Under
    if g == 17:
        if t == 9:
            return f"Plus de {p} buts"
        elif t == 10:
            return f"Moins de {p} buts"
    # Score exact
    if g == 15:
        if t == 11:
            return f"Score exact équipe 1 : {p}"
        elif t == 12:
            return f"Score exact équipe 2 : {p}"
    # Total équipe 1/2
    if g == 62:
        if t == 13:
            return f"Total buts équipe 1 : plus de {p}"
        elif t == 14:
            return f"Total buts équipe 2 : plus de {p}"
    # Mi-temps
    if g == 19:
        if t == 180:
            return "Victoire équipe 1 à la mi-temps"
        elif t == 181:
            return "Victoire équipe 2 à la mi-temps"
    # Ajoute ici d'autres mappings selon les besoins
    return f"Type {t}/Groupe {g}" + (f" (paramètre {p})" if p is not None else "")

def predire_auto(match):
    # Nouvelle prédiction : priorité au total de buts, puis handicap, puis (futur) pair/impair
    options = []
    # 1. Total de buts (G:17, T:9/10)
    for group in match.get("AE", []):
        if group.get("G") == 17:
            for me in group.get("ME", []):
                cote = me.get("C")
                t = me.get("T")
                p = me.get("P")
                try:
                    cote_f = float(cote)
                except:
                    continue
                if 1.399 <= cote_f <= 3:
                    if t == 9:
                        options.append((f"Plus de {p} buts", cote_f))
                    elif t == 10:
                        options.append((f"Moins de {p} buts", cote_f))
    # 2. Handicap (G:2, T:7/8)
    for group in match.get("AE", []):
        if group.get("G") == 2:
            for me in group.get("ME", []):
                cote = me.get("C")
                t = me.get("T")
                p = me.get("P")
                try:
                    cote_f = float(cote)
                except:
                    continue
                if 1.399 <= cote_f <= 3:
                    if t == 7:
                        if p is not None:
                            options.append((f"Handicap équipe 1 ({p:+})", cote_f))
                        else:
                            options.append(("Handicap équipe 1", cote_f))
                    elif t == 8:
                        if p is not None:
                            options.append((f"Handicap équipe 2 ({p:+})", cote_f))
                        else:
                            options.append(("Handicap équipe 2", cote_f))
    # 3. (Futur) Total pair/impair (à activer si présent dans la structure)
    # for group in match.get("AE", []):
    #     if group.get("G") == XX:  # À compléter si on trouve la structure
    #         ...
    if not options:
        return "Aucune prédiction disponible pour ce match."
    # On trie par cote croissante
    options_sorted = sorted(options, key=lambda x: x[1])
    best = options_sorted[0]
    # On peut aussi proposer la 2e option si la cote est proche
    msg = f"<b>Conseil du bot :</b> <i>{best[0]}</i> (Cote : <b>{best[1]}</b>)\n"
    if len(options_sorted) > 1 and abs(options_sorted[1][1] - best[1]) < 0.25:
        msg += f"\nAlternative : <i>{options_sorted[1][0]}</i> (Cote : <b>{options_sorted[1][1]}</b>)"
    msg += "\n⚡️ Prédiction basée sur les marchés Total de buts et Handicap."
    return msg

def format_match_complet(match):
    t1 = match.get("O1", "Équipe 1")
    t2 = match.get("O2", "Équipe 2")
    ligue = match.get("L", "Compétition non renseignée")
    ligue_en = match.get("LE", "")
    cid = match.get("CID", "")
    sport = match.get("SE", match.get("SN", "?"))
    heure = match.get("S")
    heure_fmt = ""
    if heure:
        try:
            heure_fmt = datetime.utcfromtimestamp(int(heure)).strftime('%d/%m/%Y %H:%M')
        except Exception:
            heure_fmt = str(heure)
    score = match.get("SC", {}).get("FS", {})
    stats = []
    for group in match.get("SC", {}).get("ST", []):
        for s in group.get("Value", []):
            nom = s.get("N")
            s1 = s.get("S1", "-")
            s2 = s.get("S2", "-")
            stats.append(f"  • <i>{nom}</i> : <b>{t1} {s1}</b> / <b>{t2} {s2}</b>")
    odds = match.get("E", [])
    odds_txt = []
    for o in odds:
        cote = o.get("C")
        t = o.get("T")
        g = o.get("G")
        p = o.get("P", None)
        ce = o.get("CE", None)
        odds_txt.append(f"{label_cote(t, g, p)} : <b>{cote}</b>")
    ae = match.get("AE", [])
    ae_txt = []
    for group in ae:
        g = group.get("G")
        for me in group.get("ME", []):
            cote = me.get("C")
            t = me.get("T")
            p = me.get("P", None)
            ce = me.get("CE", None)
            ae_txt.append(f"[AE] {label_cote(t, g, p)} : <b>{cote}</b>")
    # Prédiction automatique
    prediction = predire_auto(match)
    msg = f"<b>{t1}</b> <i>vs</i> <b>{t2}</b>\n"
    msg += f"🏆 <b>Compétition :</b> <i>{ligue}</i> ({ligue_en}) [CID: {cid}]\n"
    msg += f"🏅 <b>Sport :</b> <i>{sport}</i>\n"
    if heure_fmt:
        msg += f"⏰ <b>Heure :</b> <i>{heure_fmt}</i>\n"
    msg += f"🔢 <b>Score :</b> <b>{score}</b>\n"
    if odds_txt:
        msg += "💰 <b>Cotes principales :</b>\n" + "\n".join(odds_txt) + "\n"
    if ae_txt:
        msg += "💸 <b>Cotes avancées :</b>\n" + "\n".join(ae_txt) + "\n"
    if stats:
        msg += "📊 <b>Statistiques :</b>\n" + "\n".join(stats) + "\n"
    # Section prédiction bien visible
    msg += f"\n🔮 <b>Prédiction automatique :</b> {prediction}\n"
    return msg

# Adaptation de show_matches pour supporter les filtres
async def show_matches(update: Update, context: ContextTypes.DEFAULT_TYPE, filtres=None):
    users_interested.add(update.effective_user.id)
    lang = get_lang(update.effective_user.id)
    args = context.args if hasattr(context, 'args') else []
    page = 1
    competition = None
    sport_filtre = None
    statut_filtre = None
    if filtres:
        sport_filtre = filtres.get('sport')
        competition = filtres.get('competition')
        statut_filtre = filtres.get('statut')
    if args:
        for arg in args:
            if arg.isdigit():
                page = int(arg)
            else:
                competition = arg.lower()
    matchs = fetch_matches()
    # Application des filtres
    if sport_filtre:
        matchs = [m for m in matchs if detect_sport(m.get("L", ""), format_heure(m.get("SE", {}), m.get("SC", {}).get("ST", []), m.get("SC", {}).get("FS", {}))) == sport_filtre]
    if competition:
        matchs = [m for m in matchs if competition in (m.get("L", "").lower())]
    if statut_filtre:
        matchs = [m for m in matchs if get_statut_match(format_heure(m.get("SE", {}), m.get("SC", {}).get("ST", []), m.get("SC", {}).get("FS", {})), m.get("SC", {}).get("ST", []), m.get("SC", {}).get("FS", {})) == statut_filtre]
    if not matchs:
        msg_no = "❌ Aucun match FIFA virtuel en cours. Réessaie dans quelques minutes !"
        if update.message:
            await send_long_message(context.bot, update.message.chat_id, msg_no)
        elif update.callback_query:
            await send_long_message(context.bot, update.callback_query.message.chat_id, msg_no)
        return
    total_pages = (len(matchs) + MATCHS_PAR_PAGE - 1) // MATCHS_PAR_PAGE
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * MATCHS_PAR_PAGE
    end_idx = start_idx + MATCHS_PAR_PAGE
    matchs_page = matchs[start_idx:end_idx]
    MATCHS_PAR_MESSAGE = 5  # Nombre de matchs par message HTML envoyé
    for chunk in chunk_list(matchs_page, MATCHS_PAR_MESSAGE):
        message = "⚡️ <b>Matchs FIFA virtuel en direct</b> :\n\n"
        for i, match in enumerate(chunk, start_idx + 1):
            # 3. Envoi des logos d'équipes si disponibles
            if 'O1IMG' in match and match['O1IMG']:
                try:
                    await context.bot.send_photo(
                        update.message.chat_id if update.message else update.callback_query.message.chat_id,
                        photo="https://1xbet.com/" + match['O1IMG'][0]
                    )
                except Exception:
                    pass
            if 'O2IMG' in match and match['O2IMG']:
                try:
                    await context.bot.send_photo(
                        update.message.chat_id if update.message else update.callback_query.message.chat_id,
                        photo="https://1xbet.com/" + match['O2IMG'][0]
                    )
                except Exception:
                    pass
            message += format_match_complet(match) + "\n\n"
        message += f"<i>Page {page}/{total_pages}</i>"
        # 4. Boutons de navigation et de filtres (sans le filtre sport)
        reply_markup = None
        if chunk == list(chunk_list(matchs_page, MATCHS_PAR_MESSAGE))[0]:
            _, competitions = extraire_sports_competitions(fetch_matches())
            keyboard = []
            filtres_btns = [
                InlineKeyboardButton("Filtrer par compétition", callback_data="filtre_competition"),
                InlineKeyboardButton("Filtrer par statut", callback_data="filtre_statut")
            ]
            keyboard.append(filtres_btns)
            nav_btns = []
            if page > 1:
                nav_btns.append(InlineKeyboardButton("⬅️ Précédent", callback_data=f"matchs_{page-1}"))
            if page < total_pages:
                nav_btns.append(InlineKeyboardButton("Suivant ➡️", callback_data=f"matchs_{page+1}"))
            if nav_btns:
                keyboard.append(nav_btns)
            reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            if update.message:
                await send_html_long_message(context.bot, update.message.chat_id, message, parse_mode="HTML", reply_markup=reply_markup)
            elif update.callback_query:
                await send_html_long_message(context.bot, update.callback_query.message.chat_id, message, parse_mode="HTML", reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message : {e}")
            if update.message:
                await send_long_message(context.bot, update.message.chat_id, "❌ Erreur réseau ou API. Merci de réessayer plus tard.")
            elif update.callback_query:
                await send_long_message(context.bot, update.callback_query.message.chat_id, "❌ Erreur réseau ou API. Merci de réessayer plus tard.")

# Handler pour les boutons de navigation et de filtres
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    filtres = getattr(context, 'filtres', {}) if hasattr(context, 'filtres') else {}
    # Navigation page
    if data.startswith("matchs_"):
        page = int(data.split("_")[1])
        context.args = [str(page)]
        await show_matches(update, context, filtres)
        return
    # Filtres
    if data == "filtre_sport":
        sports, _ = extraire_sports_competitions(fetch_matches())
        sport_btns = [[InlineKeyboardButton(SPORTS_EMOJIS.get(s, '🏆') + ' ' + s.capitalize(), callback_data=f"sport_{s}")] for s in sports]
        await query.edit_message_text("Choisis un sport :", reply_markup=InlineKeyboardMarkup(sport_btns))
        return
    if data == "filtre_competition":
        _, competitions = extraire_sports_competitions(fetch_matches())
        comp_btns = [[InlineKeyboardButton(c, callback_data=f"competition_{c}")] for c in competitions]
        await query.edit_message_text("Choisis une compétition :", reply_markup=InlineKeyboardMarkup(comp_btns))
        return
    if data == "filtre_statut":
        statut_btns = [[InlineKeyboardButton(STATUTS_LABELS[s], callback_data=f"statut_{s}")] for s in STATUTS]
        await query.edit_message_text("Choisis un statut :", reply_markup=InlineKeyboardMarkup(statut_btns))
        return
    # Application des filtres
    if data.startswith("sport_"):
        sport = data.split("_", 1)[1]
        filtres['sport'] = sport
        await show_matches(update, context, filtres)
        return
    if data.startswith("competition_"):
        competition = data.split("_", 1)[1]
        filtres['competition'] = competition.lower()
        await show_matches(update, context, filtres)
        return
    if data.startswith("statut_"):
        statut = data.split("_", 1)[1]
        filtres['statut'] = statut
        await show_matches(update, context, filtres)
        return

# Handler d'erreur global pour Telegram
async def error_handler(update, context):
    logger.error(msg="Exception non gérée dans le handler", exc_info=context.error)
    if update and hasattr(update, 'message') and update.message:
        await send_long_message(context.bot, update.message.chat_id, "❌ Une erreur est survenue. Merci de réessayer plus tard.")

# Fonction périodique pour vérifier les buts
async def periodic_check_goals(app):
    while True:
        matchs = fetch_matches()
        for match in matchs:
            match_id = match.get('I')
            t1 = match.get("O1", "Équipe 1")
            t2 = match.get("O2", "Équipe 2")
            ligue = match.get("L") or "Compétition non renseignée"
            score = match.get("SC", {}).get("FS", {})
            buts_1 = score.get("1", 0)
            buts_2 = score.get("2", 0)
            prev = previous_scores.get(match_id, (buts_1, buts_2))
            if (buts_1, buts_2) != prev:
                # But détecté
                if (buts_1 > prev[0]) or (buts_2 > prev[1]):
                    for user_id in users_interested:
                        abos = user_subs.get(user_id, set())
                        # Si pas d'abonnement, on ne notifie pas
                        if not abos:
                            continue
                        # On notifie si l'utilisateur est abonné à l'une des équipes ou à la compétition
                        if (t1.lower() in abos) or (t2.lower() in abos) or (ligue.lower() in abos):
                            try:
                                await send_long_message(
                                    app.bot,
                                    user_id,
                                    f"⚽️ <b>BUT !</b>\n{t1} {buts_1} - {buts_2} {t2}\nCompétition : <b>{ligue}</b>",
                                    parse_mode="HTML"
                                )
                            except Exception as e:
                                logger.error(f"Erreur notification but à {user_id} : {e}")
            previous_scores[match_id] = (buts_1, buts_2)
        await asyncio.sleep(30)  # Vérifie toutes les 30 secondes

async def abonner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await send_long_message(context.bot, update.message.chat_id, "Utilisation : /abonner [équipe ou compétition]")
        return
    nom = " ".join(context.args).strip().lower()
    if not nom:
        await send_long_message(context.bot, update.message.chat_id, "Nom d'équipe ou compétition invalide.")
        return
    user_subs.setdefault(user_id, set()).add(nom)
    await send_long_message(context.bot, update.message.chat_id, f"✅ Abonnement à : <b>{nom}</b> enregistré !", parse_mode="HTML")

async def desabonner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await send_long_message(context.bot, update.message.chat_id, "Utilisation : /desabonner [équipe ou compétition]")
        return
    nom = " ".join(context.args).strip().lower()
    if user_id in user_subs and nom in user_subs[user_id]:
        user_subs[user_id].remove(nom)
        await send_long_message(context.bot, update.message.chat_id, f"❌ Désabonnement de : <b>{nom}</b> effectué.", parse_mode="HTML")
    else:
        await send_long_message(context.bot, update.message.chat_id, f"Vous n'étiez pas abonné à : <b>{nom}</b>.", parse_mode="HTML")

async def mesabos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    abos = user_subs.get(user_id, set())
    if not abos:
        await send_long_message(context.bot, update.message.chat_id, "Vous n'avez aucun abonnement.")
    else:
        for chunk in chunk_list(list(abos), 50):
            txt = "\n".join(f"• <b>{a}</b>" for a in chunk)
            await send_html_long_message(context.bot, update.message.chat_id, f"<b>Vos abonnements :</b>\n{txt}", parse_mode="HTML")

from telegram.ext import ApplicationBuilder, CommandHandler

async def start(update, context):
    await update.message.reply_text("Salut, bot opérationnel!")

def main():
    app = ApplicationBuilder().token("TON_TOKEN").build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
