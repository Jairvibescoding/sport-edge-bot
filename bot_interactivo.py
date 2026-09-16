"""
SPORT EDGE BOT - Telegram Interactivo
El usuario puede escribir comandos y el bot responde en tiempo real
"""

import requests
import json
import time
import sys
import io
import os
from datetime import datetime

# Configurar encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Telegram
TELEGRAM_TOKEN = "8563502125:AAGQ9IOEAfPgLlKkDoUeIkJ5_3llVKvWbCA"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "bets_database.json")

# Tus apuestas
BETS = {
    1: {"pick": "Yamamoto O7.5 Ks", "event": "Dodgers vs Reds", "stake": 53, "potential_win": 100.70, "player": "Yamamoto", "line": 7.5, "status": "pending", "house": "micasino"},
    2: {"pick": "Misiorowski O8.5 Ks", "event": "Brewers vs Pirates", "stake": 28, "potential_win": 60.20, "player": "Misiorowski", "line": 8.5, "status": "pending", "house": "micasino"},
    3: {"pick": "Stephens +2.5", "event": "Stephens vs Tjen", "stake": 30, "potential_win": 58.50, "player": "Stephens", "line": 2.5, "status": "pending", "house": "micasino"},
    4: {"pick": "Sanchez Ganara", "event": "Nationals vs Phillies", "stake": 285, "potential_win": 532, "player": "Sanchez", "line": 0, "status": "pending", "house": "1xBet"},
    5: {"pick": "Sandoval O5.5 Ks", "event": "Rangers vs Red Sox", "stake": 30, "potential_win": 64.50, "player": "Sandoval", "line": 5.5, "status": "pending", "house": "micasino"},
}


def load_database():
    """Carga la base de datos"""
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"bets": {}, "stats": {"wins": 0, "losses": 0, "pending": 5, "bankroll": 3065}}


def save_database(data):
    """Guarda la base de datos"""
    data["last_updated"] = datetime.now().isoformat()
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def send_message(chat_id, text, parse_mode="HTML"):
    """Envia mensaje"""
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except:
        return None


def get_updates(offset=None):
    """Obtiene nuevos mensajes"""
    url = f"{TELEGRAM_API}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    
    try:
        response = requests.get(url, params=params, timeout=35)
        return response.json()
    except:
        return {"result": []}


def handle_start(chat_id):
    """Maneja /start"""
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


def handle_status(chat_id):
    """Maneja /status"""
    data = load_database()
    stats = data.get("stats", {})
    
    msg = f"""
📊 <b>ESTADO DE APUESTAS</b>

✅ Ganadas: {stats.get('wins', 0)}
❌ Perdidas: {stats.get('losses', 0)}
⏳ Pendientes: {stats.get('pending', 5)}

💰 <b>Bankroll:</b> {stats.get('bankroll', 3065)} Bs
📈 <b>Ganancia:</b> {'+' if stats.get('total_profit', 0) >= 0 else ''}{stats.get('total_profit', 0):.2f} Bs

<b>Apuestas hoy:</b>
"""
    
    for bet_id, bet in BETS.items():
        status = data.get("bets", {}).get(str(bet_id), {}).get("result", "pending")
        emoji = "✅" if status == "win" else "❌" if status == "loss" else "⏳"
        msg += f"{emoji} #{bet_id} {bet['pick']}\n"
    
    send_message(chat_id, msg)


def handle_bankroll(chat_id):
    """Maneja /bankroll"""
    data = load_database()
    stats = data.get("stats", {})
    bankroll = stats.get("bankroll", 3065)
    profit = stats.get("total_profit", 0)
    
    msg = f"""
💰 <b>TU BANKROLL</b>

Bankroll actual: <b>{bankroll} Bs</b>
Ganancia del día: <b>{'+' if profit >= 0 else ''}{profit:.2f} Bs</b>

<b>Distribución:</b>
• 1xBet: ~2,365 Bs
• micasino: ~{bankroll - 2365} Bs

<b>Próxima apuesta sugerida:</b> {bankroll * 0.02:.0f} Bs (2%)
    """
    send_message(chat_id, msg)


def handle_stats(chat_id):
    """Maneja /stats"""
    data = load_database()
    stats = data.get("stats", {})
    
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
• Yield: {roi:.1f}%

<b>Rendimiento:</b>
• Apostado: {stats.get('total_staked', 0)} Bs
• Ganancia: {'+' if stats.get('total_profit', 0) >= 0 else ''}{stats.get('total_profit', 0):.2f} Bs
    """
    send_message(chat_id, msg)


def handle_picks(chat_id):
    """Maneja /picks"""
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
    """Maneja /win"""
    if bet_id not in BETS:
        send_message(chat_id, "❌ Apuesta no encontrada. Usa /picks para ver las apuestas.")
        return
    
    bet = BETS[bet_id]
    profit = bet["potential_win"] - bet["stake"]
    
    # Actualizar base de datos
    data = load_database()
    data["bets"][str(bet_id)]["result"] = "win"
    data["bets"][str(bet_id)]["profit"] = profit
    data["stats"]["wins"] = data["stats"].get("wins", 0) + 1
    data["stats"]["pending"] = data["stats"].get("pending", 5) - 1
    data["stats"]["total_profit"] = data["stats"].get("total_profit", 0) + profit
    data["stats"]["bankroll"] = 3065 + data["stats"]["total_profit"]
    save_database(data)
    
    msg = f"""
🏆 <b>¡{bet['player'].upper()} GANÓ!</b>

✅ {bet['pick']}
💰 Ganancia: +{profit:.2f} Bs

📊 <b>Actualizado:</b>
• Wins: {data['stats']['wins']}
• Bankroll: {data['stats']['bankroll']} Bs
    """
    send_message(chat_id, msg)


def handle_loss(chat_id, bet_id):
    """Maneja /loss"""
    if bet_id not in BETS:
        send_message(chat_id, "❌ Apuesta no encontrada. Usa /picks para ver las apuestas.")
        return
    
    bet = BETS[bet_id]
    
    # Actualizar base de datos
    data = load_database()
    data["bets"][str(bet_id)]["result"] = "loss"
    data["bets"][str(bet_id)]["profit"] = -bet["stake"]
    data["stats"]["losses"] = data["stats"].get("losses", 0) + 1
    data["stats"]["pending"] = data["stats"].get("pending", 5) - 1
    data["stats"]["total_profit"] = data["stats"].get("total_profit", 0) - bet["stake"]
    data["stats"]["bankroll"] = 3065 + data["stats"]["total_profit"]
    save_database(data)
    
    msg = f"""
❌ <b>{bet['player'].upper()} PERDIÓ</b>

❌ {bet['pick']}
💸 Pérdida: -{bet['stake']} Bs

📊 <b>Actualizado:</b>
• Losses: {data['stats']['losses']}
• Bankroll: {data['stats']['bankroll']} Bs
    """
    send_message(chat_id, msg)


def handle_ayuda(chat_id):
    """Maneja /ayuda"""
    handle_start(chat_id)


def handle_como_estas(chat_id):
    """Responde 'como estas'"""
    data = load_database()
    stats = data.get("stats", {})
    
    msg = f"""
😊 <b>¡Todo bien, gracias!</b>

Yo aquí monitoreando tus apuestas 24/7 🤖

<b>Tu estado hoy:</b>
• Bankroll: {stats.get('bankroll', 3065)} Bs
• Apuestas pendientes: {stats.get('pending', 5)}
• Ganancia: {'+' if stats.get('total_profit', 0) >= 0 else ''}{stats.get('total_profit', 0):.2f} Bs

¿En qué te puedo ayudar? 🚀
    """
    send_message(chat_id, msg)


def handle_gracias(chat_id):
    """Responde 'gracias'"""
    msg = """
¡De nada! 😊

Para eso estoy aquí, tu bot personal de apuestas 🤖

Escribe /ayuda si necesitas algo más.
    """
    send_message(chat_id, msg)


def handle_hora(chat_id):
    """Responde la hora"""
    now = datetime.now().strftime("%H:%M:%S")
    msg = f"""
🕐 <b>Hora actual:</b> {now}

¿Necesitas algo más? 🚀
    """
    send_message(chat_id, msg)


def handle_default(chat_id, text):
    """Respuesta por defecto"""
    msg = f"""
🤔 No entendi: "<i>{text}</i>"

<b>Puedo ayudarte con:</b>

📊 /status - Ver tus apuestas
💰 /bankroll - Ver tu dinero
📈 /stats - Ver estadisticas
🎯 /picks - Ver tus picks
❓ /ayuda - Ver todos los comandos

O escribe en palabras simples:
• hola → Bienvenida
• apuestas → Ver apuestas
• dinero → Ver bankroll
• gracias → De nada 😊
    """
    send_message(chat_id, msg)


def handle_response_bien(chat_id):
    """Responde cuando el usuario dice que esta bien"""
    msg = """
😊 ¡Genial que estes bien!

Yo tambien aqui monitoreando tus apuestas 24/7 🤖

¿Necesitas algo? Puedo ayudarte con:
• Ver tus apuestas (/status)
• Ver tu dinero (/bankroll)
• Ver picks (/picks)
    """
    send_message(chat_id, msg)


def handle_response_mal(chat_id):
    """Responde cuando el usuario dice que esta mal"""
    msg = """
😔 Ay, que mal! Espero que todo mejore.

Mientras tanto, aqui estoy yo apoyandote con tus apuestas 💪

¿Quieres ver como van tus picks? Usa /status

¡Las cosas van a mejorar! 🚀
    """
    send_message(chat_id, msg)


def handle_chiste(chat_id):
    """Dice un chiste"""
    import random
    chistes = [
        "¿Por que el apostador fue al medico? Porque tenia muchos \"over\" de presion 😂",
        "¿Que le dijo un numero a otro numero? Par, que hace falta para ser par 🤓",
        "Un apostador entra a un bar y dice: ¿Tiene cerveza sin alcohol? El barman dice: Tenemos una sin ganar 🍺",
        "¿Cual es el deporte favorito de los apostadores? El que esta giving good odds 📊"
    ]
    msg = f"😂 {random.choice(chistes)}"
    send_message(chat_id, msg)


def process_message(message):
    """Procesa un mensaje recibido"""
    chat_id = message["chat"]["id"]
    text = message.get("text", "").lower().strip()
    
    # Normalizar texto: quitar espacios extra y puntuación al final
    import re
    text = re.sub(r'\s+', ' ', text)  # Quitar espacios múltiples
    text = text.strip('?!.,;:')  # Quitar puntuación al final
    
    print(f"[MSG] Chat {chat_id}: {text}")
    
    # Comandos - NORMALIZADOS
    if text in ["/start", "hola", "holi", "hello", "hey", "buenas", "buenos dias", "buenas tardes", "buenas noches"]:
        handle_start(chat_id)
    elif text in ["como estas", "como estas", "como te va", "que tal", "que onda", "que hay", "como andas", "como va", "que hubo", "que pasas", "que ondas", "how are you", "como stas", "cm stas", "xd", "holis", "saludos"]:
        handle_como_estas(chat_id)
    elif text in ["gracias", "gracias!", "thanks", "thx", "agradecido", "te agradezco", " thanks"]:
        handle_gracias(chat_id)
    elif text in ["que hora es", "hora", "hora actual", "son las", "que hora son"]:
        handle_hora(chat_id)
    elif text in ["que hay de nuevo", "novedades", "news", "update", "actualizame", "que paso", "que hubo"]:
        handle_status(chat_id)
    elif text in ["ayuda", "help", "comandos", "commands", "que puedo hacer", "opciones", "menu", "comando"]:
        handle_ayuda(chat_id)
    elif text in ["apuestas", "bets", "mis apuestas", "mis picks", "que apuste", "que tengo"]:
        handle_status(chat_id)
    elif text in ["dinero", "cash", "cuanto tengo", "balance", "banca", "bankroll", "cuanto dinero"]:
        handle_bankroll(chat_id)
    elif text in ["estadisticas", "statistics", "stats", "resultados", "metricas", "numeros"]:
        handle_stats(chat_id)
    elif text in ["picks", "selecciones", "predicciones", "que apuesto", "que jugar", "mejores picks"]:
        handle_picks(chat_id)
    elif text in ["bien", "bien!", "todo bien", "perfecto", "genial", "excelente", "ok", "dale", "va", "vamo", "fino", "chido", "padre", "cool"]:
        handle_response_bien(chat_id)
    elif text in ["mal", "mal!", "regular", "no mucho", "triste", "feo"]:
        handle_response_mal(chat_id)
    elif text in ["chiste", "dime algo gracioso", "jaja", "risa", "funny"]:
        handle_chiste(chat_id)
    elif text.startswith("/status") or text == "status":
        handle_status(chat_id)
    elif text.startswith("/bankroll") or text == "bankroll":
        handle_bankroll(chat_id)
    elif text.startswith("/stats") or text == "stats":
        handle_stats(chat_id)
    elif text.startswith("/picks") or text == "picks":
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
    elif text.startswith("/ayuda") or text == "ayuda":
        handle_ayuda(chat_id)
    else:
        # Respuesta por defecto - más amigable
        handle_default(chat_id, text)


def main():
    """Loop principal del bot interactivo"""
    print("=" * 60)
    print("SPORT EDGE BOT - Interactivo")
    print("=" * 60)
    print("Escuchando mensajes en Telegram...")
    print("Comandos: /start, /status, /bankroll, /stats, /picks")
    print("Marcar: /win 1, /loss 1, etc.")
    print("Presiona Ctrl+C para detener")
    print("=" * 60)
    
    offset = None
    
    while True:
        try:
            updates = get_updates(offset)
            
            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                
                if "message" in update:
                    process_message(update["message"])
            
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("\nBot detenido")
            send_message("8831402423", "🤖 Bot detenido. Reinicia con: python bot_interactivo.py")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
