import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "sports.db")


def init_db():
    """Inicializa la base de datos con las tablas necesarias."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT NOT NULL,
                sport TEXT NOT NULL,
                market TEXT NOT NULL,
                selection TEXT NOT NULL,
                odds REAL NOT NULL,
                stake REAL NOT NULL,
                probability REAL NOT NULL,
                expected_value REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                result REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                settled_at TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                sport TEXT NOT NULL,
                league TEXT,
                start_time TIMESTAMP,
                home_team TEXT,
                away_team TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS odds_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                market TEXT NOT NULL,
                selection TEXT NOT NULL,
                odds REAL NOT NULL,
                bookmaker TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events(id)
            )
        """)
        conn.commit()


@contextmanager
def get_db():
    """Context manager para conexiones a la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def add_bet(event_name: str, sport: str, market: str, selection: str,
            odds: float, stake: float, probability: float) -> int:
    """Registra una nueva apuesta."""
    expected_value = (odds * probability - 1) * stake
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO bets (event_name, sport, market, selection, odds, stake, probability, expected_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (event_name, sport, market, selection, odds, stake, probability, expected_value))
        conn.commit()
        return cursor.lastrowid


def get_bets(limit: int = 50, status: str = None) -> List[Dict[str, Any]]:
    """Obtiene apuestas con opción de filtrar por estado."""
    with get_db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM bets WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM bets ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(row) for row in rows]


def settle_bet(bet_id: int, result: float) -> bool:
    """ liquida una apuesta con el resultado (ganancia neta)."""
    with get_db() as conn:
        conn.execute(
            "UPDATE bets SET result = ?, status = 'settled', settled_at = ? WHERE id = ?",
            (result, datetime.now().isoformat(), bet_id)
        )
        conn.commit()
        return conn.total_changes > 0


def get_stats() -> Dict[str, Any]:
    """Obtiene estadísticas generales de apuestas."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM bets").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM bets WHERE status = 'pending'").fetchone()[0]
        won = conn.execute("SELECT COUNT(*) FROM bets WHERE status = 'settled' AND result > 0").fetchone()[0]
        lost = conn.execute("SELECT COUNT(*) FROM bets WHERE status = 'settled' AND result <= 0").fetchone()[0]
        total_staked = conn.execute("SELECT COALESCE(SUM(stake), 0) FROM bets").fetchone()[0]
        total_return = conn.execute("SELECT COALESCE(SUM(result), 0) FROM bets WHERE status = 'settled'").fetchone()[0]
        
        roi = ((total_return - total_staked) / total_staked * 100) if total_staked > 0 else 0
        
        return {
            "total_bets": total,
            "pending": pending,
            "won": won,
            "lost": lost,
            "win_rate": (won / (won + lost) * 100) if (won + lost) > 0 else 0,
            "total_staked": total_staked,
            "total_return": total_return,
            "profit": total_return - total_staked,
            "roi": roi
        }


def add_event(name: str, sport: str, league: str = None, 
              start_time: str = None, home_team: str = None, away_team: str = None) -> int:
    """Agrega un evento deportivo."""
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT OR IGNORE INTO events (name, sport, league, start_time, home_team, away_team)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, sport, league, start_time, home_team, away_team))
        conn.commit()
        return cursor.lastrowid


def add_odds(event_id: int, market: str, selection: str, odds: float, bookmaker: str) -> int:
    """Agrega una cuota al historial."""
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO odds_history (event_id, market, selection, odds, bookmaker)
            VALUES (?, ?, ?, ?, ?)
        """, (event_id, market, selection, odds, bookmaker))
        conn.commit()
        return cursor.lastrowid
