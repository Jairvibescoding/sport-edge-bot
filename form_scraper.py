"""
Form Scraper - Obtiene los últimos 5-10 resultados de cada equipo.
Scrapea de Transfermarkt para las principales ligas europeas.
Cache de 6 horas para evitar rate limits.
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import os
import logging
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.transfermarkt.com",
}

CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
FORM_CACHE_FILE = os.path.join(CACHE_DIR, "form_cache.json")
FORM_CACHE_TTL = 21600  # 6 hours

# Transfermarkt league slugs
LEAGUE_SLUGS = {
    "Premier League": {"slug": "premier-league", "wm_id": "GB1"},
    "La Liga": {"slug": "laliga", "wm_id": "ES1"},
    "Serie A": {"slug": "serie-a", "wm_id": "IT1"},
    "Bundesliga": {"slug": "1-bundesliga", "wm_id": "L1"},
    "Ligue 1": {"slug": "ligue-1", "wm_id": "FR1"},
    "Champions League": {"slug": "champions-league", "wm_id": "CL"},
    "Eredivisie": {"slug": "eredivisie", "wm_id": "NL1"},
    "Primeira Liga": {"slug": "liga-portugal", "wm_id": "PO1"},
    "Championship": {"slug": "championship", "wm_id": "GB2"},
    "MLS": {"slug": "major-league-soccer", "wm_id": "MLS1"},
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def _load_cache() -> dict:
    """Carga cache desde disco."""
    try:
        if os.path.exists(FORM_CACHE_FILE):
            with open(FORM_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            ts = data.get("_timestamp", 0)
            if time.time() - ts < FORM_CACHE_TTL:
                return data.get("data", {})
    except Exception:
        pass
    return {}


def _save_cache(data: dict):
    """Guarda cache en disco."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(FORM_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"_timestamp": time.time(), "data": data}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Form cache save error: {e}")


def _fetch_standings_page(league: str) -> Optional[BeautifulSoup]:
    """Obtiene la página de standings de Transfermarkt."""
    league_info = LEAGUE_SLUGS.get(league)
    if not league_info:
        logger.warning(f"League not supported for form scraping: {league}")
        return None

    slug = league_info["slug"]
    wm_id = league_info["wm_id"]
    url = f"https://www.transfermarkt.com/{slug}/tabelle/wettbewerb/{wm_id}"

    try:
        time.sleep(2)  # Rate limit - transfermarkt is strict
        r = SESSION.get(url, timeout=20)
        if r.status_code == 200:
            return BeautifulSoup(r.text, "html.parser")
        else:
            logger.warning(f"Transfermarkt standings {r.status_code} for {league}: {url}")
            return None
    except Exception as e:
        logger.error(f"Error fetching Transfermarkt standings for {league}: {e}")
        return None


def _parse_form_from_standings(soup: BeautifulSoup, league: str) -> Dict[str, Dict]:
    """
    Parsea la tabla de standings para extraer forma reciente.
    Transfermarkt muestra la columna 'Last 5' con W/D/L icons.
    """
    results = {}
    table = soup.select_one("table.items")
    if not table:
        logger.warning("No standings table found on Transfermarkt")
        return results

    rows = table.select("tbody tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 5:
            continue

        # Team name
        team_el = row.select_one("td.hauptlink a")
        if not team_el:
            continue

        team_name = team_el.text.strip()
        team_href = team_el.get("href", "")

        # Extract team ID from URL (e.g. /verein/11/saison_id/2026)
        team_id = 0
        id_match = re.search(r'/verein/(\d+)', team_href)
        if id_match:
            team_id = int(id_match.group(1))

        # Find the form column - look for the "Last 5" section
        # Transfermarkt has a td with class "zentriert" containing form icons
        form_cell = None
        for cell in cells:
            # The form column typically has class 'zentriert' and contains img elements
            if 'zentriert' in cell.get('class', []):
                imgs = cell.select("img")
                if imgs and len(imgs) >= 3:  # Form has multiple small icons
                    form_cell = cell
                    break

        form_string = ""
        goals_scored_recent = 0
        goals_conceded_recent = 0
        wins_recent = 0
        draws_recent = 0
        losses_recent = 0

        if form_cell:
            # Parse form icons - they use title attributes like "Win", "Draw", "Loss"
            imgs = form_cell.select("img")
            for img in imgs[:5]:  # Last 5 matches
                title = img.get("title", "").lower()
                if "win" in title or "sieg" in title:
                    form_string += "W"
                    wins_recent += 1
                elif "draw" in title or "unentschieden" in title:
                    form_string += "D"
                    draws_recent += 1
                elif "loss" in title or "niederlage" in title:
                    form_string += "L"
                    losses_recent += 1

            # If no title attributes, try alt text
            if not form_string:
                for img in imgs[:5]:
                    alt = img.get("alt", "").lower()
                    src = img.get("src", "").lower()
                    if "green" in src or "sieg" in alt:
                        form_string += "W"
                        wins_recent += 1
                    elif "yellow" in src or "unentschieden" in alt:
                        form_string += "D"
                        draws_recent += 1
                    elif "red" in src or "niederlage" in alt:
                        form_string += "L"
                        losses_recent += 1

        # Parse overall stats from cells
        stat_cells = row.select("td.zentriert")
        vals = [c.text.strip() for c in stat_cells]

        try:
            mp = int(vals[1]) if len(vals) > 1 and vals[1].isdigit() else 0
            w = int(vals[2]) if len(vals) > 2 and vals[2].isdigit() else 0
            d = int(vals[3]) if len(vals) > 3 and vals[3].isdigit() else 0
            l = int(vals[4]) if len(vals) > 4 and vals[4].isdigit() else 0

            score_str = vals[5] if len(vals) > 5 else "0:0"
            parts = score_str.split(":")
            gf = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
            ga = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0

            pts = int(vals[7]) if len(vals) > 7 and vals[7].lstrip("-").isdigit() else 0
        except (ValueError, IndexError):
            mp = w = d = l = gf = ga = pts = 0

        # Calculate recent form stats (estimated from overall if form column missing)
        if not form_string and mp > 0:
            # Estimate from overall ratio
            recent_count = min(5, mp)
            wins_recent = round(w / mp * recent_count)
            draws_recent = round(d / mp * recent_count)
            losses_recent = recent_count - wins_recent - draws_recent
            losses_recent = max(0, losses_recent)
            form_string = "W" * wins_recent + "D" * draws_recent + "L" * losses_recent

        results[team_name.lower()] = {
            "team_name": team_name,
            "team_id": team_id,
            "league": league,
            "form_string": form_string,
            "form_last_5": form_string[-5:] if form_string else "",
            "wins_last_5": wins_recent,
            "draws_last_5": draws_recent,
            "losses_last_5": losses_recent,
            "played": mp,
            "wins": w,
            "draws": d,
            "losses": l,
            "goals_for": gf,
            "goals_against": ga,
            "points": pts,
            "avg_goals_for": round(gf / max(mp, 1), 3),
            "avg_goals_against": round(ga / max(mp, 1), 3),
            "home_win_rate": 0.0,
            "away_win_rate": 0.0,
        }

    return results


def _fetch_team_form_from_page(team_slug: str, team_id: int) -> Optional[Dict]:
    """
    Fetch detailed form for a specific team from their results page.
    Returns last 10 match results with goals.
    """
    if not team_id:
        return None

    url = f"https://www.transfermarkt.com/-/rekorde/verein/{team_id}/plus/1"

    try:
        time.sleep(2)
        # Try the results page instead
        url = f"https://www.transfermarkt.com/team-name/startseite/verein/{team_id}"
        r = SESSION.get(url, timeout=20)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, "html.parser")
        recent_results = []

        # Look for result boxes or recent matches section
        result_boxes = soup.select(".box-content .sb-result, .vereinsfiltertable .sb-result")
        for box in result_boxes[:10]:
            text = box.text.strip()
            # Parse "2 - 1" style results
            match = re.search(r'(\d+)\s*[-:]\s*(\d+)', text)
            if match:
                recent_results.append({
                    "home_goals": int(match.group(1)),
                    "away_goals": int(match.group(2)),
                })

        return {"recent_results": recent_results} if recent_results else None

    except Exception as e:
        logger.debug(f"Could not fetch team page for {team_slug}: {e}")
        return None


def get_team_form(team_name: str, league: str = "Premier League") -> Optional[Dict]:
    """
    Obtiene la forma reciente de un equipo.
    Retorna: form_string (ej "WWDWL"), stats de últimos partidos, factores de forma.
    """
    cache = _load_cache()
    cache_key = f"form_{league}_{team_name.lower()}"

    if cache_key in cache:
        return cache[cache_key]

    # Get standings page
    soup = _fetch_standings_page(league)
    if not soup:
        return None

    # Parse all teams form from standings
    all_form = _parse_form_from_standings(soup, league)

    # Save all to cache
    for team_key, form_data in all_form.items():
        full_cache_key = f"form_{league}_{team_key}"
        cache[full_cache_key] = form_data
    _save_cache(cache)

    # Return the specific team
    team_lower = team_name.lower().strip()
    if team_lower in all_form:
        return all_form[team_lower]

    # Try partial match
    for key, val in all_form.items():
        if team_lower in key or key in team_lower:
            return val

    return None


def calculate_form_factors(form_data: Optional[Dict]) -> Dict:
    """
    Calcula factores de forma a partir de los datos scrapeados.
    Retorna multiplicadores para ajustar el lambda de Poisson.
    """
    if not form_data:
        return {
            "form_multiplier": 1.0,
            "form_string": "",
            "recent_goals_scored": 0,
            "recent_goals_conceded": 0,
            "form_quality": "sin datos",
            "streak": "none",
            "win_rate_last_5": 0.0,
        }

    form_str = form_data.get("form_last_5", form_data.get("form_string", ""))
    wins = form_data.get("wins_last_5", 0)
    draws = form_data.get("draws_last_5", 0)
    losses = form_data.get("losses_last_5", 0)
    total = wins + draws + losses

    if total == 0:
        return {
            "form_multiplier": 1.0,
            "form_string": form_str,
            "recent_goals_scored": 0,
            "recent_goals_conceded": 0,
            "form_quality": "sin datos",
            "streak": "none",
            "win_rate_last_5": 0.0,
        }

    # Win rate in last 5
    win_rate = wins / total if total > 0 else 0.5

    # Form multiplier: ranges from 0.85 (terrible form) to 1.15 (great form)
    # Base is 1.0, adjusted by win rate vs expected (0.33 draws, etc.)
    if win_rate >= 0.8:
        form_multiplier = 1.15
        form_quality = "excelente"
    elif win_rate >= 0.6:
        form_multiplier = 1.10
        form_quality = "buena"
    elif win_rate >= 0.4:
        form_multiplier = 1.0
        form_quality = "regular"
    elif win_rate >= 0.2:
        form_multiplier = 0.92
        form_quality = "mala"
    else:
        form_multiplier = 0.85
        form_quality = "muy mala"

    # Streak detection
    streak = "none"
    if len(form_str) >= 3:
        last_3 = form_str[-3:]
        if last_3 == "WWW":
            streak = "3_wins"
            form_multiplier += 0.05  # Extra bonus for 3+ win streak
        elif last_3 == "LLL":
            streak = "3_losses"
            form_multiplier -= 0.05  # Extra penalty for 3+ loss streak
        elif form_str[-1] == "W" and form_str[-2] == "W":
            streak = "2_wins"
        elif form_str[-1] == "L" and form_str[-2] == "L":
            streak = "2_losses"

    return {
        "form_multiplier": round(min(max(form_multiplier, 0.80), 1.20), 3),
        "form_string": form_str,
        "recent_goals_scored": form_data.get("goals_for", 0),
        "recent_goals_conceded": form_data.get("goals_against", 0),
        "form_quality": form_quality,
        "streak": streak,
        "win_rate_last_5": round(win_rate * 100, 1),
    }


def get_bulk_form(teams: List[Tuple[str, str]]) -> Dict[str, Dict]:
    """
    Fetch form for multiple teams efficiently.
    teams: list of (team_name, league) tuples
    Returns: dict mapping team_name -> form data
    """
    results = {}
    fetched_leagues = set()

    for team_name, league in teams:
        # Only fetch each league once
        if league not in fetched_leagues:
            soup = _fetch_standings_page(league)
            if soup:
                all_form = _parse_form_from_standings(soup, league)
                cache = _load_cache()
                for team_key, form_data in all_form.items():
                    cache[f"form_{league}_{team_key}"] = form_data
                _save_cache(cache)
                fetched_leagues.add(league)

        form = get_team_form(team_name, league)
        if form:
            results[team_name] = form

    return results


# ============================================================
# Test
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    print("=== FORM SCRAPER TEST ===\n")

    test_teams = [
        ("Arsenal", "Premier League"),
        ("Man City", "Premier League"),
        ("Barcelona", "La Liga"),
        ("Real Madrid", "La Liga"),
        ("Bayern Munich", "Bundesliga"),
        ("Juventus", "Serie A"),
        ("PSG", "Ligue 1"),
    ]

    for team, league in test_teams:
        print(f"\n--- {team} ({league}) ---")
        form = get_team_form(team, league)
        if form:
            factors = calculate_form_factors(form)
            print(f"  Form: {factors['form_string']}")
            print(f"  Quality: {factors['form_quality']}")
            print(f"  Win rate (last 5): {factors['win_rate_last_5']}%")
            print(f"  Multiplier: {factors['form_multiplier']}")
            print(f"  Streak: {factors['streak']}")
        else:
            print("  No form data available")
