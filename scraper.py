"""
FBref/Transfermarkt Scraper - Stats reales para ligas sin API.
Combina football-data.org (Brasil) + Transfermarkt (Argentina).
Cache de 1 hora para no saturar los sitios.
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import os
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com",
}

FD_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "b9b358f4ca134a29a326a77926eeee17")

# Cache file
CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
CACHE_FILE = os.path.join(CACHE_DIR, "scraper_cache.json")
CACHE_TTL = 3600  # 1 hour


def _load_cache() -> dict:
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            ts = data.get("_timestamp", 0)
            if time.time() - ts < CACHE_TTL:
                return data.get("data", {})
    except Exception:
        pass
    return {}


def _save_cache(data: dict):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"_timestamp": time.time(), "data": data}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Cache save error: {e}")


# ============================================================
# BRAZIL SERIE A - via football-data.org (code: BSA)
# ============================================================
def _fetch_brazil_fdorg() -> Dict[str, dict]:
    """Fetch Brazil Serie A standings from football-data.org."""
    cache = _load_cache()
    if "brazil" in cache:
        return cache["brazil"]

    results = {}
    try:
        r = requests.get(
            "https://api.football-data.org/v4/competitions/BSA/standings",
            headers={"X-Auth-Token": FD_KEY},
            timeout=15,
        )
        if r.status_code == 200:
            for st in r.json().get("standings", []):
                for row in st.get("table", []):
                    team_data = row.get("team", {})
                    team_name = team_data.get("shortName", team_data.get("name", "?"))
                    mp = row.get("playedGames", 0)
                    w = row.get("won", 0)
                    d = row.get("draw", 0)
                    l = row.get("lost", 0)
                    gf = row.get("goalsFor", 0)
                    ga = row.get("goalsAgainst", 0)
                    pts = row.get("points", 0)
                    pos = row.get("position", 0)

                    results[team_name.lower()] = {
                        "team_name": team_name,
                        "played": mp,
                        "won": w,
                        "drawn": d,
                        "lost": l,
                        "goals_for": gf,
                        "goals_against": ga,
                        "goal_difference": gf - ga,
                        "points": pts,
                        "position": pos,
                        "avg_goals_for": round(gf / max(mp, 1), 3),
                        "avg_goals_against": round(ga / max(mp, 1), 3),
                    }
            # Save to cache
            cache = _load_cache()
            cache["brazil"] = results
            _save_cache(cache)
            logger.info(f"Brazil: fetched {len(results)} teams from football-data.org")
        else:
            logger.warning(f"football-data.org BSA error: {r.status_code}")
    except Exception as e:
        logger.warning(f"Brazil fetch error: {e}")

    return results


# ============================================================
# ARGENTINA LIGA PROFESIONAL - via Transfermarkt scraping
# ============================================================
def _fetch_argentina_transfermarkt() -> Dict[str, dict]:
    """Fetch Argentina Liga Profesional standings from Transfermarkt."""
    cache = _load_cache()
    if "argentina" in cache:
        return cache["argentina"]

    results = {}
    try:
        time.sleep(2)  # Rate limit
        r = requests.get(
            "https://www.transfermarkt.com/primera-division/tabelle/wettbewerb/AR1N",
            headers=HEADERS,
            timeout=15,
        )
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.select_one("table.items")
            if table:
                rows = table.select("tbody tr")
                pos = 0
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) < 5:
                        continue

                    team_el = row.select_one("td.hauptlink a")
                    if not team_el:
                        continue

                    team_name = team_el.text.strip()
                    pos += 1

                    # Parse stats from zentriert cells
                    stat_cells = row.select("td.zentriert")
                    vals = [c.text.strip() for c in stat_cells]

                    # vals format: ['', MP, W, D, L, 'GF:GA', GD, Pts]
                    try:
                        mp = int(vals[1]) if len(vals) > 1 and vals[1].isdigit() else 0
                        w = int(vals[2]) if len(vals) > 2 and vals[2].isdigit() else 0
                        d = int(vals[3]) if len(vals) > 3 and vals[3].isdigit() else 0
                        l = int(vals[4]) if len(vals) > 4 and vals[4].isdigit() else 0

                        # Parse GF:GA
                        score_str = vals[5] if len(vals) > 5 else "0:0"
                        parts = score_str.split(":")
                        gf = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
                        ga = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0

                        pts = int(vals[7]) if len(vals) > 7 and vals[7].lstrip("-").isdigit() else 0
                    except (ValueError, IndexError):
                        continue

                    results[team_name.lower()] = {
                        "team_name": team_name,
                        "played": mp,
                        "won": w,
                        "drawn": d,
                        "lost": l,
                        "goals_for": gf,
                        "goals_against": ga,
                        "goal_difference": gf - ga,
                        "points": pts,
                        "position": pos,
                        "avg_goals_for": round(gf / max(mp, 1), 3),
                        "avg_goals_against": round(ga / max(mp, 1), 3),
                    }

            # Save to cache
            cache = _load_cache()
            cache["argentina"] = results
            _save_cache(cache)
            logger.info(f"Argentina: fetched {len(results)} teams from Transfermarkt")
        else:
            logger.warning(f"Transfermarkt error: {r.status_code}")
    except Exception as e:
        logger.warning(f"Argentina fetch error: {e}")

    return results


# ============================================================
# PUBLIC API
# ============================================================
def get_scraped_team_stats(team_name: str, league: str) -> Optional[Dict]:
    """
    Busca stats de un equipo en ligas que no estan en football-data.org.
    Soporta: 'Brasil Serie A', 'Argentina Liga Profesional'
    """
    team_lower = team_name.lower().strip()

    # Normalize league name
    league_lower = league.lower().strip()
    if "brasil" in league_lower or "brazil" in league_lower or "serie a" in league_lower:
        data = _fetch_brazil_fdorg()
    elif "argentin" in league_lower:
        data = _fetch_argentina_transfermarkt()
    else:
        return None

    # Team name aliases (user input -> Transfermarkt name)
    ALIASES = {
        "lanus": "lan",
        "dep. riestra": "riestra",
        "deportivo riestra": "riestra",
        "barracas central": "barracas c",
        "barracas": "barracas c",
        "atl. tucuman": "atl. tucum",
        "union santa fe": "uni",
        "ind. rivadavia": "ind. rivadavia",
        "estudiantes lp": "estudiantes lp",
        "instituto acc": "instituto acc",
        "central cordoba": "central c",
        "argentinos jrs": "argentinos jrs",
        "sarmiento junin": "sarmiento junin",
        "defensa y justicia": "defensa",
    }

    # Search by exact match first
    if team_lower in data:
        return data[team_lower]

    # Search by partial match
    for key, val in data.items():
        if team_lower in key or key in team_lower:
            return val
        # Handle common variations
        if team_lower.replace(".", "") in key or key in team_lower.replace(".", ""):
            return val
        if team_lower.replace("fc ", "") in key or team_lower.replace("cf ", "") in key:
            return val
        # Try alias
        alias = ALIASES.get(team_lower, "")
        if alias and alias in key:
            return val

    return None


def get_scraped_standings(league: str) -> List[Dict]:
    """Retorna toda la tabla de posiciones de una liga soportada."""
    league_lower = league.lower().strip()
    if "brasil" in league_lower or "brazil" in league_lower:
        data = _fetch_brazil_fdorg()
    elif "argentin" in league_lower:
        data = _fetch_argentina_transfermarkt()
    else:
        return []

    return sorted(data.values(), key=lambda x: x.get("position", 99))


# ============================================================
# Test
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=== BRAZIL TEST ===")
    for team in ["Bahia", "Remo", "Flamengo", "Palmeiras"]:
        stats = get_scraped_team_stats(team, "Brasil Serie A")
        if stats:
            print(f"  {stats['team_name']}: #{stats['position']} | {stats['played']}PJ | GF:{stats['goals_for']} GA:{stats['goals_against']} | AvgGF:{stats['avg_goals_for']} AvgGA:{stats['avg_goals_against']}")
        else:
            print(f"  {team}: NOT FOUND")

    print("\n=== ARGENTINA TEST ===")
    for team in ["Lanus", "Dep. Riestra", "Banfield", "Barracas Central", "River Plate", "Boca Juniors"]:
        stats = get_scraped_team_stats(team, "Argentina Liga Profesional")
        if stats:
            print(f"  {stats['team_name']}: #{stats['position']} | {stats['played']}PJ | GF:{stats['goals_for']} GA:{stats['goals_against']} | AvgGF:{stats['avg_goals_for']} AvgGA:{stats['avg_goals_against']}")
        else:
            print(f"  {team}: NOT FOUND")
