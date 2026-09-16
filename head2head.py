"""
Head-to-Head - Obtiene historial de enfrentamientos directos.
Usa football-data.org API (ya configurada) para ligas europeas.
Fallback: cálculo basado en stats de temporada.
Cache de 24 horas.
"""

import requests
import time
import json
import os
import logging
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
H2H_CACHE_FILE = os.path.join(CACHE_DIR, "h2h_cache.json")
H2H_CACHE_TTL = 86400  # 24 hours

# Load API key
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
try:
    from dotenv import load_dotenv
    load_dotenv(_env_path)
except ImportError:
    pass

import os as _os
FD_KEY = _os.getenv("FOOTBALL_DATA_API_KEY", "")

# football-data.org league codes
LEAGUE_CODES = {
    "Premier League": "PL",
    "La Liga": "PD",
    "Serie A": "SA",
    "Bundesliga": "BL1",
    "Ligue 1": "FL1",
    "Champions League": "CL",
    "Eredivisie": "DED",
    "Primeira Liga": "PPL",
    "Championship": "ELC",
}

SESSION = requests.Session()
SESSION.headers.update({"X-Auth-Token": FD_KEY})


def _load_cache() -> dict:
    try:
        if os.path.exists(H2H_CACHE_FILE):
            with open(H2H_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            ts = data.get("_timestamp", 0)
            if time.time() - ts < H2H_CACHE_TTL:
                return data.get("data", {})
    except Exception:
        pass
    return {}


def _save_cache(data: dict):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(H2H_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"_timestamp": time.time(), "data": data}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"H2H cache save error: {e}")


def _fetch_finished_matches(league: str) -> List[Dict]:
    """Fetch all finished matches for a league from football-data.org."""
    league_code = LEAGUE_CODES.get(league)
    if not league_code or not FD_KEY:
        return []

    try:
        time.sleep(1)  # Rate limit
        r = SESSION.get(
            f"https://api.football-data.org/v4/competitions/{league_code}/matches",
            params={"status": "FINISHED"},
            timeout=15,
        )
        if r.status_code == 200:
            matches = []
            for m in r.json().get("matches", []):
                home = m.get("homeTeam", {})
                away = m.get("awayTeam", {})
                score = m.get("score", {}).get("fullTime", {})
                matches.append({
                    "home_name": home.get("shortName", home.get("name", "")),
                    "home_id": home.get("id", 0),
                    "away_name": away.get("shortName", away.get("name", "")),
                    "away_id": away.get("id", 0),
                    "home_goals": score.get("home"),
                    "away_goals": score.get("away"),
                    "date": m.get("utcDate", ""),
                    "matchday": m.get("matchday", 0),
                })
            return matches
        else:
            logger.warning(f"football-data.org H2H error {r.status_code} for {league}")
            return []
    except Exception as e:
        logger.error(f"Error fetching H2H matches for {league}: {e}")
        return []


def _find_h2h_in_matches(matches: List[Dict], team1: str, team2: str) -> Optional[Dict]:
    """Filter matches between two teams and calculate H2H stats."""
    t1_lower = team1.lower().strip()
    t2_lower = team2.lower().strip()

    h2h_matches = []
    for m in matches:
        h_name = m["home_name"].lower()
        a_name = m["away_name"].lower()

        # Check if this match is between team1 and team2
        is_t1_home = t1_lower in h_name or h_name in t1_lower
        is_t2_away = t2_lower in a_name or a_name in t2_lower
        is_t2_home = t2_lower in h_name or h_name in t2_lower
        is_t1_away = t1_lower in a_name or a_name in t1_lower

        if (is_t1_home and is_t2_away) or (is_t2_home and is_t1_away):
            if m["home_goals"] is not None and m["away_goals"] is not None:
                h2h_matches.append(m)

    if len(h2h_matches) < 2:
        return None

    # Calculate stats
    team1_wins = 0
    team2_wins = 0
    draws = 0
    total_goals = 0
    team1_goals = []
    team2_goals = []

    for m in h2h_matches:
        hg = m["home_goals"]
        ag = m["away_goals"]
        total_goals += hg + ag

        is_t1_home = t1_lower in m["home_name"].lower() or m["home_name"].lower() in t1_lower

        if is_t1_home:
            team1_goals.append(hg)
            team2_goals.append(ag)
            if hg > ag:
                team1_wins += 1
            elif hg < ag:
                team2_wins += 1
            else:
                draws += 1
        else:
            team1_goals.append(ag)
            team2_goals.append(hg)
            if ag > hg:
                team1_wins += 1
            elif ag < hg:
                team2_wins += 1
            else:
                draws += 1

    total = len(h2h_matches)
    avg_goals = total_goals / total if total > 0 else 2.5
    avg_t1 = sum(team1_goals) / len(team1_goals) if team1_goals else 1.2
    avg_t2 = sum(team2_goals) / len(team2_goals) if team2_goals else 1.0

    if team2_wins > 0:
        ratio = (team1_wins + 0.5 * draws) / (team2_wins + 0.5 * draws)
    elif team1_wins > 0:
        ratio = 2.0
    else:
        ratio = 1.0

    return {
        "team1": team1,
        "team2": team2,
        "total_matches": total,
        "team1_wins": team1_wins,
        "team2_wins": team2_wins,
        "draws": draws,
        "team1_win_pct": round(team1_wins / total * 100, 1) if total > 0 else 33.3,
        "team2_win_pct": round(team2_wins / total * 100, 1) if total > 0 else 33.3,
        "draw_pct": round(draws / total * 100, 1) if total > 0 else 33.3,
        "avg_total_goals": round(avg_goals, 2),
        "avg_goals_team1": round(avg_t1, 2),
        "avg_goals_team2": round(avg_t2, 2),
        "h2h_ratio": round(ratio, 3),
        "recent_matches": [
            {"home_goals": m["home_goals"], "away_goals": m["away_goals"], "date": m["date"][:10]}
            for m in h2h_matches[-10:]
        ],
        "source": "football-data.org",
    }


def _estimate_h2h_from_stats(home_stats, away_stats) -> Optional[Dict]:
    """
    Estimate H2H from season stats when no direct history available.
    Uses relative strength to estimate likely outcome.
    """
    if not home_stats or not away_stats:
        return None

    def _g(s, k, d=0):
        if isinstance(s, dict):
            return s.get(k, d)
        return getattr(s, k, d)

    h_gf = _g(home_stats, "avg_goals_for", 1.3)
    h_ga = _g(home_stats, "avg_goals_against", 1.1)
    a_gf = _g(away_stats, "avg_goals_for", 1.1)
    a_ga = _g(away_stats, "avg_goals_against", 1.3)

    # Relative strength
    h_strength = h_gf * a_ga
    a_strength = a_gf * h_ga

    if a_strength > 0:
        ratio = h_strength / a_strength
    else:
        ratio = 1.5

    # Estimate wins/draws from strength ratio
    h_win_pct = min(70, max(15, 33 + (ratio - 1) * 25))
    a_win_pct = min(70, max(15, 33 - (ratio - 1) * 25))
    draw_pct = 100 - h_win_pct - a_win_pct
    draw_pct = max(10, draw_pct)

    return {
        "team1": _g(home_stats, "team_name", "Home"),
        "team2": _g(away_stats, "team_name", "Away"),
        "total_matches": 0,
        "team1_wins": 0,
        "team2_wins": 0,
        "draws": 0,
        "team1_win_pct": round(h_win_pct, 1),
        "team2_win_pct": round(a_win_pct, 1),
        "draw_pct": round(draw_pct, 1),
        "avg_total_goals": round((h_gf + a_gf) / 2 + (h_ga + a_ga) / 2, 2),
        "h2h_ratio": round(ratio, 3),
        "recent_matches": [],
        "source": "estimated_from_stats",
    }


def get_h2h(team1: str, team2: str, league: str = "Premier League",
            home_stats=None, away_stats=None) -> Optional[Dict]:
    """
    Obtiene el historial de enfrentamientos directos.
    Intenta football-data.org API primero, luego estima desde stats.
    Cache de 24 horas.
    """
    teams = sorted([team1.lower().strip(), team2.lower().strip()])
    cache_key = "h2h_%s_%s" % (teams[0], teams[1])

    cache = _load_cache()
    if cache_key in cache:
        return cache[cache_key]

    # Try football-data.org for the requested league only
    matches = _fetch_finished_matches(league)
    if matches:
        result = _find_h2h_in_matches(matches, team1, team2)
        if result and result["total_matches"] >= 2:
            cache[cache_key] = result
            _save_cache(cache)
            return result

    # Fallback: estimate from stats
    result = _estimate_h2h_from_stats(home_stats, away_stats)
    if result:
        cache[cache_key] = result
        _save_cache(cache)
        return result

    return None


def calculate_h2h_factor(h2h_data: Optional[Dict], is_home_team: bool = True) -> Dict:
    """
    Calcula el factor H2H para ajustar el lambda de Poisson.
    is_home_team: True si team1 en el H2H es el equipo local actual.
    """
    if not h2h_data or h2h_data.get("total_matches", 0) < 2:
        # Even for estimated data, use the ratio
        if h2h_data and h2h_data.get("source") == "estimated_from_stats":
            ratio = h2h_data.get("h2h_ratio", 1.0)
            if ratio >= 1.4:
                h2h_factor = 1.08
            elif ratio >= 1.1:
                h2h_factor = 1.04
            elif ratio >= 0.9:
                h2h_factor = 1.0
            elif ratio >= 0.7:
                h2h_factor = 0.96
            else:
                h2h_factor = 0.92

            if not is_home_team:
                h2h_factor = 1.0 / h2h_factor if h2h_factor != 0 else 1.0

            return {
                "h2h_factor": round(h2h_factor, 3),
                "h2h_confidence": "estimada",
                "h2h_record": "Estimado desde stats de temporada",
                "avg_goals_h2h": h2h_data.get("avg_total_goals", 2.7),
                "h2h_ratio": ratio,
            }

        return {
            "h2h_factor": 1.0,
            "h2h_confidence": "sin datos",
            "h2h_record": "N/A",
            "avg_goals_h2h": 2.7,
        }

    ratio = h2h_data.get("h2h_ratio", 1.0)

    if ratio >= 1.5:
        h2h_factor = 1.12
        confidence = "alta"
    elif ratio >= 1.2:
        h2h_factor = 1.06
        confidence = "media"
    elif ratio >= 0.8:
        h2h_factor = 1.0
        confidence = "media"
    elif ratio >= 0.6:
        h2h_factor = 0.94
        confidence = "media"
    else:
        h2h_factor = 0.88
        confidence = "alta"

    if not is_home_team:
        h2h_factor = 1.0 / h2h_factor if h2h_factor != 0 else 1.0

    t1_w = h2h_data.get("team1_wins", 0)
    t2_w = h2h_data.get("team2_wins", 0)
    draws = h2h_data.get("draws", 0)
    total = h2h_data.get("total_matches", 0)

    if total > 0:
        record = "%dW-%dD-%dL (%d matches)" % (t1_w, draws, t2_w, total)
    else:
        record = "Estimado desde stats"

    return {
        "h2h_factor": round(h2h_factor, 3),
        "h2h_confidence": confidence,
        "h2h_record": record,
        "avg_goals_h2h": h2h_data.get("avg_total_goals", 2.7),
        "h2h_ratio": ratio,
    }


# ============================================================
# Test
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    print("=== HEAD-TO-HEAD TEST ===\n")

    # Mock stats for estimation test
    home_mock = {"team_name": "Arsenal", "avg_goals_for": 2.1, "avg_goals_against": 0.9}
    away_mock = {"team_name": "Chelsea", "avg_goals_for": 1.7, "avg_goals_against": 1.1}

    test_pairs = [
        ("Arsenal", "Chelsea", "Premier League"),
        ("Barcelona", "Real Madrid", "La Liga"),
        ("Bayern Munich", "Dortmund", "Bundesliga"),
        ("Liverpool", "Man City", "Premier League"),
        ("Juventus", "AC Milan", "Serie A"),
    ]

    for t1, t2, league in test_pairs:
        print("\n--- %s vs %s (%s) ---" % (t1, t2, league))
        h2h = get_h2h(t1, t2, league, home_mock, away_mock)
        if h2h:
            factors = calculate_h2h_factor(h2h, is_home_team=True)
            print("  Source: %s" % h2h["source"])
            print("  Matches: %d" % h2h["total_matches"])
            print("  Record: %s" % factors["h2h_record"])
            print("  H2H Ratio: %s" % h2h["h2h_ratio"])
            print("  Factor: %s" % factors["h2h_factor"])
            print("  Avg Goals: %s" % h2h["avg_total_goals"])
            print("  Confidence: %s" % factors["h2h_confidence"])
        else:
            print("  No H2H data available")
