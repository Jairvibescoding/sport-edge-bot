"""
SPORT EDGE BOT - Telegram Notifications
Monitorea apuestas y envía notificaciones en tiempo real
"""

import requests
import json
import time
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
TELEGRAM_TOKEN = "8563502125:AAGQ9IOEAfPgLlKkDoUeIkJ5_3llVKvWbCA"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Base de datos de apuestas del día
BETS = [
    {
        "id": 1,
        "boleto": "5420883747",
        "event": "Dodgers vs Reds",
        "pick": "Yamamoto O7.5 Ks",
        "house": "micasino",
        "odds": 1.90,
        "stake": 53,
        "potential_win": 100.70,
        "ev": 21.6,
        "status": "pending",
        "sport": "MLB",
        "time": "18:40"
    },
    {
        "id": 2,
        "boleto": "5420980491",
        "event": "Brewers vs Pirates",
        "pick": "Misiorowski O8.5 Ks",
        "house": "micasino",
        "odds": 2.15,
        "stake": 28,
        "potential_win": 60.20,
        "ev": 3.2,
        "status": "pending",
        "sport": "MLB",
        "time": "18:40"
    },
    {
        "id": 3,
        "boleto": "5421161569",
        "event": "Stephens vs Tjen",
        "pick": "Stephens +2.5",
        "house": "micasino",
        "odds": 1.95,
        "stake": 30,
        "potential_win": 58.50,
        "ev": 7.3,
        "status": "pending",
        "sport": "Tenis",
        "time": "WTA"
    },
    {
        "id": 4,
        "boleto": "87318108523",
        "event": "Nationals vs Phillies",
        "pick": "Sánchez Ganará",
        "house": "1xBet",
        "odds": 1.87,
        "stake": 285,
        "potential_win": 532,
        "ev": 19.7,
        "status": "pending",
        "sport": "MLB",
        "time": "18:45"
    },
    {
        "id": 5,
        "boleto": "5421384041",
        "event": "Rangers vs Red Sox",
        "pick": "Sandoval O5.5 Ks",
        "house": "micasino",
        "odds": 2.15,
        "stake": 30,
        "potential_win": 64.50,
        "ev": 16.1,
        "status": "pending",
        "sport": "MLB",
        "time": "19:05"
    }
]

# Estado global
BANKROLL = 3065
BANKROLL_INICIAL = 3065


def send_message(chat_id, text, parse_mode="HTML"):
    """Envía mensaje a Telegram"""
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error enviando mensaje: {e}")
        return None


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
        print(f"Error obteniendo chat_id: {e}")
    return None


def send_welcome():
    """Envía mensaje de bienvenida"""
    chat_id = get_chat_id()
    if not chat_id:
        print("No se pudo obtener chat_id. Envía un mensaje a @Sport_edge_jair_bot primero.")
        return
    
    welcome_msg = f"""
🏆 <b>SPORT EDGE BOT ACTIVADO</b> 🏆

📊 <b>Tus apuestas de hoy:</b>

1️⃣ Yamamoto O7.5 Ks @ 1.90
   💰 53 Bs → Ganar: 100.70 Bs
   ⏰ 18:40 | EV: +21.6%

2️⃣ Misiorowski O8.5 Ks @ 2.15
   💰 28 Bs → Ganar: 60.20 Bs
   ⏰ 18:40 | EV: +3.2%

3️⃣ Stephens +2.5 @ 1.95
   💰 30 Bs → Ganar: 58.50 Bs
   ⏰ WTA | EV: +7.3%

4️⃣ Sánchez Ganará @ 1.87
   💰 285 Bs → Ganar: 532 Bs
   ⏰ 18:45 | EV: +19.7%

5️⃣ Sandoval O5.5 Ks @ 2.15
   💰 30 Bs → Ganar: 64.50 Bs
   ⏰ 19:05 | EV: +16.1%

📈 <b>Total apostado:</b> 426 Bs (13.9%)
🎯 <b>EV promedio:</b> +13.6%

💡 Te notificaré cuando ganes o pierdas cada apuesta.
    """
    send_message(chat_id, welcome_msg)
    print(f"✅ Bienvenida enviada a chat_id: {chat_id}")


def notify_win(bet, profit):
    """Notifica victoria"""
    chat_id = get_chat_id()
    if not chat_id:
        return
    
    msg = f"""
🏆 <b>¡{bet['pick'].split()[0].upper()} GANÓ!</b> 🏆

✅ {bet['pick']}
📊 {bet['event']}
💰 Cuota: {bet['odds']}
💵 Stake: {bet['stake']} Bs
🎉 <b>Ganancia: +{profit:.2f} Bs</b>

📈 <b>Total hoy:</b> {get_wins()}/5 ✅
💰 <b>Bankroll:</b> {BANKROLL + profit:.0f} Bs
    """
    send_message(chat_id, msg)


def notify_loss(bet):
    """Notifica derrota"""
    chat_id = get_chat_id()
    if not chat_id:
        return
    
    msg = f"""
❌ <b>{bet['pick'].split()[0].upper()} PERDIÓ</b>

❌ {bet['pick']}
📊 {bet['event']}
💰 Cuota: {bet['odds']}
💸 <b>Pérdida: -{bet['stake']} Bs</b>

📈 <b>Total hoy:</b> {get_wins()}/5
💰 <b>Bankroll:</b> {BANKROLL - bet['stake']:.0f} Bs
    """
    send_message(chat_id, msg)


def get_wins():
    """Cuenta apuestas ganadas"""
    return sum(1 for b in BETS if b["status"] == "win")


def get_losses():
    """Cuenta apuestas perdidas"""
    return sum(1 for b in BETS if b["status"] == "loss")


def send_summary():
    """Envía resumen del día"""
    chat_id = get_chat_id()
    if not chat_id:
        return
    
    wins = get_wins()
    losses = get_losses()
    pending = 5 - wins - losses
    
    total_won = sum(b["potential_win"] for b in BETS if b["status"] == "win")
    total_lost = sum(b["stake"] for b in BETS if b["status"] == "loss")
    net_profit = total_won - total_lost
    
    msg = f"""
📊 <b>RESUMEN DEL DÍA</b>

✅ Ganadas: {wins}
❌ Perdidas: {losses}
⏳ Pendientes: {pending}

💰 <b>Ganancia neta:</b> {'+' if net_profit >= 0 else ''}{net_profit:.2f} Bs
📈 <b>Bankroll:</b> {BANKROLL + net_profit:.0f} Bs
📊 <b>ROI:</b> {(net_profit/BANKROLL)*100:.1f}%
    """
    send_message(chat_id, msg)


def check_results():
    """Simula verificación de resultados (en producción conecta a API real)"""
    # En producción, aquí iría la lógica para verificar resultados
    # Por ahora, solo mostramos el estado
    print("\nEstado actual de las apuestas:")
    for bet in BETS:
        status_emoji = "WIN" if bet["status"] == "win" else "LOSS" if bet["status"] == "loss" else "PENDING"
        print(f"  [{status_emoji}] {bet['pick']} - {bet['status']}")


def main():
    """Función principal"""
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 50)
    print("SPORT EDGE BOT - Telegram Notifications")
    print("=" * 50)
    
    # Verificar conexión
    print("\nVerificando conexion con Telegram...")
    chat_id = get_chat_id()
    
    if chat_id:
        print(f"Conectado! Chat ID: {chat_id}")
        
        # Enviar bienvenida
        print("\nEnviando bienvenida...")
        send_welcome()
        
        print("\n" + "=" * 50)
        print("BOT ACTIVO - Esperando resultados...")
        print("=" * 50)
        print("\nComandos disponibles:")
        print("  /status - Ver estado de apuestas")
        print("  /summary - Ver resumen del dia")
        print("  /win [id] - Marcar apuesta como ganada")
        print("  /loss [id] - Marcar apuesta como perdida")
        
    else:
        print("No se pudo conectar. Asegurate de haber enviado")
        print("un mensaje a @Sport_edge_jair_bot primero.")
        print("\nPasos:")
        print("   1. Abre Telegram")
        print("   2. Busca @Sport_edge_jair_bot")
        print("   3. Envia /start")
        print("   4. Ejecuta este script de nuevo")


if __name__ == "__main__":
    main()
