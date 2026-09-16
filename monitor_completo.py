"""
SPORT EDGE BOT - Monitoreo Completo
Automáticamente:
1. Notifica en Telegram (Inicio, Mitad, Final)
2. Actualiza la base de datos local
3. Actualiza el dashboard
"""

import requests
import json
import time
import sys
import io
import csv
import os
from datetime import datetime

# Configurar encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "bets_database.json")
CSV_FILE = os.path.join(BASE_DIR, "tracking_apuestas.csv")
DASHBOARD_FILE = os.path.join(BASE_DIR, "tracking_dashboard.html")

# Telegram
TELEGRAM_TOKEN = "8563502125:AAGQ9IOEAfPgLlKkDoUeIkJ5_3llVKvWbCA"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
CHAT_ID = "8831402423"

# MLB API
MLB_API = "https://statsapi.mlb.com/api/v1"

# Tus apuestas
BETS = {
    1: {"pick": "Yamamoto O7.5 Ks", "event": "Dodgers vs Reds", "stake": 53, "potential_win": 100.70, "player": "Yamamoto", "team": "LAD", "line": 7.5, "status": "pending", "notified_start": False, "notified_middle": False},
    2: {"pick": "Misiorowski O8.5 Ks", "event": "Brewers vs Pirates", "stake": 28, "potential_win": 60.20, "player": "Misiorowski", "team": "MIL", "line": 8.5, "status": "pending", "notified_start": False, "notified_middle": False},
    3: {"pick": "Stephens +2.5", "event": "Stephens vs Tjen", "stake": 30, "potential_win": 58.50, "player": "Stephens", "sport": "tennis", "line": 2.5, "status": "pending", "notified_start": False, "notified_middle": False},
    4: {"pick": "Sanchez Ganara", "event": "Nationals vs Phillies", "stake": 285, "potential_win": 532, "player": "Sanchez", "team": "PHI", "line": 0, "status": "pending", "notified_start": False, "notified_middle": False},
    5: {"pick": "Sandoval O5.5 Ks", "event": "Rangers vs Red Sox", "stake": 30, "potential_win": 64.50, "player": "Sandoval", "team": "BOS", "line": 5.5, "status": "pending", "notified_start": False, "notified_middle": False},
}

# Estado
MATCH_STATUS = {}
RESULTS_LOG = []


# ============================================
# FUNCIONES DE BASE DE DATOS
# ============================================

def init_database():
    """Inicializa la base de datos JSON"""
    if not os.path.exists(DB_FILE):
        data = {
            "bets": {},
            "stats": {
                "total_bets": 0,
                "wins": 0,
                "losses": 0,
                "pending": 5,
                "total_staked": 0,
                "total_profit": 0,
                "bankroll": 3065
            },
            "last_updated": datetime.now().isoformat()
        }
        save_database(data)
    return load_database()


def load_database():
    """Carga la base de datos"""
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return init_database()


def save_database(data):
    """Guarda la base de datos"""
    data["last_updated"] = datetime.now().isoformat()
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[DB] Base de datos actualizada")


def update_bet_in_db(bet_id, status, profit=0, ks=0, score=""):
    """Actualiza una apuesta en la base de datos"""
    data = load_database()
    
    bet = BETS[bet_id]
    
    # Actualizar apuesta
    data["bets"][str(bet_id)] = {
        "id": bet_id,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "sport": "MLB" if bet.get("sport") != "tennis" else "Tenis",
        "market": "Player Props" if "Ks" in bet["pick"] else "Win",
        "event": bet["event"],
        "pick": bet["pick"],
        "house": "micasino" if bet_id != 4 else "1xBet",
        "odds": 1.90 if bet_id == 1 else 2.15 if bet_id == 2 else 1.95 if bet_id == 3 else 1.87 if bet_id == 4 else 2.15,
        "stake": bet["stake"],
        "potential_win": bet["potential_win"],
        "result": status,
        "profit": profit,
        "ks": ks,
        "score": score,
        "updated_at": datetime.now().isoformat()
    }
    
    # Actualizar estadísticas
    data["stats"]["total_bets"] = len(data["bets"])
    data["stats"]["wins"] = sum(1 for b in data["bets"].values() if b["result"] == "win")
    data["stats"]["losses"] = sum(1 for b in data["bets"].values() if b["result"] == "loss")
    data["stats"]["pending"] = sum(1 for b in data["bets"].values() if b["result"] == "pending")
    data["stats"]["total_staked"] = sum(b["stake"] for b in data["bets"].values())
    data["stats"]["total_profit"] = sum(b["profit"] for b in data["bets"].values())
    data["stats"]["bankroll"] = 3065 + data["stats"]["total_profit"]
    
    save_database(data)
    print(f"[DB] Bet #{bet_id} actualizada: {status}")
    
    # Actualizar CSV
    update_csv(bet_id, status, profit)
    
    # Actualizar dashboard HTML
    update_dashboard(data)
    
    return data["stats"]


def update_csv(bet_id, status, profit):
    """Actualiza el archivo CSV"""
    bet = BETS[bet_id]
    
    # Leer CSV existente
    rows = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
    
    # Buscar y actualizar fila
    updated = False
    for i, row in enumerate(rows):
        if len(row) > 0 and str(bet_id) in str(row):
            if status == "win":
                rows[i][6] = "Win"
                rows[i][7] = str(profit)
            elif status == "loss":
                rows[i][6] = "Loss"
                rows[i][7] = str(-bet["stake"])
            updated = True
            break
    
    # Si no existe, agregar
    if not updated:
        new_row = [
            datetime.now().strftime("%Y-%m-%d"),
            "MLB" if bet.get("sport") != "tennis" else "Tenis",
            "Player Props" if "Ks" in bet["pick"] else "Win",
            bet["event"],
            bet["pick"],
            "micasino" if bet_id != 4 else "1xBet",
            "Pending",
            "0",
            "0",
            "Pending"
        ]
        rows.append(new_row)
    
    # Guardar CSV
    with open(CSV_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    
    print(f"[CSV] Archivo actualizado")


def update_dashboard(data):
    """Actualiza el dashboard HTML con los resultados"""
    try:
        with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Actualizar stats en el dashboard
        stats = data["stats"]
        
        # Buscar y reemplazar stats
        import re
        
        # Actualizar wins/losses
        content = re.sub(r'let totalWins = \d+;', f'let totalWins = {stats["wins"]};', content)
        content = re.sub(r'let totalLosses = \d+;', f'let totalLosses = {stats["losses"]};', content)
        content = re.sub(r'let bankroll = \d+;', f'let bankroll = {stats["bankroll"]};', content)
        
        # Actualizar resultados de bets
        for bet_id, bet_data in data["bets"].items():
            if bet_data["result"] == "win":
                content = content.replace(
                    f"id: {bet_id},\n                result: 'pending'",
                    f"id: {bet_id},\n                result: 'win'"
                )
            elif bet_data["result"] == "loss":
                content = content.replace(
                    f"id: {bet_id},\n                result: 'pending'",
                    f"id: {bet_id},\n                result: 'loss'"
                )
        
        with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[DASHBOARD] Dashboard actualizado")
        
    except Exception as e:
        print(f"[DASHBOARD] Error: {e}")


# ============================================
# FUNCIONES DE TELEGRAM
# ============================================

def send_telegram(message):
    """Envia mensaje a Telegram"""
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except:
        return None


# ============================================
# FUNCIONES DE MLB API
# ============================================

def get_mlb_games():
    """Obtiene juegos de MLB"""
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"{MLB_API}/schedule?sportId=1&date={today}&hydrate=lineups,probablePitcher"
    
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        games = []
        
        for date in data.get("dates", []):
            for g in date.get("games", []):
                games.append({
                    "id": g["gamePk"],
                    "status": g["status"]["detailedState"],
                    "status_code": g["status"]["statusCode"],
                    "away": g["teams"]["away"]["team"]["name"],
                    "home": g["teams"]["home"]["team"]["name"],
                    "away_score": g["teams"]["away"].get("score", 0),
                    "home_score": g["teams"]["home"].get("score", 0),
                    "inning": g.get("linescore", {}).get("currentInning", 0),
                    "inning_state": g.get("linescore", {}).get("inningState", ""),
                    "away_pitcher": g["teams"]["away"].get("probablePitcher", {}).get("fullName", ""),
                    "home_pitcher": g["teams"]["home"].get("probablePitcher", {}).get("fullName", ""),
                })
        
        return games
    except Exception as e:
        print(f"Error MLB API: {e}")
        return []


def get_pitcher_ks(player_name, game_id):
    """Obtiene strikeouts del pitcher"""
    url = f"{MLB_API}/game/{game_id}/feed/live"
    
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        players = data.get("liveData", {}).get("boxscore", {}).get("players", {})
        
        for side in ["away", "home"]:
            for pid, pdata in players.get(side, {}).get("players", {}).items():
                if player_name.lower() in pdata.get("person", {}).get("fullName", "").lower():
                    pitching = pdata.get("stats", {}).get("pitching", {})
                    return pitching.get("strikeOuts", 0)
        
        return 0
    except:
        return 0


# ============================================
# MONITOREO PRINCIPAL
# ============================================

def check_games():
    """Verifica todos los juegos y actualiza todo"""
    global BETS, MATCH_STATUS, RESULTS_LOG
    
    games = get_mlb_games()
    
    for bet_id, bet in BETS.items():
        if bet["status"] != "pending":
            continue
        if bet.get("sport") == "tennis":
            continue
        
        # Buscar juego del pitcher
        for game in games:
            player = bet["player"]
            is_home = player.lower() in game["home_pitcher"].lower()
            is_away = player.lower() in game["away_pitcher"].lower()
            
            if not is_home and not is_away:
                continue
            
            game_id = game["id"]
            status = game["status"]
            
            # INICIO DEL PARTIDO
            if status == "In Progress" and not bet["notified_start"]:
                ks = get_pitcher_ks(player, game_id)
                msg = f"""
⚾ <b>PARTIDO INICIADO</b>

{game['away']} @ {game['home']}
📊 {bet['event']}
🎯 {bet['pick']}
📈 {player}: {ks} Ks

⏳ Mitad: ~19:15
                """
                send_telegram(msg)
                BETS[bet_id]["notified_start"] = True
                print(f"[INICIO] {bet['event']}")
            
            # MITAD DEL PARTIDO (5ta entrada)
            elif status == "In Progress" and game["inning"] == 5 and not bet["notified_middle"]:
                ks = get_pitcher_ks(player, game_id)
                line = bet["line"]
                
                if "O" in bet["pick"]:
                    status_text = f"{'WINNING' if ks > line else 'NEED MORE'} {ks}/{line} Ks"
                else:
                    status_text = f"{'WINNING' if ks < line else 'NEED LESS'} {ks}/{line} Ks"
                
                msg = f"""
📊 <b>MITAD DEL PARTIDO</b>

{game['away']} {game['away_score']} - {game['home']} {game['home_score']}
{player}: {status_text}
🎯 {bet['pick']}

⏳ Final: ~20:00
                """
                send_telegram(msg)
                BETS[bet_id]["notified_middle"] = True
                print(f"[MITAD] {bet['event']}")
            
            # FINAL DEL PARTIDO
            elif status == "Final":
                ks = get_pitcher_ks(player, game_id)
                line = bet["line"]
                score = f"{game['away']} {game['away_score']} - {game['home']} {game['home_score']}"
                
                # Determinar si gano
                if "O" in bet["pick"]:
                    won = ks > line
                elif "U" in bet["pick"]:
                    won = ks < line
                else:
                    won = None
                
                if won is not None:
                    if won:
                        profit = bet["potential_win"] - bet["stake"]
                        msg = f"""
🏆 <b>¡{player.upper()} GANÓ!</b>

{score}
✅ {bet['pick']}
📊 {ks} Ks vs Línea {line}
💰 <b>Ganancia: +{profit:.2f} Bs</b>

✅ Actualizado en dashboard
                        """
                        print(f"[WIN] {bet['event']} +{profit:.2f} Bs")
                    else:
                        profit = -bet["stake"]
                        msg = f"""
❌ <b>{player.upper()} PERDIÓ</b>

{score}
❌ {bet['pick']}
📊 {ks} Ks vs Línea {line}
💸 <b>Pérdida: -{bet['stake']} Bs</b>

✅ Actualizado en dashboard
                        """
                        print(f"[LOSS] {bet['event']} -{bet['stake']} Bs")
                    
                    # Enviar notificación
                    send_telegram(msg)
                    
                    # Actualizar base de datos
                    result_status = "win" if won else "loss"
                    update_bet_in_db(bet_id, result_status, profit, ks, score)
                    
                    # Marcar como procesada
                    BETS[bet_id]["status"] = result_status
                    
                    # Log
                    RESULTS_LOG.append({
                        "bet_id": bet_id,
                        "pick": bet["pick"],
                        "result": result_status,
                        "profit": profit,
                        "ks": ks,
                        "score": score,
                        "time": datetime.now().isoformat()
                    })
            
            break


def main():
    """Loop principal"""
    print("=" * 60)
    print("SPORT EDGE BOT - Monitoreo Completo con DB")
    print("=" * 60)
    print("Automáticamente:")
    print("  1. Notifica en Telegram")
    print("  2. Actualiza base de datos JSON")
    print("  3. Actualiza CSV")
    print("  4. Actualiza dashboard HTML")
    print("=" * 60)
    
    # Inicializar base de datos
    init_database()
    
    # Enviar mensaje de inicio
    send_telegram("""🔄 <b>Monitoreo COMPLETO activado</b>

✅ Notificaciones en tiempo real
✅ Base de datos automática
✅ Dashboard actualizado

3 notificaciones por partido:
• Inicio
• Mitad (5ta entrada)
• Final + resultado""")
    
    print("\n[INIT] Base de datos inicializada")
    print("[INIT] Monitoreo activo")
    
    while True:
        try:
            now = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{now}] Verificando...")
            
            check_games()
            
            # Verificar pendientes
            data = load_database()
            pending = data["stats"]["pending"]
            wins = data["stats"]["wins"]
            losses = data["stats"]["losses"]
            
            print(f"   Estado: {wins}W - {losses}L - {pending}P")
            print(f"   Bankroll: {data['stats']['bankroll']} Bs")
            
            if pending == 0:
                # Resumen final
                profit = data["stats"]["total_profit"]
                msg = f"""
✅ <b>TODOS LOS PARTIDOS TERMINARON</b>

📊 <b>RESUMEN FINAL</b>
• Ganadas: {wins}
• Perdidas: {losses}
• Bankroll: {data['stats']['bankroll']} Bs
• Ganancia: {'+' if profit >= 0 else ''}{profit:.2f} Bs

📁 Datos guardados en:
• bets_database.json
• tracking_apuestas.csv
• tracking_dashboard.html
                """
                send_telegram(msg)
                print("\n" + "=" * 60)
                print("TODOS LOS PARTIDOS TERMINARON")
                print("=" * 60)
                break
            
            time.sleep(120)
            
        except KeyboardInterrupt:
            print("\nDetenido por usuario")
            send_telegram("⏹️ Monitoreo detenido")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(120)


if __name__ == "__main__":
    main()
