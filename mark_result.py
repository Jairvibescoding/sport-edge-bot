"""
SPORT EDGE BOT - Marcar resultados
Uso: python mark_result.py [win/loss] [bet_id]
Ejemplo: python mark_result.py win 1
"""

import sys
import requests

# Configuración
TELEGRAM_TOKEN = "8563502125:AAGQ9IOEAfPgLlKkDoUeIkJ5_3llVKvWbCA"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Base de datos de apuestas
BETS = {
    1: {"pick": "Yamamoto O7.5 Ks", "event": "Dodgers vs Reds", "stake": 53, "potential_win": 100.70, "house": "micasino"},
    2: {"pick": "Misiorowski O8.5 Ks", "event": "Brewers vs Pirates", "stake": 28, "potential_win": 60.20, "house": "micasino"},
    3: {"pick": "Stephens +2.5", "event": "Stephens vs Tjen", "stake": 30, "potential_win": 58.50, "house": "micasino"},
    4: {"pick": "Sánchez Ganará", "event": "Nationals vs Phillies", "stake": 285, "potential_win": 532, "house": "1xBet"},
    5: {"pick": "Sandoval O5.5 Ks", "event": "Rangers vs Red Sox", "stake": 30, "potential_win": 64.50, "house": "micasino"},
}


def get_chat_id():
    """Obtiene el chat_id del usuario"""
    url = f"{TELEGRAM_API}/getUpdates"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("result"):
            for update in data["result"]:
                if "message" in update:
                    return update["message"]["chat"]["id"]
    except Exception as e:
        print(f"Error: {e}")
    return None


def send_message(chat_id, text):
    """Envía mensaje a Telegram"""
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None


def mark_win(bet_id):
    """Marca apuesta como ganada y notifica"""
    if bet_id not in BETS:
        print(f"❌ Apuesta {bet_id} no encontrada")
        return
    
    bet = BETS[bet_id]
    profit = bet["potential_win"] - bet["stake"]
    
    chat_id = get_chat_id()
    if not chat_id:
        print("❌ No se pudo obtener chat_id")
        return
    
    msg = f"""
🏆 <b>¡{bet['pick'].split()[0].upper()} GANÓ!</b> 🏆

✅ {bet['pick']}
📊 {bet['event']}
💰 Cuota: {bet['house']}
💵 Stake: {bet['stake']} Bs
🎉 <b>Ganancia: +{profit:.2f} Bs</b>

📈 ¡Sigue así! 💪
    """
    send_message(chat_id, msg)
    print(f"✅ Notificación enviada: {bet['pick']} GANÓ +{profit:.2f} Bs")


def mark_loss(bet_id):
    """Marca apuesta como perdida y notifica"""
    if bet_id not in BETS:
        print(f"❌ Apuesta {bet_id} no encontrada")
        return
    
    bet = BETS[bet_id]
    
    chat_id = get_chat_id()
    if not chat_id:
        print("❌ No se pudo obtener chat_id")
        return
    
    msg = f"""
❌ <b>{bet['pick'].split()[0].upper()} PERDIÓ</b>

❌ {bet['pick']}
📊 {bet['event']}
💰 Cuota: {bet['house']}
💸 <b>Pérdida: -{bet['stake']} Bs</b>

💪 Siguiente apuesta! 🎯
    """
    send_message(chat_id, msg)
    print(f"✅ Notificación enviada: {bet['pick']} PERDIÓ -{bet['stake']} Bs")


def main():
    if len(sys.argv) < 3:
        print("Uso: python mark_result.py [win/loss] [bet_id]")
        print("Ejemplo: python mark_result.py win 1")
        print("\nApuestas disponibles:")
        for id, bet in BETS.items():
            print(f"  {id}. {bet['pick']} ({bet['event']})")
        return
    
    action = sys.argv[1].lower()
    bet_id = int(sys.argv[2])
    
    if action == "win":
        mark_win(bet_id)
    elif action == "loss":
        mark_loss(bet_id)
    else:
        print(f"❌ Acción no válida: {action}")


if __name__ == "__main__":
    main()
