"""
SPORT EDGE BOT - Con Memoria Completa
Recuerda TODO el contexto de la conversación
"""

import requests
import json
import time
import sys
import io
import os
import re
import random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

# Configurar encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ============================================
# PERSISTENCIA - Guardar estado en archivo
# ============================================
STATE_FILE = os.path.join(os.path.dirname(__file__), 'monitor_state.json')

def save_state():
    """Guarda estado del monitor en archivo"""
    try:
        state = {
            'games_notified': MONITOR_STATUS['games_notified'],
            'last_check': MONITOR_STATUS['last_check'],
            'bankroll': MEMORY['bankroll'],
            'apuestas': {str(k): {kk: vv for kk, vv in v.items()} for k, v in MEMORY['apuestas_hoy']['picks'].items()}
        }
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        print(f"[STATE] Guardado: {STATE_FILE}")
    except Exception as e:
        print(f"[STATE] Error guardando: {e}")

def load_state():
    """Carga estado del monitor desde archivo"""
    global MONITOR_STATUS
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
            MONITOR_STATUS['games_notified'] = state.get('games_notified', {})
            MONITOR_STATUS['last_check'] = state.get('last_check', None)
            if 'bankroll' in state:
                MEMORY['bankroll'] = state['bankroll']
            if 'apuestas' in state:
                for k, v in state['apuestas'].items():
                    MEMORY['apuestas_hoy']['picks'][int(k)] = v
            print(f"[STATE] Cargado: {len(MONITOR_STATUS['games_notified'])} notificaciones previas")
        else:
            print("[STATE] No existe archivo, empezando de cero")
    except Exception as e:
        print(f"[STATE] Error cargando: {e}")

# Estado del monitor (se persiste en archivo)
MONITOR_STATUS = {
    'running': False,
    'last_check': None,
    'games_notified': {}
}

# Cargar estado al iniciar
load_state()

# Telegram
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '8563502125:AAFyhneNu2iBjQbUmE_bNGtFdYi8nNHzfgo')
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ============================================
# MEMORIA COMPLETA - TODO EL CONTEXTO
# ============================================

MEMORY = {
    "usuario": {
        "nombre": "Jair",
        "username": "JairRuiz11",
        "pais": "Venezuela",
        "timezone": "UTC-4",
        "banco": "Nu (Colombia)",
        "plataformas": ["1xBet", "micasino"],
        "exchange_rate": 950  # Bs por USD
    },
    
    "proyecto": {
        "nombre": "Sports Edge",
        "ubicacion": "C:/Users/jruiz/sports_analyzer",
        "stack": ["Python", "Flask", "Poisson Model", "Telegram Bot"],
        "api_football": "b9b358f4ca134a29a326a77926eeee17",
        "api_odds": "af560452f738537eeb2be3faec31a73f",
        "api_odds_agotada": True
    },
    
    "bankroll": {
        "inicial": 3065,
        "actual": 3065,
        "1xbet": 2365,
        "micasino": 700,
        "unidad": 30.65,  # 1%
        "max_por_dia": 153,  # 5%
        "max_por_pick": 61  # 2%
    },
    
    "estrategia": {
        "disciplinas": ["MLB Props", "MLB Totales", "Tenis WTA"],
        "mercados_favoritos": ["Player Props", "Handicap", "Totales"],
        "mercados_evitar": ["1X2", "Moneyline"],
        "modelos": {
            "poisson_basico": "48-53% precision",
            "poisson_mejorado": "52-57% precision",
            "mercado": "55-58% precision",
            "maximo_realista": "60% en Tenis"
        },
        "principios": [
            "Solo apostar EV positivo",
            "Kelly Criterion conservador (25%)",
            "Maximo 3% por pick",
            "Maximo 5% por dia",
            "Especializarse en 1-2 mercados",
            "Line shopping entre casas"
        ]
    },
    
    "apuestas_hoy": {
        "fecha": "2026-09-15",
        "total_apostado": 426,
        "picks": {
            1: {
                "pick": "Yamamoto O7.5 Ks",
                "event": "Dodgers vs Reds",
                "casa": "micasino",
                "cuota": 1.90,
                "stake": 53,
                "ganar": 100.70,
                "ev": 21.6,
                "razon": "Yamamoto ERA 2.62, K/9 8.95, ultimos 5: 10,8,8,9,9. Reds K% 25.5%",
                "estado": "pendiente",
                "boleto": "5420883747"
            },
            2: {
                "pick": "Misiorowski O8.5 Ks",
                "event": "Brewers vs Pirates",
                "casa": "micasino",
                "cuota": 2.15,
                "stake": 28,
                "ganar": 60.20,
                "ev": 3.2,
                "razon": "Misiorowski ERA 1.95, K/9 13.17. Pirates K% 22-24%",
                "estado": "pendiente",
                "boleto": "5420980491"
            },
            3: {
                "pick": "Stephens +2.5",
                "event": "Stephens vs Tjen",
                "casa": "micasino",
                "cuota": 1.95,
                "stake": 30,
                "ganar": 58.50,
                "ev": 7.3,
                "razon": "WTA Guadalajara, hard court. Stephens experiencia superior",
                "estado": "pendiente",
                "boleto": "5421161569"
            },
            4: {
                "pick": "Sanchez Ganara",
                "event": "Nationals vs Phillies",
                "casa": "1xBet",
                "cuota": 1.87,
                "stake": 285,
                "ganar": 532,
                "ev": 19.7,
                "razon": "Sanchez ERA 2.79 vs Kent ERA 6.59. Phillies favoritos",
                "estado": "pendiente",
                "boleto": "87318108523"
            },
            5: {
                "pick": "Sandoval O5.5 Ks",
                "event": "Rangers vs Red Sox",
                "casa": "micasino",
                "cuota": 2.15,
                "stake": 30,
                "ganar": 64.50,
                "ev": 16.1,
                "razon": "Sandoval K/9 8.5, linea baja 5.5. Rangers no elite en contacto",
                "estado": "pendiente",
                "boleto": "5421384041"
            }
        }
    },
    
    "conversacion": {
        "resumen": """
RESUMEN DE LA CONVERSACION - 15 Septiembre 2026:

1. INICIO: Jair queria analisis de apuestas deportivas con modelo Poisson
2. PROYECTO: Se creo Sports Edge en C:/Users/jruiz/sports_analyzer
3. MODELO: Poisson mejorado con form scraper, head2head, home advantage
4. API: the-odds-api.com agotada (500/500 requests)
5. ESTRATEGIA: Disciplinas: MLB Props, MLB Totales, Tenis WTA
6. APUESTAS: 5 picks seleccionados con EV positivo
7. PLATAFORMAS: micasino (4 picks) + 1xBet (1 pick)
8. TELEGRAM: Bot creado @Sport_edge_jair_bot
9. RENDER: Bot desplegado 24/7 gratis
10. MEMORIA: Bot ahora recuerda todo el contexto
        """,
        "momentos_clave": [
            "Jair explico que Poisson basico = 48-53%, nunca claim 70-90%",
            "Jair tiene tarjeta Nu colombiana pero esta en Venezuela",
            "1xBet minimo $0.30 USD = 285 Bs (9.3% del bankroll)",
            "Estrategia profesional: EV+, Kelly, CLV, line shopping",
            "Telegram bot configurado con notificaciones automaticas"
        ],
        "Decisiones_tomadas": [
            "Usar Poisson mejorado con form + H2H + home advantage",
            "Disciplinas: MLB Props (40%), Tenis (35%), MLB Totales (25%)",
            "4 picks en micasino + 1 en 1xBet",
            "Monitor automatico cada 2 minutos",
            "Bot 24/7 en Render (gratis)"
        ]
    },
    
    "conocimiento": {
        "poisson": """
MODELO POISSON MEJORADO:
- Lambda base = (Goles local prom / 90) * (Goles visitante prom / 90) * 90
- Factor de forma: Ultimos 5 partidos del equipo
- Head-to-Head: Historial entre ambos equipos
- Home advantage dinamico: % victorias local en temporada
- P(X=k) = (lambda^k * e^-lambda) / k!
        """,
        "kelly": """
KRITERIO KELLY:
- f* = (bp - q) / b
- b = cuota - 1
- p = probabilidad estimada
- q = 1 - p
- Conservador: 25% de f*
- Maximo 3% del bankroll por pick
        """,
        "ev": """
EXPECTED VALUE:
- EV = (p * ganancia) - (q * stake)
- EV positivo = +valor
- EV negativo = -valor
- Si EV > 0, la apuesta tiene valor a largo plazo
        """
    },
    
    "metricas": {
        "hits_hoy": 0,
        "misses_hoy": 0,
        "roi_dia": 0,
        "roi_total": 0,
        "tracking_file": "tracking_apuestas.csv",
        "dashboard_file": "tracking_dashboard.html"
    }
}


# Base de datos de estado
database = {
    "stats": {
        "wins": 0,
        "losses": 0,
        "pending": 5,
        "bankroll": 3065,
        "total_profit": 0,
        "total_staked": 426
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
# HANDLERS CON MEMORIA COMPLETA
# ============================================

def handle_start(chat_id):
    """Bienvenida"""
    msg = """
🏆 <b>SPORT EDGE BOT</b> 🏆

¡Hola Jair! Soy tu asistente con MEMORIA COMPLETA.

<b>Recuerdo TODO sobre ti:</b>
• Tu bankroll y apuestas
• Las razones de cada pick
• Tu estrategia y principios
• Todo lo que hablamos hoy

<b>Comandos:</b>
📊 /status - Ver apuestas
💰 /bankroll - Ver dinero
📈 /stats - Ver estadísticas
🎯 /picks - Ver picks del día
🧠 /memoria - Ver lo que recuerdo
❓ /ayuda - Ver ayuda

<b>Puedes preguntarme:</b>
• "¿Por qué aposté a Yamamoto?"
• "¿Cuál es mi estrategia?"
• "¿Qué modelo uso?"
• "Cuéntame sobre Poisson"
    """
    send_message(chat_id, msg)

def handle_memoria(chat_id):
    """Muestra toda la memoria"""
    msg = f"""
🧠 <b>MI MEMORIA COMPLETA</b>

<b>👤 Sobre ti:</b>
• Nombre: {MEMORY['usuario']['nombre']}
• País: {MEMORY['usuario']['pais']}
• Plataformas: {', '.join(MEMORY['usuario']['plataformas'])}

<b>💰 Tu bankroll:</b>
• Inicial: {MEMORY['bankroll']['inicial']} Bs
• 1xBet: {MEMORY['bankroll']['1xbet']} Bs
• micasino: {MEMORY['bankroll']['micasino']} Bs
• Unidad: {MEMORY['bankroll']['unidad']} Bs

<b>📊 Tus apuestas de hoy:</b>
"""
    
    for bet_id, bet in MEMORY['apuestas_hoy']['picks'].items():
        msg += f"{bet_id}. {bet['pick']} ({bet['casa']}) - {bet['estado']}\n"
    
    msg += f"""
<b>🧠 Lo que recuerdo:</b>
• Modelo: Poisson mejorado
• Precisión: 52-57%
• Estrategia: EV+ solamente
• Max 5% bankroll/día

<b>📝 Resumen de nuestra conversación:</b>
{MEMORY['conversacion']['resumen'][:500]}...
    """
    send_message(chat_id, msg)

def handle_preguntar(chat_id, pregunta):
    """Responde preguntas con contexto"""
    pregunta = pregunta.lower()
    
    # YAMAMOTO
    if "yamamoto" in pregunta or "pick 1" in pregunta or "primera apuesta" in pregunta:
        bet = MEMORY['apuestas_hoy']['picks'][1]
        msg = f"""
⚾ <b>YAMAMOTO O7.5 KS</b>

<b>¿Por qué este pick?</b>
{bet['razon']}

<b>Datos:</b>
• ERA: 2.62
• K/9: 8.95
• Últimos 5: 10, 8, 8, 9, 9 (avg 8.8)
• Rival: Reds (K% 25.5%)

<b>Apuesta:</b>
• Casa: {bet['casa']}
• Cuota: {bet['cuota']}
• Stake: {bet['stake']} Bs
• EV: {bet['ev']}%

<b>Razonamiento:</b>
Yamamoto tiene K/9 de 8.5+ y enfrenta a un equipo con K% alto. La línea de 7.5 es conservadora dado su promedio reciente de 8.8 Ks.
        """
        send_message(chat_id, msg)
    
    # MISIOROWSKI
    elif "misiorowski" in pregunta or "pick 2" in pregunta or "segunda apuesta" in pregunta or "brewers" in pregunta:
        bet = MEMORY['apuestas_hoy']['picks'][2]
        msg = f"""
⚾ <b>MISIOROWSKI O8.5 KS</b>

<b>¿Por qué este pick?</b>
{bet['razon']}

<b>Datos:</b>
• ERA: 1.95 (élite)
• K/9: 13.17 (élite)
• Pirates K%: 22-24%

<b>Apuesta:</b>
• Casa: {bet['casa']}
• Cuota: {bet['cuota']}
• Stake: {bet['stake']} Bs
• EV: {bet['ev']}%

<b>Razonamiento:</b>
Misiorowski es un pitcher élite con K/9 de 13+. Aunque la línea de 8.5 es alta, su talento puro justifica el over.
        """
        send_message(chat_id, msg)
    
    # STEPHENS
    elif "stephens" in pregunta or "pick 3" in pregunta or "tercera apuesta" in pregunta or "tenis" in pregunta:
        bet = MEMORY['apuestas_hoy']['picks'][3]
        msg = f"""
🎾 <b>STEPHENS +2.5</b>

<b>¿Por qué este pick?</b>
{bet['razon']}

<b>Datos:</b>
• Ranking: ~169 WTA
• Rival: Tjen (~51 WTA)
• Torneo: WTA Guadalajara
• Superficie: Hard court

<b>Apuesta:</b>
• Casa: {bet['casa']}
• Cuota: {bet['cuota']}
• Stake: {bet['stake']} Bs
• EV: {bet['ev']}%

<b>Razonamiento:</b>
Stephens es underdog pero tiene experiencia en Grand Slams. El handicap de +2.5 juegos le da margen para perder un set y aún ganar la apuesta.
        """
        send_message(chat_id, msg)
    
    # SANCHEZ
    elif "sanchez" in pregunta or "pick 4" in pregunta or "cuarta apuesta" in pregunta or "phillies" in pregunta:
        bet = MEMORY['apuestas_hoy']['picks'][4]
        msg = f"""
⚾ <b>SÁNCHEZ GANARÁ</b>

<b>¿Por qué este pick?</b>
{bet['razon']}

<b>Datos:</b>
• ERA: 2.79
• K/9: 10.1
• Rival: Nationals (Kent ERA 6.59)

<b>Apuesta:</b>
• Casa: {bet['casa']}
• Cuota: {bet['cuota']}
• Stake: {bet['stake']} Bs
• EV: {bet['ev']}%

<b>Razonamiento:</b>
Phillies son favoritos claros con Sánchez (ERA 2.79) vs Kent (ERA 6.59). El win tiene EV del 19.7%.
        """
        send_message(chat_id, msg)
    
    # SANDOVAL
    elif "sandoval" in pregunta or "pick 5" in pregunta or "quinta apuesta" in pregunta or "red sox" in pregunta:
        bet = MEMORY['apuestas_hoy']['picks'][5]
        msg = f"""
⚾ <b>SANDOVAL O5.5 KS</b>

<b>¿Por qué este pick?</b>
{bet['razon']}

<b>Datos:</b>
• K/9: 8.5
• ERA: 4.58
• Línea: 5.5 Ks (baja)

<b>Apuesta:</b>
• Casa: {bet['casa']}
• Cuota: {bet['cuota']}
• Stake: {bet['stake']} Bs
• EV: {bet['ev']}%

<b>Razonamiento:</b>
Sandoval tiene K/9 de 8.5, pero la línea está en solo 5.5. Esto le da margen para tener un día regular y aún ganar.
        """
        send_message(chat_id, msg)
    
    elif "poisson" in pregunta:
        msg = f"""
📊 <b>MODELO POISSON</b>

{MEMORY['conocimiento']['poisson']}

<b>Precisión según estudios:</b>
• Básico: 48-53%
• Mejorado (con forma): 52-57%
• Mercado: 55-58%
• Máximo realista: 60% (Tenis)

<b>¿Por qué lo usamos?</b>
Porque es el mejor modelo estadístico para predecir goles/resultados en deportes. Nosotros lo mejoramos con datos de forma y head-to-head.
        """
        send_message(chat_id, msg)
    
    elif "kelly" in pregunta or "kriterion" in pregunta:
        msg = f"""
📊 <b>KRITERIO KELLY</b>

{MEMORY['conocimiento']['kelly']}

<b>En tu caso:</b>
• Bankroll: 3,065 Bs
• Máximo 3% por pick = 91.95 Bs
• Máximo 5% por día = 153 Bs
• Usamos 25% conservador

<b>¿Por qué?</b>
Para proteger tu bankroll y crecer de forma sostenible. Nunca apostamos más de lo que el modelo sugiere.
        """
        send_message(chat_id, msg)
    
    elif "ev" in pregunta or "valor esperado" in pregunta:
        msg = f"""
📊 <b>EXPECTED VALUE (EV)</b>

{MEMORY['conocimiento']['ev']}

<b>Tus picks de hoy:</b>
"""
        for bet_id, bet in MEMORY['apuestas_hoy']['picks'].items():
            msg += f"• {bet['pick']}: EV {bet['ev']}%\n"
        
        msg += f"""
<b>Regla:</b>
Solo apostamos si EV > 0%
        """
        send_message(chat_id, msg)
    
    elif "estrategia" in pregunta:
        msg = f"""
🎯 <b>TU ESTRATEGIA</b>

<b>Disciplinas:</b>
{chr(10).join(['• ' + d for d in MEMORY['estrategia']['disciplinas']])}

<b>Mercados favoritos:</b>
{chr(10).join(['• ' + m for m in MEMORY['estrategia']['mercados_favoritos']])}

<b>Mercados a evitar:</b>
{chr(10).join(['• ' + m for m in MEMORY['estrategia']['mercados_evitar']])}

<b>Principios:</b>
{chr(10).join(['• ' + p for p in MEMORY['estrategia']['principios']])}
        """
        send_message(chat_id, msg)
    
    elif "bankroll" in pregunta or "dinero" in pregunta:
        msg = f"""
💰 <b>TU BANKROLL</b>

<b>Actual:</b> {MEMORY['bankroll']['actual']} Bs

<b>Distribución:</b>
• 1xBet: {MEMORY['bankroll']['1xbet']} Bs
• micasino: {MEMORY['bankroll']['micasino']} Bs

<b>Límites:</b>
• Unidad: {MEMORY['bankroll']['unidad']} Bs (1%)
• Máximo/día: {MEMORY['bankroll']['max_por_dia']} Bs (5%)
• Máximo/pick: {MEMORY['bankroll']['max_por_pick']} Bs (2%)

<b>Exchange:</b> 1 USD = {MEMORY['usuario']['exchange_rate']} Bs
        """
        send_message(chat_id, msg)
    
    elif "hoy" in pregunta or "qué pasa" in pregunta:
        msg = f"""
📅 <b>HOY - {MEMORY['apuestas_hoy']['fecha']}</b>

<b>Tus apuestas:</b>
"""
        for bet_id, bet in MEMORY['apuestas_hoy']['picks'].items():
            emoji = "✅" if bet['estado'] == 'win' else "❌" if bet['estado'] == 'loss' else "⏳"
            msg += f"{emoji} {bet['pick']} ({bet['casa']})\n"
        
        msg += f"""
<b>Total apostado:</b> {MEMORY['apuestas_hoy']['total_apostado']} Bs
<b>Pendientes:</b> {database['stats']['pending']}
        """
        send_message(chat_id, msg)
    
    else:
        msg = f"""
🤔 No tengo información específica sobre: "<i>{pregunta}</i>"

<b>Puedo contarte sobre:</b>
• "Yamamoto" → Por qué aposté a Yamamoto
• "Misiorowski" → Por qué aposté a Misiorowski
• "Stephens" → Por qué aposté a Stephens
• "Sanchez" → Por qué aposté a Sánchez
• "Sandoval" → Por qué aposté a Sandoval
• "Poisson" → Sobre el modelo estadístico
• "Kelly" → Sobre el criterio de Kelly
• "EV" → Sobre valor esperado
• "Estrategia" → Tu estrategia de apuestas
• "Bankroll" → Tu dinero actual

Pregúntame lo que quieras! 🧠
        """
        send_message(chat_id, msg)

def handle_status(chat_id):
    """Ver apuestas"""
    msg = """
📊 <b>ESTADO DE APUESTAS</b>

"""
    for bet_id, bet in MEMORY['apuestas_hoy']['picks'].items():
        emoji = "✅" if bet['estado'] == 'win' else "❌" if bet['estado'] == 'loss' else "⏳"
        msg += f"{emoji} <b>#{bet_id}</b> {bet['pick']}\n"
        msg += f"   💰 {bet['stake']} Bs → {bet['ganar']} Bs\n"
        msg += f"   📊 EV: {bet['ev']}%\n\n"
    
    msg += f"""
<b>Resumen:</b>
• Apostado: {MEMORY['apuestas_hoy']['total_apostado']} Bs
• Pendientes: {database['stats']['pending']}
• Bankroll: {MEMORY['bankroll']['actual']} Bs
    """
    send_message(chat_id, msg)

def handle_bankroll(chat_id):
    """Ver bankroll"""
    msg = f"""
💰 <b>TU BANKROLL</b>

<b>Actual:</b> {MEMORY['bankroll']['actual']} Bs

<b>Distribución:</b>
• 1xBet: {MEMORY['bankroll']['1xbet']} Bs
• micasino: {MEMORY['bankroll']['micasino']} Bs

<b>Límites:</b>
• Unidad (1%): {MEMORY['bankroll']['unidad']} Bs
• Máximo/día (5%): {MEMORY['bankroll']['max_por_dia']} Bs
• Máximo/pick (2%): {MEMORY['bankroll']['max_por_pick']} Bs

<b>Exchange:</b> 1 USD = {MEMORY['usuario']['exchange_rate']} Bs
    """
    send_message(chat_id, msg)

def handle_stats(chat_id):
    """Ver estadísticas"""
    msg = f"""
📈 <b>ESTADÍSTICAS</b>

<b>Hoy:</b>
• Ganadas: {database['stats']['wins']}
• Perdidas: {database['stats']['losses']}
• Pendientes: {database['stats']['pending']}

<b>Bankroll:</b>
• Inicial: {MEMORY['bankroll']['inicial']} Bs
• Actual: {MEMORY['bankroll']['actual']} Bs
• Ganancia: {'+' if database['stats']['total_profit'] >= 0 else ''}{database['stats']['total_profit']:.2f} Bs

<b>Modelo:</b>
• Precisión estimada: 52-57%
• EV promedio de picks: +13.6%
    """
    send_message(chat_id, msg)

def handle_picks(chat_id):
    """Ver picks"""
    msg = """
🎯 <b>TUS PICKS DE HOY</b>

"""
    for bet_id, bet in MEMORY['apuestas_hoy']['picks'].items():
        emoji = "✅" if bet['estado'] == 'win' else "❌" if bet['estado'] == 'loss' else "⏳"
        msg += f"{emoji} <b>#{bet_id}</b> {bet['pick']}\n"
        msg += f"   🏠 {bet['casa']} | 💰 {bet['cuota']} | 📊 EV: {bet['ev']}%\n"
        msg += f"   💵 {bet['stake']} Bs → {bet['ganar']} Bs\n\n"
    
    msg += f"""
<b>Total:</b> {MEMORY['apuestas_hoy']['total_apostado']} Bs (13.9%)
    """
    send_message(chat_id, msg)

def handle_win(chat_id, bet_id):
    """Marcar ganada"""
    if bet_id not in MEMORY['apuestas_hoy']['picks']:
        send_message(chat_id, "❌ Apuesta no encontrada.")
        return
    
    bet = MEMORY['apuestas_hoy']['picks'][bet_id]
    bet['estado'] = 'win'
    profit = bet['ganar'] - bet['stake']
    
    database['stats']['wins'] += 1
    database['stats']['pending'] -= 1
    database['stats']['total_profit'] += profit
    database['stats']['bankroll'] = MEMORY['bankroll']['inicial'] + database['stats']['total_profit']
    
    MEMORY['bankroll']['actual'] = database['stats']['bankroll']
    
    msg = f"""
🏆 <b>¡{bet['pick'].split()[0].upper()} GANÓ!</b>

✅ {bet['pick']}
💰 Ganancia: +{profit:.2f} Bs

📊 <b>Actualizado:</b>
• Wins: {database['stats']['wins']}
• Bankroll: {database['stats']['bankroll']} Bs
    """
    send_message(chat_id, msg)

def handle_loss(chat_id, bet_id):
    """Marcar perdida"""
    if bet_id not in MEMORY['apuestas_hoy']['picks']:
        send_message(chat_id, "❌ Apuesta no encontrada.")
        return
    
    bet = MEMORY['apuestas_hoy']['picks'][bet_id]
    bet['estado'] = 'loss'
    
    database['stats']['losses'] += 1
    database['stats']['pending'] -= 1
    database['stats']['total_profit'] -= bet['stake']
    database['stats']['bankroll'] = MEMORY['bankroll']['inicial'] + database['stats']['total_profit']
    
    MEMORY['bankroll']['actual'] = database['stats']['bankroll']
    
    msg = f"""
❌ <b>{bet['pick'].split()[0].upper()} PERDIÓ</b>

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
    msg = f"""
😊 ¡Todo bien, gracias!

Yo aquí monitoreando tus apuestas 24/7 🤖

<b>Tu estado hoy:</b>
• Bankroll: {MEMORY['bankroll']['actual']} Bs
• Apuestas pendientes: {database['stats']['pending']}
• Ganancia: {'+' if database['stats']['total_profit'] >= 0 else ''}{database['stats']['total_profit']:.2f} Bs

¿En qué te puedo ayudar? 🚀
    """
    send_message(chat_id, msg)

def handle_gracias(chat_id):
    """Gracias"""
    msg = """
¡De nada! 😊

Para eso estoy aquí, tu bot personal con memoria completa 🤖

Pregúntame lo que quieras sobre tus apuestas!
    """
    send_message(chat_id, msg)

def handle_hora(chat_id):
    """Hora"""
    now = datetime.now().strftime("%H:%M:%S")
    msg = f"🕐 Hora actual: {now}"
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
    """Respuesta por defecto - busca en memoria"""
    # Intentar encontrar algo relevante en la memoria
    text_lower = text.lower()
    
    # Buscar en picks
    for bet_id, bet in MEMORY['apuestas_hoy']['picks'].items():
        pick_words = bet['pick'].lower().split()
        event_words = bet['event'].lower().split()
        
        for word in pick_words:
            if len(word) > 3 and word in text_lower:
                handle_preguntar(chat_id, text)
                return
        
        for word in event_words:
            if len(word) > 3 and word in text_lower:
                handle_preguntar(chat_id, text)
                return
    
    # Buscar temas generales
    temas = ["poisson", "kelly", "ev", "estrategia", "bankroll", "modelo", "apuesta", "apostar", "por que", "porque", "razon", "razón"]
    for tema in temas:
        if tema in text_lower:
            handle_preguntar(chat_id, text)
            return
    
    # Si no encuentra nada específico
    msg = f"""
🤔 No encontré información específica sobre: "<i>{text}</i>"

<b>Puedo contarte sobre:</b>
• Tus picks: Yamamoto, Misiorowski, Stephens, Sanchez, Sandoval
• Modelos: Poisson, Kelly, EV
• Tu estrategia y bankroll
• Todo lo que hablamos hoy

Prueba preguntar:
• "¿Por qué aposté a Yamamoto?"
• "Cuéntame sobre Poisson"
• "¿Cuál es mi estrategia?"
    """
    send_message(chat_id, msg)

# ============================================
# WEBHOOK
# ============================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """Recibe mensajes de Telegram"""
    data = request.get_json()
    
    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "").lower().strip()
        
        # Normalizar
        text = re.sub(r'\s+', ' ', text)
        text = text.strip('?!.,;:')
        
        print(f"[MSG] {chat_id}: {text}")
        
        # Comandos
        if text in ["/start", "hola", "holi", "hello", "hey", "buenas"]:
            handle_start(chat_id)
        elif text in ["como estas", "que tal", "que onda"]:
            handle_como_estas(chat_id)
        elif text in ["gracias", "thanks"]:
            handle_gracias(chat_id)
        elif text in ["hora", "que hora es"]:
            handle_hora(chat_id)
        elif text in ["bien", "todo bien", "genial"]:
            send_message(chat_id, "😊 ¡Genial! ¿Necesitas algo?")
        elif text in ["mal", "regular"]:
            send_message(chat_id, "😔 Aquí estoy apoyándote. ¿Qué necesitas?")
        elif text in ["chiste"]:
            handle_chiste(chat_id)
        elif text == "/status" or text in ["apuestas", "mis apuestas"]:
            handle_status(chat_id)
        elif text == "/bankroll" or text in ["dinero", "cuanto tengo"]:
            handle_bankroll(chat_id)
        elif text == "/stats" or text in ["estadisticas"]:
            handle_stats(chat_id)
        elif text == "/picks" or text in ["picks", "selecciones"]:
            handle_picks(chat_id)
        elif text == "/memoria" or text in ["memoria", "que sabes", "que recuerdas"]:
            handle_memoria(chat_id)
        elif text.startswith("/win"):
            try:
                bet_id = int(text.split()[1])
                handle_win(chat_id, bet_id)
            except:
                send_message(chat_id, "Uso: /win [numero]")
        elif text.startswith("/loss"):
            try:
                bet_id = int(text.split()[1])
                handle_loss(chat_id, bet_id)
            except:
                send_message(chat_id, "Uso: /loss [numero]")
        elif text in ["/ayuda", "ayuda", "help", "comandos"]:
            handle_ayuda(chat_id)
        else:
            # Buscar en memoria
            handle_preguntar(chat_id, text)
    
    return jsonify({"ok": True})

@app.route('/')
def home():
    """Pagina principal"""
    return """
    <h1>🏆 SPORT EDGE BOT</h1>
    <p>Bot con MEMORIA COMPLETA - 24/7</p>
    <p>Status: ✅ ONLINE</p>
    <p>Memoria: ✅ Activa</p>
    """

@app.route('/health')
def health():
    """Health check"""
    return jsonify({"status": "ok", "bot": "sport-edge", "memory": "active"})

@app.route('/memory')
def show_memory():
    """Muestra la memoria (opcional)"""
    return jsonify(MEMORY)

# ============================================
# CONFIGURAR WEBHOOK
# ============================================

def setup_webhook():
    """Configura el webhook"""
    url = os.environ.get('RENDER_EXTERNAL_URL', 'https://sport-edge-bot.onrender.com')
    webhook_url = f"{url}/webhook"
    
    api_url = f"{TELEGRAM_API}/setWebhook"
    payload = {"url": webhook_url}
    
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        print(f"Webhook configurado: {webhook_url}")
        print(f"Respuesta: {response.json()}")
    except Exception as e:
        print(f"Error configurando webhook: {e}")

# ============================================
# MONITOR 24/7 - VERIFICA RESULTADOS
# ============================================

def monitor_loop():
    """Loop del monitor - corre en background"""
    print("[MONITOR] Iniciando monitor 24/7...")
    
    while True:
        try:
            now = datetime.now().strftime("%H:%M:%S")
            print(f"[MONITOR] Verificando... {now}")
            
            games = get_mlb_games()
            games_found = 0
            
            for bet_id, bet in MEMORY["apuestas_hoy"]["picks"].items():
                if bet["estado"] != "pending":
                    continue
                if bet.get("sport") == "tennis":
                    continue
                
                player = bet.get("player", "")
                
                for game in games:
                    is_home = player.lower() in game["home_pitcher"].lower()
                    is_away = player.lower() in game["away_pitcher"].lower()
                    
                    if not is_home and not is_away:
                        continue
                    
                    game_id = game["id"]
                    status = game["status"]
                    key = f"{bet_id}_{game_id}"
                    games_found += 1
                    
                    # INICIO DEL PARTIDO
                    if status == "In Progress" and key + "_start" not in MONITOR_STATUS["games_notified"]:
                        ks = get_pitcher_ks(player, game_id)
                        msg = f"""
⚾ <b>PARTIDO INICIADO</b>

{game['away']} @ {game['home']}
🎯 {bet['pick']}
📈 {player}: {ks} Ks
⏰ Esperando resultado...
                        """
                        send_message(CHAT_ID, msg)
                        MONITOR_STATUS["games_notified"][key + "_start"] = True
                        save_state()  # Persistir estado
                        print(f"[MONITOR] INICIO: {bet['event']}")
                    
                    # MITAD (5ta entrada)
                    elif status == "In Progress" and game["inning"] == 5 and key + "_mid" not in MONITOR_STATUS["games_notified"]:
                        ks = get_pitcher_ks(player, game_id)
                        line = bet["line"]
                        
                        if "O" in bet["pick"]:
                            status_text = f"{'WINNING' if ks > line else 'NEED MORE'} {ks}/{line} Ks"
                        else:
                            status_text = f"{ks} Ks"
                        
                        msg = f"""
📊 <b>MITAD DEL PARTIDO</b>

{game['away']} {game['away_score']} - {game['home']} {game['home_score']}
📈 {player}: {status_text}
🎯 {bet['pick']}
⏰ Final: ~20:00
                        """
                        send_message(CHAT_ID, msg)
                        MONITOR_STATUS["games_notified"][key + "_mid"] = True
                        save_state()  # Persistir estado
                        print(f"[MONITOR] MITAD: {bet['event']}")
                    
                    # FINAL
                    elif status == "Final" and key + "_final" not in MONITOR_STATUS["games_notified"]:
                        ks = get_pitcher_ks(player, game_id)
                        line = bet["line"]
                        score = f"{game['away']} {game['away_score']} - {game['home']} {game['home_score']}"
                        
                        if "O" in bet["pick"]:
                            won = ks > line
                        elif "U" in bet["pick"]:
                            won = ks < line
                        else:
                            won = None
                        
                        if won is not None:
                            profit = bet["ganar"] - bet["stake"] if won else -bet["stake"]
                            bet["estado"] = "win" if won else "loss"
                            MEMORY["bankroll"]["actual"] += profit
                            
                            if won:
                                msg = f"""
🏆 <b>¡{player.upper()} GANÓ!</b>

{score}
✅ {bet['pick']}
📈 {ks} Ks vs Línea {line}
💰 <b>Ganancia: +{profit:.2f} Bs</b>

📊 Bankroll: {MEMORY['bankroll']['actual']} Bs
                                """
                            else:
                                msg = f"""
❌ <b>{player.upper()} PERDIÓ</b>

{score}
❌ {bet['pick']}
📈 {ks} Ks vs Línea {line}
💸 <b>Pérdida: -{bet['stake']} Bs</b>

📊 Bankroll: {MEMORY['bankroll']['actual']} Bs
                                """
                            
                            send_message(CHAT_ID, msg)
                            MONITOR_STATUS["games_notified"][key + "_final"] = True
                            save_state()  # Persistir estado
                            print(f"[MONITOR] FINAL: {bet['event']} - {'WIN' if won else 'LOSS'}")
            
            # Verificar si todos terminaron
            pending = sum(1 for b in MEMORY["apuestas_hoy"]["picks"].values() if b["estado"] == "pending")
            if pending == 0 and games_found > 0:
                msg = f"""
✅ <b>TODOS LOS PARTIDOS TERMINARON</b>

📊 <b>RESUMEN FINAL</b>
• Bankroll: {MEMORY['bankroll']['actual']} Bs
• Ganancia: {'+' if MEMORY['bankroll']['actual'] - MEMORY['bankroll']['inicial'] >= 0 else ''}{MEMORY['bankroll']['actual'] - MEMORY['bankroll']['inicial']:.2f} Bs
                """
                send_message(CHAT_ID, msg)
                save_state()  # Persistir estado final
                print("[MONITOR] Todos los partidos terminaron")
                break
            
            print(f"[MONITOR] Pendientes: {pending}/5")
            
        except Exception as e:
            print(f"[MONITOR] Error: {e}")
        
        time.sleep(120)  # Verificar cada 2 minutos

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("SPORT EDGE BOT - Con Monitor 24/7")
    print("=" * 50)
    
    # Configurar webhook
    setup_webhook()
    
    # Iniciar monitor en background
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    print("[MONITOR] Monitor iniciado en background")
    
    # Iniciar servidor Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
