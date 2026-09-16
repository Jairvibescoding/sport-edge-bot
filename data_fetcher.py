"""
Fetcher de datos reales de fútbol y cuotas.
Requiere 2 API keys GRATUITAS:
1. football-data.org → https://www.football-data.org/client/register (10 req/min, gratis)
2. the-odds-api.com → https://the-odds-api.com (500 req/mes, gratis)

Configurar en .env:
  FOOTBALL_DATA_API_KEY=tu_key
  ODDS_API_KEY=tu_key
"""

import os
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Cargar .env desde el directorio del proyecto
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_env_path)

FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
logger.info(f"FOOTBALL_DATA_API_KEY loaded: {'YES' if FOOTBALL_DATA_KEY else 'NO'}")


@dataclass
class TeamStats:
    team_name: str
    team_id: int
    league: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    home_goals_for: int = 0
    home_goals_against: int = 0
    away_goals_for: int = 0
    away_goals_against: int = 0
    home_played: int = 0
    away_played: int = 0
    points: int = 0
    form: str = ""
    position: int = 0

    @property
    def avg_goals_for(self) -> float:
        return self.goals_for / self.played if self.played > 0 else 1.3

    @property
    def avg_goals_against(self) -> float:
        return self.goals_against / self.played if self.played > 0 else 1.1

    @property
    def home_avg_for(self) -> float:
        return self.home_goals_for / self.home_played if self.home_played > 0 else 1.5

    @property
    def home_avg_against(self) -> float:
        return self.home_goals_against / self.home_played if self.home_played > 0 else 1.0

    @property
    def away_avg_for(self) -> float:
        return self.away_goals_for / self.away_played if self.away_played > 0 else 1.1

    @property
    def away_avg_against(self) -> float:
        return self.away_goals_against / self.away_played if self.away_played > 0 else 1.3


@dataclass
class MatchFixture:
    fixture_id: int
    league: str
    league_id: int
    home_team: str
    away_team: str
    home_id: int
    away_id: int
    kickoff: str
    status: str = "SCHEDULED"


@dataclass
class MatchOdds:
    fixture_id: int
    home_team: str
    away_team: str
    kickoff: str = ""
    markets: Dict[str, Dict[str, float]] = field(default_factory=dict)
    bookmakers: List[Dict[str, Any]] = field(default_factory=list)


class FootballDataFetcher:
    """Fetches real match data from football-data.org"""

    BASE_URL = "https://api.football-data.org/v4"

    LEAGUE_MAP = {
        "Premier League": "PL",
        "La Liga": "PD",
        "Serie A": "SA",
        "Bundesliga": "BL1",
        "Ligue 1": "FL1",
        "Champions League": "CL",
        "Eredivisie": "DED",
        "Primeira Liga": "PPL",
        "Championship": "ELC",
        "MLS": "MLS",
        "Argentina Liga Profesional": None,
        "Brasil Serie A": None,
        "Copa Libertadores": "CL",
        "Copa Sudamericana": None,
        "Liga MX": None,
    }

    def __init__(self):
        self.headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self._standings_cache = {}
        self._fixtures_cache = {}

    def _get(self, endpoint: str, params: dict = None) -> Optional[dict]:
        try:
            r = self.session.get(f"{self.BASE_URL}{endpoint}", params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                logger.warning("football-data.org rate limit - esperando 60s")
                return None
            else:
                logger.error(f"football-data.org {r.status_code}: {r.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"Error football-data.org: {e}")
            return None

    def get_standings(self, league: str = "Premier League") -> List[TeamStats]:
        league_id = self.LEAGUE_MAP.get(league, 39)
        cache_key = f"{league_id}_{datetime.now().strftime('%Y%m%d')}"

        if cache_key in self._standings_cache:
            return self._standings_cache[cache_key]

        data = self._get(f"/competitions/{league_id}/standings")
        if not data:
            return []

        teams = []
        for table in data.get("standings", []):
            if table.get("type") == "TOTAL":
                for row in table.get("table", []):
                    team_info = row.get("team", {})
                    stats = TeamStats(
                        team_name=team_info.get("shortName", team_info.get("name", "Unknown")),
                        team_id=team_info.get("id", 0),
                        league=league,
                        played=row.get("playedGames", 0),
                        wins=row.get("won", 0),
                        draws=row.get("draw", 0),
                        losses=row.get("lost", 0),
                        goals_for=row.get("goalsFor", 0),
                        goals_against=row.get("goalsAgainst", 0),
                        points=row.get("points", 0),
                        position=row.get("position", 0),
                    )

                    form = row.get("form", "")
                    stats.form = form[-5:] if form else ""

                    teams.append(stats)

        for team in teams:
            for table in data.get("standings", []):
                if table.get("type") == "HOME":
                    for row in table.get("table", []):
                        if row.get("team", {}).get("id") == team.team_id:
                            team.home_played = row.get("playedGames", 0)
                            team.home_goals_for = row.get("goalsFor", 0)
                            team.home_goals_against = row.get("goalsAgainst", 0)
                if table.get("type") == "AWAY":
                    for row in table.get("table", []):
                        if row.get("team", {}).get("id") == team.team_id:
                            team.away_played = row.get("playedGames", 0)
                            team.away_goals_for = row.get("goalsFor", 0)
                            team.away_goals_against = row.get("goalsAgainst", 0)

        self._standings_cache[cache_key] = teams
        return teams

    def get_fixtures(self, league: str = "Premier League", days_ahead: int = 7) -> List[MatchFixture]:
        league_id = self.LEAGUE_MAP.get(league, 39)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        end = (datetime.utcnow() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        data = self._get(f"/competitions/{league_id}/matches", {
            "dateFrom": today,
            "dateTo": end,
            "status": "SCHEDULED"
        })

        if not data:
            return []

        fixtures = []
        for m in data.get("matches", []):
            fixtures.append(MatchFixture(
                fixture_id=m.get("id", 0),
                league=league,
                league_id=league_id,
                home_team=m.get("homeTeam", {}).get("shortName", "TBD"),
                away_team=m.get("awayTeam", {}).get("shortName", "TBD"),
                home_id=m.get("homeTeam", {}).get("id", 0),
                away_id=m.get("awayTeam", {}).get("id", 0),
                kickoff=m.get("utcDate", ""),
                status=m.get("status", "SCHEDULED"),
            ))

        self._fixtures_cache[league_id] = fixtures
        return fixtures

    def get_recent_results(self, league: str = "Premier League", matchdays: int = 10) -> List[Dict]:
        league_id = self.LEAGUE_MAP.get(league, 39)
        data = self._get(f"/competitions/{league_id}/matches", {
            "status": "FINISHED"
        })

        if not data:
            return []

        results = []
        for m in data.get("matches", [])[-matchdays * 20:]:
            results.append({
                "id": m.get("id"),
                "home": m.get("homeTeam", {}).get("shortName"),
                "away": m.get("awayTeam", {}).get("shortName"),
                "home_goals": m.get("score", {}).get("fullTime", {}).get("home"),
                "away_goals": m.get("score", {}).get("fullTime", {}).get("away"),
                "matchday": m.get("matchday"),
                "utc_date": m.get("utcDate"),
            })

        return results


class OddsFetcher:
    """Fetches real odds from the-odds-api.com"""

    BASE_URL = "https://api.the-odds-api.com/v4"

    SPORT_MAP = {
        "Premier League": "soccer_epl",
        "La Liga": "soccer_spain_la_liga",
        "Serie A": "soccer_italy_serie_a",
        "Bundesliga": "soccer_germany_bundesliga",
        "Ligue 1": "soccer_france_ligue_one",
        "Champions League": "soccer_uefa_champs_league",
        "Eredivisie": "soccer_netherlands_eredivisie",
        "Argentina Liga Profesional": "soccer_argentina_primera_division",
        "Brasil Serie A": "soccer_brazil_campeonato",
        "Copa Libertadores": "soccer_conmebol_copa_libertadores",
        "Copa Sudamericana": "soccer_conmebol_copa_sudamericana",
        "Liga MX": "soccer_mexico_ligamx",
        "MLS": "soccer_usa_mls",
        "Portugal Primeira Liga": "soccer_portugal_primeira_liga",
        "Turquia Super Lig": "soccer_turkey_super_league",
        "Japon J League": "soccer_japan_j_league",
        "Korea K League": "soccer_korea_kleague1",
        "Chile Primera Division": "soccer_chile_campeonato",
        "China Super League": "soccer_china_superleague",
        "Championship": "soccer_efl_champ",
    }

    def __init__(self):
        self.api_key = ODDS_API_KEY
        self.session = requests.Session()
        self._remaining_requests = 500

    def get_odds(self, league: str = "Premier League", markets: str = "h2h,totals,spreads") -> List[MatchOdds]:
        if not self.api_key:
            logger.warning("ODDS_API_KEY no configurada. Usando datos de ejemplo.")
            return self._get_sample_odds()

        sport = self.SPORT_MAP.get(league, "soccer_epl")

        try:
            r = self.session.get(
                f"{self.BASE_URL}/sports/{sport}/odds/",
                params={
                    "apiKey": self.api_key,
                    "regions": "eu,uk",
                    "markets": markets,
                    "oddsFormat": "decimal",
                    "bookmakers": "bet365,1xbet,williamhill,unibet,pinnacle,betfair"
                },
                timeout=15
            )

            self._remaining_requests = int(r.headers.get("x-requests-remaining", 500))

            if r.status_code == 200:
                return self._parse_odds(r.json())
            else:
                logger.error(f"the-odds-api {r.status_code}: {r.text[:200]}")
                return []
        except Exception as e:
            logger.error(f"Error odds API: {e}")
            return []

    def _parse_odds(self, data: list) -> List[MatchOdds]:
        results = []
        for match in data:
            odds = MatchOdds(
                fixture_id=0,
                home_team=match.get("home_team", ""),
                away_team=match.get("away_team", ""),
                kickoff=match.get("commence_time", ""),
            )

            for bookmaker in match.get("bookmakers", []):
                bm_name = bookmaker.get("title", bookmaker.get("key", ""))
                bm_data = {"name": bm_name, "markets": {}}

                for market in bookmaker.get("markets", []):
                    market_key = market.get("key", "")
                    outcomes = {}

                    for outcome in market.get("outcomes", []):
                        name = outcome.get("name", "")
                        price = outcome.get("price", 0)
                        outcomes[name] = price

                        if market_key not in odds.markets:
                            odds.markets[market_key] = {}
                        if name not in odds.markets[market_key] or price > odds.markets[market_key][name]:
                            odds.markets[market_key][name] = price

                    bm_data["markets"][market_key] = outcomes

                odds.bookmakers.append(bm_data)

            results.append(odds)

        return results

    def get_remaining_requests(self) -> int:
        return self._remaining_requests

    def _get_sample_odds(self) -> List[MatchOdds]:
        return [
            MatchOdds(
                fixture_id=1,
                home_team="Arsenal",
                away_team="Chelsea",
                kickoff=datetime.now().isoformat(),
                markets={
                    "h2h": {"Arsenal": 1.85, "Draw": 3.50, "Chelsea": 4.20},
                    "totals": {"Over 2.5": 1.85, "Under 2.5": 1.95},
                },
                bookmakers=[
                    {"name": "Ejemplo Bet365", "markets": {"h2h": {"Arsenal": 1.85, "Draw": 3.50, "Chelsea": 4.20}}},
                    {"name": "Ejemplo 1xBet", "markets": {"h2h": {"Arsenal": 1.90, "Draw": 3.40, "Chelsea": 4.30}}},
                ]
            ),
            MatchOdds(
                fixture_id=2,
                home_team="Man United",
                away_team="Liverpool",
                kickoff=datetime.now().isoformat(),
                markets={
                    "h2h": {"Man United": 2.90, "Draw": 3.30, "Liverpool": 2.40},
                    "totals": {"Over 2.5": 1.80, "Under 2.5": 2.00},
                },
                bookmakers=[
                    {"name": "Ejemplo Bet365", "markets": {"h2h": {"Man United": 2.90, "Draw": 3.30, "Liverpool": 2.40}}},
                ]
            ),
        ]

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


class DataManager:
    """Central data manager that combines stats + odds + form + H2H"""

    def __init__(self):
        self.football = FootballDataFetcher()
        self.odds = OddsFetcher()

    def get_team_stats(self, team_name: str, league: str = "Premier League") -> Optional[TeamStats]:
        # Primero buscar en football-data.org (ligas europeas)
        league_code = self.football.LEAGUE_MAP.get(league)
        if league_code:  # Solo buscar si la liga esta en football-data.org
            standings = self.football.get_standings(league)
            for team in standings:
                if team_name.lower() in team.team_name.lower():
                    return team

        # Si no se encontro, intentar con scraper (Brasil, Argentina)
        try:
            from scraper import get_scraped_team_stats
            scraped = get_scraped_team_stats(team_name, league)
            if scraped:
                return TeamStats(
                    team_name=scraped["team_name"],
                    team_id=0,
                    league=league,
                    position=scraped.get("position", 0),
                    played=scraped["played"],
                    wins=scraped.get("won", 0),
                    draws=scraped.get("drawn", 0),
                    losses=scraped.get("lost", 0),
                    goals_for=scraped["goals_for"],
                    goals_against=scraped["goals_against"],
                    points=scraped.get("points", 0),
                    form=scraped.get("form", ""),
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Scraper error for {team_name}: {e}")

        return None

    def get_team_form(self, team_name: str, league: str = "Premier League") -> Optional[Dict]:
        """Obtiene forma reciente de un equipo desde Transfermarkt."""
        try:
            from form_scraper import get_team_form
            return get_team_form(team_name, league)
        except Exception as e:
            logger.warning(f"Form scraper error for {team_name}: {e}")
            return None

    def get_h2h(self, team1: str, team2: str, league: str = "Premier League",
                home_stats=None, away_stats=None) -> Optional[Dict]:
        """Obtiene historial de enfrentamientos directos."""
        try:
            from head2head import get_h2h
            return get_h2h(team1, team2, league, home_stats, away_stats)
        except Exception as e:
            logger.warning(f"H2H scraper error for {team1} vs {team2}: {e}")
            return None

    def get_available_leagues(self) -> List[str]:
        return list(FootballDataFetcher.LEAGUE_MAP.keys())

    def get_full_match_analysis(self, home_team: str, away_team: str,
                                 league: str = "Premier League") -> Dict[str, Any]:
        standings = self.football.get_standings(league)
        odds_list = self.odds.get_odds(league)

        home_stats = None
        away_stats = None
        for t in standings:
            if home_team.lower() in t.team_name.lower():
                home_stats = t
            if away_team.lower() in t.team_name.lower():
                away_stats = t

        match_odds = None
        for o in odds_list:
            if (home_team.lower() in o.home_team.lower() and
                away_team.lower() in o.away_team.lower()):
                match_odds = o
                break

        # Fetch form data (graceful fallback)
        home_form = self.get_team_form(home_team, league)
        away_form = self.get_team_form(away_team, league)

        # Fetch H2H data (graceful fallback)
        h2h_data = self.get_h2h(home_team, away_team, league, home_stats, away_stats)

        return {
            "home_stats": asdict(home_stats) if home_stats else None,
            "away_stats": asdict(away_stats) if away_stats else None,
            "home_form": home_form,
            "away_form": away_form,
            "h2h": h2h_data,
            "odds": asdict(match_odds) if match_odds else None,
            "odds_source": "the-odds-api" if self.odds.is_configured else "ejemplo",
            "stats_source": "football-data.org" if FOOTBALL_DATA_KEY else "estimado",
        }


def get_data_manager() -> DataManager:
    return DataManager()
