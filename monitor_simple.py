"""
SPORT EDGE BOT - Monitoreo Simplificado
Solo 3 notificaciones por partido:
1. INICIO del partido
2. MITAD del partido (5ta entrada)
3. FINAL del partido + resultado
"""

import requests
import json
import time
import sys
import io
from datetime import datetime

# Configurar encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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
GAME_NOTIFIED = {}


def send_telegram(message):
    """Envia mensaje a Telegram"""
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except:
        return None


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
        print(f"Error: {e}")
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


def notify(message):
    """Envia notificacion"""
    send_telegram(message)
    print(f"[NOTIFY] Enviado")


def check_games():
    """Verifica todos los juegos"""
    global GAME_NOTIFIED, BETS
    
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
            key = f"{bet_id}_{game_id}"
            
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
                notify(msg)
                BETS[bet_id]["notified_start"] = True
                print(f"[INICIO] {bet['event']}")
            
            # MITAD DEL PARTIDO (5ta entrada)
            elif status == "In Progress" and game["inning"] == 5 and not bet["notified_middle"]:
                ks = get_pitcher_ks(player, game_id)
                line = bet["line"]
                
                if "O" in bet["pick"]:
                    status_text = f"{'✅' if ks > line else '⏳'} {ks}/{line} Ks"
                else:
                    status_text = f"{'✅' if ks < line else '⏳'} {ks}/{line} Ks"
                
                msg = f"""
📊 <b>MITAD DEL PARTIDO</b>

{game['away']} {game['away_score']} - {game['home']} {game['home_score']}
{player}: {status_text}
🎯 {bet['pick']}

⏳ Final: ~20:00
                """
                notify(msg)
                BETS[bet_id]["notified_middle"] = True
                print(f"[MITAD] {bet['event']}")
            
            # FINAL DEL PARTIDO
            elif status == "Final":
                ks = get_pitcher_ks(player, game_id)
                line = bet["line"]
                
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

{game['away']} {game['away_score']} - {game['home']} {game['home_score']}
✅ {bet['pick']}
📊 {ks} Ks vs Línea {line}
💰 <b>Ganancia: +{profit:.2f} Bs</b>

¡Excelente! 💪
                        """
                        print(f"[WIN] {bet['event']} +{profit:.2f} Bs")
                    else:
                        msg = f"""
❌ <b>{player.upper()} PERDIÓ</b>

{game['away']} {game['away_score']} - {game['home']} {game['home_score']}
❌ {bet['pick']}
📊 {ks} Ks vs Línea {line}
💸 <b>Pérdida: -{bet['stake']} Bs</b>

Siguiente apuesta! 🎯
                        """
                        print(f"[LOSS] {bet['event']} -{bet['stake']} Bs")
                    
                    notify(msg)
                    BETS[bet_id]["status"] = "win" if won else "loss"
            
            break


def main():
    """Loop principal"""
    print("=" * 60)
    print("SPORT EDGE BOT - Monitoreo Simplificado")
    print("=" * 60)
    print("3 notificaciones por partido:")
    print("  1. INICIO")
    print("  2. MITAD (5ta entrada)")
    print("  3. FINAL + resultado")
    print("=" * 60)
    
    send_telegram("🔄 Monitoreo ACTIVO\n3 notificaciones por partido: Inicio, Mitad, Final")
    
    while True:
        try:
            now = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{now}] Verificando...")
            
            check_games()
            
            pending = sum(1 for b in BETS.values() if b["status"] == "pending")
            print(f"   Pendientes: {pending}/5")
            
            if pending == 0:
                send_telegram("✅ TODOS LOS PARTIDOS TERMINARON")
                print("\nTodos los partidos terminaron!")
                break
            
            time.sleep(120)  # Verificar cada 2 minutos
            
        except KeyboardInterrupt:
            print("\nDetenido por usuario")
            send_telegram("⏹️ Monitoreo detenido")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(120)


if __name__ == "__main__":
    main()
