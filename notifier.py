import os
import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    Bot = None
    TelegramError = Exception

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Alerta a enviar."""
    title: str
    message: str
    priority: str = "normal"
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class TelegramNotifier:
    """Notificador por Telegram para alertas de apuestas."""

    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.bot: Optional[Bot] = None
        self.enabled = TELEGRAM_AVAILABLE and bool(self.bot_token and self.chat_id)

        if self.enabled:
            self.bot = Bot(token=self.bot_token)
            logger.info("Telegram notifier inicializado")
        else:
            logger.warning("Telegram no configurado - alertas solo en log")

    async def send_message(self, text: str, parse_mode: str = "HTML",
                           disable_notification: bool = False) -> bool:
        """Envía un mensaje simple."""
        if not self.enabled:
            logger.info(f"[TELEGRAM SIMULADO] {text}")
            return True

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_notification=disable_notification
            )
            return True
        except TelegramError as e:
            logger.error(f"Error enviando mensaje Telegram: {e}")
            return False

    async def send_alert(self, alert: Alert) -> bool:
        """Envía una alerta formateada."""
        priority_emoji = {
            "low": "🔵",
            "normal": "🟢",
            "high": "🟠",
            "urgent": "🔴"
        }
        emoji = priority_emoji.get(alert.priority, "🟢")

        tags_str = " ".join(f"#{tag}" for tag in alert.tags) if alert.tags else ""

        text = f"""
{emoji} <b>{alert.title}</b>

{alert.message}

{tags_str}
⏰ {datetime.now().strftime('%H:%M:%S')}
        """.strip()

        return await self.send_message(text)


def get_notifier() -> TelegramNotifier:
    """Obtiene una instancia del notificador."""
    return TelegramNotifier()


async def notify_value_bets(bets: List[Dict[str, Any]]) -> bool:
    """Notifica sobre value bets encontrados."""
    notifier = get_notifier()

    if not bets:
        return True

    message = "🎯 <b>VALUE BETS DETECTADOS</b>\n\n"

    for i, bet in enumerate(bets[:5], 1):
        emoji = "🔥" if bet['recommendation'] == 'FUERTE' else "⚡" if bet['recommendation'] == 'MEDIA' else "💡"
        message += f"""
{emoji} <b>{i}. {bet['market'].upper()}</b>
   Cuota: <b>{bet['odds']}</b>
   Probabilidad: {bet['probability']}%
   EV: +{bet['expected_value']}%
   Edge: +{bet['edge']}%
   Kelly: {bet['kelly_pct']}%
   Recomendación: {bet['recommendation']}
"""

    alert = Alert(
        title="Nuevos Value Bets",
        message=message,
        priority="high",
        tags=["value-bets", "oportunidad"]
    )

    return await notifier.send_alert(alert)


async def notify_bet_placed(bet: Dict[str, Any]) -> bool:
    """Notifica cuando se coloca una apuesta."""
    notifier = get_notifier()

    message = f"""
赛事: {bet.get('event_name', 'N/A')}
Mercado: {bet.get('market', 'N/A')}
Selección: {bet.get('selection', 'N/A')}
Cuota: {bet.get('odds', 0)}
Monto: ${bet.get('stake', 0):.2f}
Probabilidad: {bet.get('probability', 0) * 100:.1f}%
EV: {bet.get('expected_value', 0) * 100:.1f}%
    """

    alert = Alert(
        title="Apuesta Colocada",
        message=message,
        priority="normal",
        tags=["apuesta", "colocada"]
    )

    return await notifier.send_alert(alert)


async def notify_bet_result(bet: Dict[str, Any], won: bool) -> bool:
    """Notifica el resultado de una apuesta."""
    notifier = get_notifier()

    emoji = "✅" if won else "❌"
    result_text = "GANADA" if won else "PERDIDA"

    message = f"""
{emoji} <b>Apuesta {result_text}</b>

赛事: {bet.get('event_name', 'N/A')}
Mercado: {bet.get('market', 'N/A')}
Cuota: {bet.get('odds', 0)}
Resultado: ${bet.get('result', 0):+.2f}
    """

    alert = Alert(
        title=f"Apuesta {result_text}",
        message=message,
        priority="high" if won else "normal",
        tags=["resultado", result_text.lower()]
    )

    return await notifier.send_alert(alert)


async def notify_daily_summary(stats: Dict[str, Any]) -> bool:
    """Envía resumen diario de estadísticas."""
    notifier = get_notifier()

    emoji_profit = "📈" if stats['profit'] >= 0 else "📉"

    message = f"""
{emoji_profit} <b>RESUMEN DIARIO</b>

Total apuestas: {stats['total_bets']}
Ganadas: {stats['won']} | Perdidas: {stats['lost']}
Win Rate: {stats['win_rate']:.1f}%

Dinero apostado: ${stats['total_staked']:.2f}
Dinero recuperado: ${stats['total_return']:.2f}
Balance: ${stats['profit']:+.2f}
ROI: {stats['roi']:+.1f}%
    """

    alert = Alert(
        title="Resumen del Día",
        message=message,
        priority="normal",
        tags=["resumen", "diario"]
    )

    return await notifier.send_alert(alert)
