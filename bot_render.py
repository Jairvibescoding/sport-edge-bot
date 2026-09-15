"""
SPORT EDGE BOT - Telegram Interactivo
Versión optimizada para Render (24/7)
"""

import requests
import json
import time
import sys
import io
import os
import re
import random
from datetime import datetime
from flask import Flask, request, jsonify

# Configurar encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Telegram
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '8563502125:AAGQ9IOEAfPgLlKkDoUeIkJ5_3llVKvWbCA')
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Tus apuestas
BETS = {
    1: {"pick": "Yamamoto O7.5 Ks", "event": "Dodgers vs Reds", "stake": 53, "potential_win": 100.70, "player": "Yamamoto", "line": 7.5, "status": "pending", "house": "micasino"},
    2: {"pick": "Misiorowski O8.5 Ks", "event": "Brewers vs Pirates", "stake": 28, "potential_win": 60.20, "player": "Misiorowski", "line": 8.5, "status": "pending", "house": "micasino"},
    3: {"pick": "Stephens +2.5", "event": "Stephens vs Tjen", "stake": 30, "potential_win": 58.50, "player": "Stephens", "line": 2.5, "status": "pending", "house": "micasino"},
    4: {"pick": "Sanchez Ganara", "event": "Nationals vs Phillies", "stake": 285, "potential_win": 532, "player": "Sanchez", "line": 0, "status": "pending", "house": "1xBet"},
    5: {"pick": "Sandoval O5.5 Ks", "event": "Rangers vs Red Sox", "stake": 30, "potential_win": 64.50, "player": "Sandoval", "line": 5.5, "status": "pending", "house": "micasino"},
}

# Base de datos en memoria (para Render)
database = {
    "bets": {},
    "stats": {
        "total_bets": 5,
        "wins": 0,
        "losses": 0,
        "pending": 5,
        "total_staked": 426,
        "total_profit": 0,
        "bankroll": 3065
    }
}

app = Flask(__name__)

# ============================================
# FUNCIONES DE TELEGRAM
# ============================================

def send_message(chat_id, text, parse_mode="HTML"):
    """Envia mensaje a Telegram"""
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except:
        return None

# ============================================
# HANDLERS
# ============================================

def handle_start(chat_id):
    """Bienvenida"""
    msg = """
🏆 <b>SPORT EDGE BOT</b> 🏆

¡Hola! Soy tu asistente de apuestas deportivas.

<b>Comandos disponibles:</b>

📊 /status - Ver estado de tus apuestas
💰 /bankroll - Ver tu bankroll
📈 /stats - Ver estadísticas del día
🎯 /picks - Ver tus picks de hoy
❓ /ayuda - Ver esta ayuda

<b>Marcar resultados:</b>
/win [número] - Marcar como ganada
/loss [número] - Marcar como perdida

<b>Ejemplo:</b>
/win 1 → Marca Yamamoto como ganada

Escribe cualquier comando y te respondo! 🚀
    """
    send_message(chat_id, msg)

def handle_como_estas(chat_id):
    """Responde como estas"""
    msg = """
😊 <b>¡Todo bien, gracias!</b>

Yo aquí monitoreando tus apuestas 24/7 🤖

<b>Tu estado hoy:</b>
• Bankroll: 3065 Bs
• Apuestas pendientes: 5
• Ganancia: +0.00 Bs

¿En qué te puedo ayudar? 🚀
    """
    send_message(chat_id, msg)

def handle_gracias(chat_id):
    """Responde gracias"""
    msg = """
¡De nada! 😊

Para eso estoy aquí, tu bot personal de apuestas 🤖

Escribe /ayuda si necesitas algo más.
    """
    send_message(chat_id, msg)

def handle_hora(chat_id):
    """Responde hora"""
    now = datetime.now().strftime("%H:%M:%S")
    msg = f"""
🕐 <b>Hora actual:</b> {now}

¿Necesitas algo más? 🚀
    """
    send_message(chat_id, msg)

def handle_status(chat_id):
    """Ver apuestas"""
    stats = database.get("stats", {})
    
    msg = f"""
📊 <b>ESTADO DE APUESTAS</b>

✅ Ganadas: {stats.get('wins', 0)}
❌ Perdidas: {stats.get('losses', 0)}
⏳ Pendientes: {stats.get('pending', 5)}

💰 <b>Bankroll:</b> {stats.get('bankroll', 3065)} Bs
📈 <b>Ganancia:</b> +{stats.get('total_profit', 0):.2f} Bs

<b>Apuestas hoy:</b>
"""
    
    for bet_id, bet in BETS.items():
        status = database.get("bets", {}).get(str(bet_id), {}).get("result", "pending")
        emoji = "✅" if status == "win" else "❌" if status == "loss" else "⏳"
        msg += f"{emoji} #{bet_id} {bet['pick']}\n"
    
    send_message(chat_id, msg)

def handle_bankroll(chat_id):
    """Ver bankroll"""
    stats = database.get("stats", {})
    bankroll = stats.get("bankroll", 3065)
    profit = stats.get("total_profit", 0)
    
    msg = f"""
💰 <b>TU BANKROLL</b>

Bankroll actual: <b>{bankroll} Bs</b>
Ganancia del día: <b>+{profit:.2f} Bs</b>

<b>Distribución:</b>
• 1xBet: ~2,365 Bs
• micasino: ~{bankroll - 2365} Bs

<b>Próxima apuesta sugerida:</b> {bankroll * 0.02:.0f} Bs (2%)
    """
    send_message(chat_id, msg)

def handle_stats(chat_id):
    """Ver estadísticas"""
    stats = database.get("stats", {})
    
    wins = stats.get("wins", 0)
    losses = stats.get("losses", 0)
    total = wins + losses
    
    hit_rate = (wins / total * 100) if total > 0 else 0
    roi = (stats.get("total_profit", 0) / stats.get("total_staked", 426) * 100) if stats.get("total_staked", 0) > 0 else 0
    
    msg = f"""
📈 <b>ESTADÍSTICAS DEL DÍA</b>

<b>Resultados:</b>
• Ganadas: {wins}
• Perdidas: {losses}
• Total: {total}

<b>Métricas:</b>
• Hit Rate: {hit_rate:.1f}%
• ROI: {roi:.1f}%

<b>Rendimiento:</b>
• Apostado: {stats.get('total_staked', 0)} Bs
• Ganancia: +{stats.get('total_profit', 0):.2f} Bs
    """
    send_message(chat_id, msg)

def handle_picks(chat_id):
    """Ver picks"""
    msg = """
🎯 <b>TUS PICKS DE HOY</b>

<b>MLB Props:</b>
1️⃣ Yamamoto O7.5 Ks @ 1.90
   💰 53 Bs → Ganar: 100.70 Bs
   📊 EV: +21.6%

2️⃣ Misiorowski O8.5 Ks @ 2.15
   💰 28 Bs → Ganar: 60.20 Bs
   📊 EV: +3.2%

<b>Tenis:</b>
3️⃣ Stephens +2.5 @ 1.95
   💰 30 Bs → Ganar: 58.50 Bs
   📊 EV: +7.3%

<b>MLB Win:</b>
4️⃣ Sanchez Ganara @ 1.87
   💰 285 Bs → Ganar: 532 Bs
   📊 EV: +19.7%

<b>MLB Props:</b>
5️⃣ Sandoval O5.5 Ks @ 2.15
   💰 30 Bs → Ganar: 64.50 Bs
   📊 EV: +16.1%

📈 <b>Total:</b> 426 Bs (13.9%)
🎯 <b>EV promedio:</b> +13.6%
    """
    send_message(chat_id, msg)

def handle_win(chat_id, bet_id):
    """Marcar ganada"""
    if bet_id not in BETS:
        send_message(chat_id, "❌ Apuesta no encontrada.")
        return
    
    bet = BETS[bet_id]
    profit = bet["potential_win"] - bet["stake"]
    
    database["bets"][str(bet_id)] = {"result": "win", "profit": profit}
    database["stats"]["wins"] = database["stats"].get("wins", 0) + 1
    database["stats"]["pending"] = database["stats"].get("pending", 5) - 1
    database["stats"]["total_profit"] = database["stats"].get("total_profit", 0) + profit
    database["stats"]["bankroll"] = 3065 + database["stats"]["total_profit"]
    
    msg = f"""
🏆 <b>¡{bet['player'].upper()} GANÓ!</b>

✅ {bet['pick']}
💰 Ganancia: +{profit:.2f} Bs

📊 <b>Actualizado:</b>
• Wins: {database['stats']['wins']}
• Bankroll: {database['stats']['bankroll']} Bs
    """
    send_message(chat_id, msg)

def handle_loss(chat_id, bet_id):
    """Marcar perdida"""
    if bet_id not in BETS:
        send_message(chat_id, "❌ Apuesta no encontrada.")
        return
    
    bet = BETS[bet_id]
    
    database["bets"][str(bet_id)] = {"result": "loss", "profit": -bet["stake"]}
    database["stats"]["losses"] = database["stats"].get("losses", 0) + 1
    database["stats"]["pending"] = database["stats"].get("pending", 5) - 1
    database["stats"]["total_profit"] = database["stats"].get("total_profit", 0) - bet["stake"]
    database["stats"]["bankroll"] = 3065 + database["stats"]["total_profit"]
    
    msg = f"""
❌ <b>{bet['player'].upper()} PERDIÓ</b>

❌ {bet['pick']}
💸 Pérdida: -{bet['stake']} Bs

📊 <b>Actualizado:</b>
• Losses: {database['stats']['losses']}
• Bankroll: {database['stats']['bankroll']} Bs
    """
    send_message(chat_id, msg)

def handle_ayuda(chat_id):
    """Ayuda"""
    handle_start(chat_id)

def handle_como_estas(chat_id):
    """Como estas"""
    msg = """
😊 ¡Todo bien, gracias!

Yo aquí monitoreando tus apuestas 24/7 🤖

¿En qué te puedo ayudar? 🚀
    """
    send_message(chat_id, msg)

def handle_gracias(chat_id):
    """Gracias"""
    msg = """
¡De nada! 😊

Para eso estoy aquí, tu bot personal de apuestas 🤖

Escribe /ayuda si necesitas algo más.
    """
    send_message(chat_id, msg)

def handle_hora(chat_id):
    """Hora"""
    now = datetime.now().strftime("%H:%M:%S")
    msg = f"🕐 Hora actual: {now}"
    send_message(chat_id, msg)

def handle_response_bien(chat_id):
    """Respuesta bien"""
    msg = "😊 ¡Genial! ¿Necesitas algo? Usa /status para ver tus apuestas."
    send_message(chat_id, msg)

def handle_response_mal(chat_id):
    """Respuesta mal"""
    msg = "😔 Ay, que mal! Aquí estoy apoyándote. Usa /status para ver cómo van tus picks."
    send_message(chat_id, msg)

def handle_chiste(chat_id):
    """Chiste"""
    chistes = [
        "¿Por qué el apostador fue al medico? Porque tenia muchos over de presion 😂",
        "¿Que le dijo un numero a otro numero? Par, que hace falta para ser par 🤓",
        "Un apostador entra a un bar y dice: ¿Tiene cerveza sin alcohol? El barman dice: Tenemos una sin ganar 🍺"
    ]
    msg = f"😂 {random.choice(chistes)}"
    send_message(chat_id, msg)

def handle_default(chat_id, text):
    """Respuesta por defecto"""
    msg = f"""
🤔 No entendi: "<i>{text}</i>"

<b>Puedo ayudarte con:</b>
📊 /status - Ver apuestas
💰 /bankroll - Ver dinero
📈 /stats - Ver estadisticas
🎯 /picks - Ver picks
❓ /ayuda - Ver comandos

O escribe: hola, que tal, gracias
    """
    send_message(chat_id, msg)

# ============================================
# WEBHOOK - Recibe mensajes de Telegram
# ============================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """Recibe mensajes de Telegram"""
    data = request.get_json()
    
    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "").lower().strip()
        
        # Normalizar texto
        text = re.sub(r'\s+', ' ', text)
        text = text.strip('?!.,;:')
        
        print(f"[MSG] {chat_id}: {text}")
        
        # Procesar comando
        if text in ["/start", "hola", "holi", "hello", "hey", "buenas"]:
            handle_start(chat_id)
        elif text in ["como estas", "que tal", "que onda", "que hay", "como andas"]:
            handle_como_estas(chat_id)
        elif text in ["gracias", "thanks", "thx"]:
            handle_gracias(chat_id)
        elif text in ["hora", "que hora es"]:
            handle_hora(chat_id)
        elif text in ["bien", "todo bien", "perfecto", "genial"]:
            handle_response_bien(chat_id)
        elif text in ["mal", "regular", "triste"]:
            handle_response_mal(chat_id)
        elif text in ["chiste", "dime algo gracioso"]:
            handle_chiste(chat_id)
        elif text == "/status" or text in ["apuestas", "mis apuestas"]:
            handle_status(chat_id)
        elif text == "/bankroll" or text in ["dinero", "cuanto tengo"]:
            handle_bankroll(chat_id)
        elif text == "/stats" or text in ["estadisticas", "resultados"]:
            handle_stats(chat_id)
        elif text == "/picks" or text in ["picks", "selecciones"]:
            handle_picks(chat_id)
        elif text.startswith("/win"):
            try:
                bet_id = int(text.split()[1])
                handle_win(chat_id, bet_id)
            except:
                send_message(chat_id, "Uso: /win [numero]\nEjemplo: /win 1")
        elif text.startswith("/loss"):
            try:
                bet_id = int(text.split()[1])
                handle_loss(chat_id, bet_id)
            except:
                send_message(chat_id, "Uso: /loss [numero]\nEjemplo: /loss 1")
        elif text in ["/ayuda", "ayuda", "help", "comandos"]:
            handle_ayuda(chat_id)
        else:
            handle_default(chat_id, text)
    
    return jsonify({"ok": True})

@app.route('/')
def home():
    """Pagina principal"""
    return """
    <h1>🏆 SPORT EDGE BOT</h1>
    <p>Bot de apuestas deportivas activo 24/7</p>
    <p>Status: ✅ ONLINE</p>
    """

@app.route('/health')
def health():
    """Health check para Render"""
    return jsonify({"status": "ok", "bot": "sport-edge"})

# ============================================
# CONFIGURAR WEBHOOK
# ============================================

def setup_webhook():
    """Configura el webhook de Telegram"""
    url = os.environ.get('RENDER_EXTERNAL_URL', 'https://sport-edge-bot.onrender.com')
    webhook_url = f"{url}/webhook"
    
    # Configurar webhook
    api_url = f"{TELEGRAM_API}/setWebhook"
    payload = {"url": webhook_url}
    
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        print(f"Webhook configurado: {webhook_url}")
        print(f"Respuesta: {response.json()}")
    except Exception as e:
        print(f"Error configurando webhook: {e}")

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("SPORT EDGE BOT - Iniciando en Render...")
    print("=" * 50)
    
    # Configurar webhook
    setup_webhook()
    
    # Iniciar servidor
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
