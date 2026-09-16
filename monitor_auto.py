"""
SPORT EDGE BOT - Monitoreo Automático
Verifica resultados cada minuto y envía notificaciones cuando:
- Un partido COMIENZA
- Un partido TERMINA
- Ganas o pierdes una apuesta
"""

import requests
import json
import time
import sys
import io
from datetime import datetime, timedelta

# Configurar encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Telegram
TELEGRAM_TOKEN = "8563502125:AAGQ9IOEAfPgLlKkDoUeIkJ5_3llVKvWbCA"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
CHAT_ID = "8831402423"

# MLB API (gratuita)
MLB_API = "https://statsapi.mlb.com/api/v1"

# Tus apuestas
BETS = {
    1: {"pick": "Yamamoto O7.5 Ks", "event": "Dodgers vs Reds", "stake": 53, "potential_win": 100.70, "player": "Yamamoto", "team": "LAD", "line": 7.5, "status": "pending"},
    2: {"pick": "Misiorowski O8.5 Ks", "event": "Brewers vs Pirates", "stake": 28, "potential_win": 60.20, "player": "Misiorowski", "team": "MIL", "line": 8.5, "status": "pending"},
    3: {"pick": "Stephens +2.5", "event": "Stephens vs Tjen", "stake": 30, "potential_win": 58.50, "player": "Stephens", "sport": "tennis", "line": 2.5, "status": "pending"},
    4: {"pick": "Sanchez Ganara", "event": "Nationals vs Phillies", "stake": 285, "potential_win": 532, "player": "Sanchez", "team": "PHI", "line": 0, "status": "pending"},
    5: {"pick": "Sandoval O5.5 Ks", "event": "Rangers vs Red Sox", "stake": 30, "potential_win": 64.50, "player": "Sandoval", "team": "BOS", "line": 5.5, "status": "pending"},
}

# Estado de partidos (para detectar cambios)
MATCH_STATUS = {}


def send_telegram(message):
    """Envia mensaje a Telegram"""
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error Telegram: {e}")
        return None


def get_mlb_scores():
    """Obtiene resultados de MLB desde la API oficial"""
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"{MLB_API}/schedule?sportId=1&date={today}&hydrate=lineups,probablePitcher"
    
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        games = []
        
        for game in data.get("dates", []):
            for g in game.get("games", []):
                game_info = {
                    "id": g["gamePk"],
                    "status": g["status"]["detailedState"],
                    "status_code": g["status"]["statusCode"],
                    "away_team": g["teams"]["away"]["team"]["name"],
                    "home_team": g["teams"]["home"]["team"]["name"],
                    "away_score": g["teams"]["away"].get("score", 0),
                    "home_score": g["teams"]["home"].get("score", 0),
                    "inning": g.get("linescore", {}).get("currentInning", 0),
                    "inning_state": g.get("linescore", {}).get("inningState", ""),
                    "away_pitcher": g["teams"]["away"].get("probablePitcher", {}).get("fullName", "TBD"),
                    "home_pitcher": g["teams"]["home"].get("probablePitcher", {}).get("fullName", "TBD"),
                }
                games.append(game_info)
        
        return games
    except Exception as e:
        print(f"Error MLB API: {e}")
        return []


def get_pitcher_stats(player_name, game_id):
    """Obtiene stats del pitcher en el juego actual"""
    url = f"{MLB_API}/game/{game_id}/feed/live"
    
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        
        players = data.get("liveData", {}).get("boxscore", {}).get("players", {})
        
        for team_side in ["away", "home"]:
            team_players = players.get(team_side, {}).get("players", {})
            for player_id, player_data in team_players.items():
                if player_name.lower() in player_data.get("person", {}).get("fullName", "").lower():
                    stats = player_data.get("stats", {})
                    pitching = stats.get("pitching", {})
                    return {
                        "strikeouts": pitching.get("strikeOuts", 0),
                        "hits": pitching.get("hits", 0),
                        "walks": pitching.get("baseOnBalls", 0),
                        "innings": pitching.get("inningsPitched", "0"),
                        "earned_runs": pitching.get("earnedRuns", 0),
                    }
        
        return None
    except Exception as e:
        print(f"Error obteniendo stats: {e}")
        return None


def check_mlb_bet(bet, game):
    """Verifica si una apuesta MLB gano o perdio"""
    global MATCH_STATUS
    
    game_id = game["id"]
    player_name = bet["player"]
    
    # Verificar si el pitcher esta en este juego
    if (player_name.lower() not in game["away_pitcher"].lower() and 
        player_name.lower() not in game["home_pitcher"].lower()):
        return None
    
    # Obtener stats del pitcher
    stats = get_pitcher_stats(player_name, game_id)
    
    if not stats:
        return None
    
    ks = stats["strikeouts"]
    line = bet["line"]
    pick = bet["pick"]
    
    # Verificar si el juego termino
    game_ended = game["status"] == "Final"
    game_started = game["status"] == "In Progress" or game["status"] == "Final"
    
    # Detectar cambio de estado
    prev_status = MATCH_STATUS.get(game_id, "Preview")
    MATCH_STATUS[game_id] = game["status"]
    
    result = {
        "game_id": game_id,
        "player": player_name,
        "ks": ks,
        "line": line,
        "game_started": game_started,
        "game_ended": game_ended,
        "score": f"{game['away_team']} {game['away_score']} - {game['home_team']} {game['home_score']}",
        "innings": f"#{game['inning']} {game['inning_state']}",
        "prev_status": prev_status,
    }
    
    # Si el juego termino, determinar resultado
    if game_ended:
        if "O" in pick:  # Over
            result["won"] = ks > line
        elif "U" in pick:  # Under
            result["won"] = ks < line
        else:
            result["won"] = None
    
    return result


def check_all_bets():
    """Verifica todas las apuestas"""
    global BETS
    
    # Obtener juegos de MLB
    mlb_games = get_mlb_scores()
    
    results = []
    
    for bet_id, bet in BETS.items():
        if bet["status"] != "pending":
            continue
        
        if bet.get("sport") == "tennis":
            # Tenis - por ahora solo notificar
            continue
        
        # Buscar juego de MLB
        for game in mlb_games:
            result = check_mlb_bet(bet, game)
            if result:
                results.append({"bet_id": bet_id, "bet": bet, "result": result})
                break
    
    return results


def notify_start(bet, result):
    """Notifica cuando un partido empieza"""
    msg = f"""
⚾ <b>PARTIDO INICIADO</b>

{result['score']}
📊 {bet['event']}
🎯 {bet['pick']}
⏰ {result['innings']}

⏳ Esperando resultado...
    """
    send_telegram(msg)
    print(f"[INICIO] {bet['event']}")


def notify_progress(bet, result):
    """Notifica progreso del partido"""
    msg = f"""
📊 <b>ACTUALIZACION</b>

{result['score']}
{bet['player']}: {result['ks']} Ks
🎯 Necesita: {'>' if 'O' in bet['pick'] else '<'}{bet['line']} Ks
⏰ {result['innings']}
    """
    send_telegram(msg)
    print(f"[PROGRESO] {bet['event']} - {result['ks']} Ks")


def notify_final(bet, result, won):
    """Notifica resultado final"""
    if won:
        profit = bet["potential_win"] - bet["stake"]
        msg = f"""
🏆 <b>¡{bet['player'].upper()} GANÓ!</b>

{result['score']}
✅ {bet['pick']}
📊 {result['ks']} Ks vs Línea {bet['line']}
💰 <b>Ganancia: +{profit:.2f} Bs</b>

📈 ¡Excelente! 💪
        """
        print(f"[WIN] {bet['event']} +{profit:.2f} Bs")
    else:
        msg = f"""
❌ <b>{bet['player'].upper()} PERDIÓ</b>

{result['score']}
❌ {bet['pick']}
📊 {result['ks']} Ks vs Línea {bet['line']}
💸 <b>Pérdida: -{bet['stake']} Bs</b>

💪 Siguiente apuesta! 🎯
        """
        print(f"[LOSS] {bet['event']} -{bet['stake']} Bs")
    
    send_telegram(msg)


def main():
    """Loop principal de monitoreo"""
    print("=" * 60)
    print("SPORT EDGE BOT - Monitoreo Automatico")
    print("=" * 60)
    print("Verificando partidos cada 60 segundos...")
    print("Presiona Ctrl+C para detener")
    print("=" * 60)
    
    # Enviar mensaje de inicio
    send_telegram("🔄 Monitoreo automatico ACTIVADO\nVerificando resultados cada 60 segundos...")
    
    check_count = 0
    
    while True:
        try:
            check_count += 1
            now = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{now}] Verificacion #{check_count}...")
            
            # Verificar apuestas
            results = check_all_bets()
            
            for item in results:
                bet_id = item["bet_id"]
                bet = item["bet"]
                result = item["result"]
                
                # Detectar inicio del partido
                if result["game_started"] and result["prev_status"] == "Preview":
                    notify_start(bet, result)
                
                # Detectar fin del partido
                if result["game_ended"] and bet["status"] == "pending":
                    won = result.get("won")
                    if won is not None:
                        notify_final(bet, result, won)
                        BETS[bet_id]["status"] = "win" if won else "loss"
                
                # Reportar progreso cada 3 entradas
                elif result["game_started"] and not result["game_ended"]:
                    ks = result["ks"]
                    line = result["line"]
                    if ks > 0 and ks % 3 == 0:
                        notify_progress(bet, result)
            
            # Verificar si todas las apuestas terminaron
            pending = sum(1 for b in BETS.values() if b["status"] == "pending")
            if pending == 0:
                send_telegram("✅ TODOS LOS PARTIDOS TERMINARON\nResumen del dia completo!")
                print("\n Todos los partidos terminaron!")
                break
            
            print(f"   Pendientes: {pending}/5")
            
            # Esperar 60 segundos
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n\nMonitoreo detenido por el usuario")
            send_telegram("⏹️ Monitoreo detenido manualmente")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
