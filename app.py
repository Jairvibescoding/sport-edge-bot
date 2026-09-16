"""
Sports Analyzer - Centro de datos de apuestas deportivas en tiempo real.
Motor de análisis Poisson + cuotas reales + optimización de bankroll.
"""

import os
import json
import asyncio
from flask import Flask, render_template, request, jsonify
from datetime import datetime

from data_fetcher import get_data_manager, FootballDataFetcher, OddsFetcher
from analyzer import (
    calculate_poisson, calibrate_lambdas, calibrate_from_odds, find_value_bets,
    monte_carlo_simulation, LEAGUE_AVG_GOALS, calculate_enhanced_poisson
)
from budget_optimizer import optimize_budget, quick_bet_advice
from database import init_db, add_bet, get_bets, get_stats

app = Flask(__name__)
app.config["DOTENV_LOAD"] = False
app.secret_key = os.getenv("SECRET_KEY", "sports-analyzer-dev-key")

init_db()
data_mgr = get_data_manager()


@app.route("/")
def dashboard():
    stats = get_stats()
    recent_bets = get_bets(limit=10)
    leagues = data_mgr.get_available_leagues()
    odds_status = "Activa" if data_mgr.odds.is_configured else "Demo (sin API key)"
    stats_status = "Activa" if os.getenv("FOOTBALL_DATA_API_KEY") else "Estimada (sin API key)"
    return render_template("dashboard.html",
                           stats=stats, recent_bets=recent_bets,
                           leagues=leagues, odds_status=odds_status,
                           stats_status=stats_status)


# ============================================================
# API: Análisis completo de un partido
# ============================================================
@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.get_json()
    home_team = data.get("home_team", "")
    away_team = data.get("away_team", "")
    league = data.get("league", "Premier League")
    budget = float(data.get("budget", 100))

    analysis = data_mgr.get_full_match_analysis(home_team, away_team, league)

    home_stats = analysis.get("home_stats")
    away_stats = analysis.get("away_stats")
    home_form = analysis.get("home_form")
    away_form = analysis.get("away_form")
    h2h_data = analysis.get("h2h")

    # Use enhanced Poisson model
    try:
        model, factors = calculate_enhanced_poisson(
            home_stats, away_stats, league,
            home_form=home_form,
            away_form=away_form,
            h2h_data=h2h_data,
        )
        home_lambda = factors["enhanced_home_lambda"]
        away_lambda = factors["enhanced_away_lambda"]
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Enhanced model error, falling back to basic: {e}")
        home_lambda, away_lambda = calibrate_lambdas(home_stats, away_stats, league)
        model = calculate_poisson(home_lambda, away_lambda)
        factors = {
            "base_home_lambda": home_lambda,
            "base_away_lambda": away_lambda,
            "enhanced_home_lambda": home_lambda,
            "enhanced_away_lambda": away_lambda,
            "home_advantage": 1.15,
            "home_form": {"multiplier": 1.0, "string": "", "quality": "fallback"},
            "away_form": {"multiplier": 1.0, "string": "", "quality": "fallback"},
            "h2h": {"h2h_factor": 1.0, "h2h_confidence": "sin datos"},
            "adjustments": {"form_effect_home": 0, "form_effect_away": 0, "h2h_effect": 0},
        }

    mc = monte_carlo_simulation(home_lambda, away_lambda)

    odds_data = {}
    best_odds = {}
    if analysis.get("odds"):
        home_name = analysis["odds"].get("home_team", home_team).lower()
        away_name = analysis["odds"].get("away_team", away_team).lower()
        for bm in analysis["odds"].get("bookmakers", []):
            bm_name = bm.get("name", "")
            h2h = bm.get("markets", {}).get("h2h", {})
            if h2h:
                odds_data[bm_name] = {}
                for sel, val in h2h.items():
                    sel_lower = sel.lower()
                    if sel_lower == "draw":
                        key = "draw"
                    elif home_name in sel_lower or sel_lower in home_name:
                        key = "home"
                    elif away_name in sel_lower or sel_lower in away_name:
                        key = "away"
                    else:
                        key = sel_lower
                    odds_data[bm_name][key] = val
                    if key not in best_odds or val > best_odds[key]:
                        best_odds[key] = val

    if not odds_data and best_odds:
        odds_data["Mejor cuota"] = best_odds

    value_bets = []
    if odds_data:
        vb_list = find_value_bets(model, odds_data)
        for vb in vb_list:
            vb_dict = {
                "market": vb.market,
                "selection": vb.selection,
                "odds": vb.odds,
                "probability": vb.probability,
                "expected_value": vb.expected_value,
                "edge": vb.edge,
                "kelly_pct": vb.kelly_fraction,
                "confidence": vb.confidence,
                "bookmaker": vb.bookmaker,
            }
            value_bets.append(vb_dict)

    budget_plan = None
    if budget > 0 and value_bets:
        budget_plan = optimize_budget(bankroll=budget, value_bets=value_bets)

    result = {
        "match": {
            "home": home_team,
            "away": away_team,
            "league": league,
        },
        "stats": {
            "home": home_stats,
            "away": away_stats,
            "home_lambda": home_lambda,
            "away_lambda": away_lambda,
            "source": analysis.get("stats_source", "N/A"),
        },
        "poisson": {
            "home_win": round(model.home_win_prob * 100, 1),
            "draw": round(model.draw_prob * 100, 1),
            "away_win": round(model.away_win_prob * 100, 1),
            "over_15": round(model.over_15 * 100, 1),
            "over_25": round(model.over_25 * 100, 1),
            "over_35": round(model.over_35 * 100, 1),
            "btts": round(model.btts_prob * 100, 1),
            "correct_scores": model.correct_scores,
        },
        "monte_carlo": mc,
        "enhanced_factors": factors,
        "odds": {
            "source": analysis.get("odds_source", "N/A"),
            "best": best_odds,
            "all_bookmakers": odds_data,
        },
        "value_bets": value_bets,
        "budget_plan": None,
    }

    if budget_plan:
        result["budget_plan"] = {
            "bankroll": budget_plan.bankroll,
            "total_staked": budget_plan.total_staked,
            "total_potential_profit": budget_plan.total_potential_profit,
            "num_bets": budget_plan.num_bets,
            "risk_level": budget_plan.risk_level,
            "kelly_multiplier": budget_plan.kelly_multiplier,
            "warnings": budget_plan.warnings,
            "bets": [
                {
                    "match": b.match,
                    "market": b.market,
                    "selection": b.selection,
                    "odds": b.odds,
                    "probability": b.probability,
                    "edge": b.edge,
                    "kelly_full": b.kelly_full,
                    "kelly_fraction": b.kelly_fraction,
                    "stake": b.stake,
                    "potential_profit": b.potential_profit,
                    "confidence": b.confidence,
                    "bookmaker": b.bookmaker,
                }
                for b in budget_plan.bets
            ],
        }

    return jsonify(result)


# ============================================================
# API: Quick bet (una sola apuesta)
# ============================================================
@app.route("/api/quick-bet", methods=["POST"])
def api_quick_bet():
    data = request.get_json()
    result = quick_bet_advice(
        bankroll=float(data.get("budget", 100)),
        odds=float(data.get("odds", 2.0)),
        probability=float(data.get("probability", 50)),
        match_name=data.get("match", "N/A"),
        market=data.get("market", "1X2"),
        selection=data.get("selection", "N/A"),
        bookmaker=data.get("bookmaker", "N/A"),
    )
    return jsonify(result)


# ============================================================
# API: Obtener fixtures de una liga
# ============================================================
@app.route("/api/fixtures/<league>")
def api_fixtures(league):
    days = int(request.args.get("days", 7))
    fixtures = data_mgr.football.get_fixtures(league, days)
    return jsonify({
        "league": league,
        "fixtures": [
            {
                "id": f.fixture_id,
                "home": f.home_team,
                "away": f.away_team,
                "kickoff": f.kickoff,
                "status": f.status,
            }
            for f in fixtures
        ]
    })


# ============================================================
# API: Standings de una liga
# ============================================================
@app.route("/api/standings/<league>")
def api_standings(league):
    standings = data_mgr.football.get_standings(league)
    return jsonify({
        "league": league,
        "standings": [
            {
                "position": t.position,
                "team": t.team_name,
                "played": t.played,
                "won": t.wins,
                "drawn": t.draws,
                "lost": t.losses,
                "gf": t.goals_for,
                "ga": t.goals_against,
                "gd": t.goals_for - t.goals_against,
                "points": t.points,
                "form": t.form,
                "avg_gf": t.avg_goals_for,
                "avg_ga": t.avg_goals_against,
            }
            for t in standings
        ]
    })


# ============================================================
# API: Escanear value bets en todas las ligas
# ============================================================
@app.route("/api/scan")
def api_scan():
    leagues = request.args.get("leagues", "Premier League").split(",")
    budget = float(request.args.get("budget", 100))

    all_value_bets = []
    for league in leagues:
        league = league.strip()
        fixtures = data_mgr.football.get_fixtures(league, days_ahead=7)
        standings = data_mgr.football.get_standings(league)
        odds_list = data_mgr.odds.get_odds(league)

        standings_map = {t.team_name.lower(): t for t in standings}

        for fixture in fixtures:
            home_stats = standings_map.get(fixture.home_team.lower())
            away_stats = standings_map.get(fixture.away_team.lower())

            # Fetch form and H2H for enhanced model
            home_form = data_mgr.get_team_form(fixture.home_team, league)
            away_form = data_mgr.get_team_form(fixture.away_team, league)
            h2h_data = data_mgr.get_h2h(fixture.home_team, fixture.away_team, league,
                                          home_stats.__dict__ if home_stats else None,
                                          away_stats.__dict__ if away_stats else None)

            try:
                model, factors = calculate_enhanced_poisson(
                    home_stats.__dict__ if home_stats else None,
                    away_stats.__dict__ if away_stats else None,
                    league,
                    home_form=home_form,
                    away_form=away_form,
                    h2h_data=h2h_data,
                )
                home_lambda = factors["enhanced_home_lambda"]
                away_lambda = factors["enhanced_away_lambda"]
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Enhanced scan error: {e}")
                home_lambda, away_lambda = calibrate_lambdas(
                    home_stats.__dict__ if home_stats else None,
                    away_stats.__dict__ if away_stats else None,
                    league
                )
                model = calculate_poisson(home_lambda, away_lambda)
                factors = None

            odds_data = {}
            for o in odds_list:
                if (fixture.home_team.lower() in o.home_team.lower() and
                    fixture.away_team.lower() in o.away_team.lower()):
                    for bm in o.bookmakers:
                        bm_name = bm.get("name", "")
                        h2h = bm.get("markets", {}).get("h2h", {})
                        if h2h:
                            odds_data[bm_name] = {k.lower(): v for k, v in h2h.items()}
                    break

            if odds_data:
                vbs = find_value_bets(model, odds_data)
                for vb in vbs:
                    vb_dict = {
                        "match": f"{fixture.home_team} vs {fixture.away_team}",
                        "league": league,
                        "market": vb.market,
                        "selection": vb.selection,
                        "odds": vb.odds,
                        "probability": vb.probability,
                        "expected_value": vb.expected_value,
                        "edge": vb.edge,
                        "kelly_pct": vb.kelly_fraction,
                        "confidence": vb.confidence,
                        "bookmaker": vb.bookmaker,
                        "home_lambda": home_lambda,
                        "away_lambda": away_lambda,
                    }
                    if factors:
                        vb_dict["enhanced_factors"] = {
                            "home_form": factors.get("home_form", {}).get("quality", "N/A"),
                            "away_form": factors.get("away_form", {}).get("quality", "N/A"),
                            "h2h": factors.get("h2h", {}).get("h2h_confidence", "N/A"),
                        }
                    all_value_bets.append(vb_dict)

    all_value_bets.sort(key=lambda x: -x.get("edge", 0))

    budget_plan = None
    if budget > 0 and all_value_bets:
        budget_plan = optimize_budget(bankroll=budget, value_bets=all_value_bets)

    return jsonify({
        "total_value_bets": len(all_value_bets),
        "value_bets": all_value_bets[:30],
        "budget_plan": {
            "bankroll": budget_plan.bankroll,
            "total_staked": budget_plan.total_staked,
            "total_potential_profit": budget_plan.total_potential_profit,
            "num_bets": budget_plan.num_bets,
            "risk_level": budget_plan.risk_level,
            "bets": [
                {
                    "match": b.match,
                    "selection": b.selection,
                    "odds": b.odds,
                    "stake": b.stake,
                    "potential_profit": b.potential_profit,
                    "edge": b.edge,
                    "confidence": b.confidence,
                    "bookmaker": b.bookmaker,
                }
                for b in budget_plan.bets
            ],
        } if budget_plan else None,
    })


# ============================================================
# API: Guardar apuesta
# ============================================================
@app.route("/api/bets", methods=["GET", "POST"])
def api_bets():
    if request.method == "POST":
        data = request.get_json()
        bet_id = add_bet(
            event_name=data.get("event_name", "N/A"),
            sport=data.get("sport", "Soccer"),
            market=data.get("market", "1X2"),
            selection=data.get("selection", "N/A"),
            odds=float(data.get("odds", 0)),
            stake=float(data.get("stake", 0)),
            probability=float(data.get("probability", 0)) / 100,
        )
        return jsonify({"success": True, "bet_id": bet_id})

    bets = get_bets(limit=50)
    return jsonify({"bets": bets})


# ============================================================
# API: Estadisticas
# ============================================================
@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())


# ============================================================
# API: Analisis manual (pegas cuotas de 1xBet/tu casino)
# ============================================================
@app.route("/api/analyze_manual", methods=["POST"])
def api_analyze_manual():
    """Analiza cuotas pegadas manualmente por el usuario."""
    data = request.get_json()
    budget = float(data.get("budget", 0))

    matches = data.get("matches", [])
    all_results = []

    for m in matches:
        home_team = m.get("home_team", "Local")
        away_team = m.get("away_team", "Visitante")
        odds_1x2 = m.get("odds_1x2", {})  # {"1": x, "X": y, "2": z}
        league = m.get("league", "")

        if not odds_1x2:
            continue

        stats_source = "manual"
        home_stats = None
        away_stats = None
        home_lambda = 1.5
        away_lambda = 1.2
        factors = None

        if league:
            home_stats = data_mgr.get_team_stats(home_team, league)
            away_stats = data_mgr.get_team_stats(away_team, league)

        if home_stats and away_stats:
            # Fetch form and H2H for enhanced model
            home_form = data_mgr.get_team_form(home_team, league)
            away_form = data_mgr.get_team_form(away_team, league)
            h2h_data = data_mgr.get_h2h(home_team, away_team, league,
                                          home_stats.__dict__ if home_stats else None,
                                          away_stats.__dict__ if away_stats else None)

            try:
                model, factors = calculate_enhanced_poisson(
                    home_stats, away_stats, league,
                    home_form=home_form,
                    away_form=away_form,
                    h2h_data=h2h_data,
                )
                home_lambda = factors["enhanced_home_lambda"]
                away_lambda = factors["enhanced_away_lambda"]
                stats_source = "datos reales + enhanced"
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Enhanced model error in manual: {e}")
                home_lambda, away_lambda = calibrate_lambdas(home_stats, away_stats, league)
                model = calculate_poisson(home_lambda, away_lambda)
                stats_source = "datos reales"
        else:
            from analyzer import LEAGUE_AVG_GOALS
            league_avg = LEAGUE_AVG_GOALS.get(league, 2.8) / 2
            home_lambda = league_avg * 1.15
            away_lambda = league_avg
            stats_source = f"modelo neutro (promedio {league or 'general'})"
            model = calculate_poisson(home_lambda, away_lambda)

        if factors is None:
            model = calculate_poisson(home_lambda, away_lambda)

        mc = monte_carlo_simulation(home_lambda, away_lambda)

        odds_data = {"Mi Casino": {}}
        for sel, val in odds_1x2.items():
            key_map = {"1": "home", "X": "draw", "2": "away"}
            key = key_map.get(sel.strip(), sel.lower())
            odds_data["Mi Casino"][key] = float(val)

        vb_list = find_value_bets(model, odds_data)
        value_bets = []
        for vb in vb_list:
            vb_dict = {
                "market": vb.market,
                "selection": vb.selection,
                "odds": vb.odds,
                "bookmaker": vb.bookmaker,
                "probability": round(vb.probability * 100, 1),
                "expected_value": round(vb.edge, 1),
                "confidence": vb.confidence,
                "home_lambda": home_lambda,
                "away_lambda": away_lambda,
                "match": f"{home_team} vs {away_team}",
            }
            value_bets.append(vb_dict)

        result = {
            "home_team": home_team,
            "away_team": away_team,
            "league": league,
            "stats_source": stats_source,
            "home_lambda": round(home_lambda, 2),
            "away_lambda": round(away_lambda, 2),
            "poisson": {
                "home_win": round(model.home_win_prob * 100, 1),
                "draw": round(model.draw_prob * 100, 1),
                "away_win": round(model.away_win_prob * 100, 1),
            },
            "enhanced_factors": factors,
            "odds_1x2": odds_1x2,
            "value_bets": value_bets,
        }
        all_results.append(result)

    all_vb = []
    for r in all_results:
        all_vb.extend(r["value_bets"])
    all_vb.sort(key=lambda x: -x.get("expected_value", 0))

    budget_plan = None
    if budget > 0 and all_vb:
        budget_plan = optimize_budget(bankroll=budget, value_bets=all_vb)

    return jsonify({
        "matches": all_results,
        "total_value_bets": len(all_vb),
        "budget_plan": {
            "bankroll": budget_plan.bankroll,
            "total_staked": budget_plan.total_staked,
            "total_potential_profit": budget_plan.total_potential_profit,
            "num_bets": budget_plan.num_bets,
            "risk_level": budget_plan.risk_level,
            "bets": [
                {
                    "match": b.match,
                    "selection": b.selection,
                    "odds": b.odds,
                    "stake": b.stake,
                    "potential_profit": b.potential_profit,
                    "edge": b.edge,
                    "confidence": b.confidence,
                    "bookmaker": b.bookmaker,
                }
                for b in budget_plan.bets
            ],
        } if budget_plan else None,
    })


# ============================================================
# API: Bet Finder - Partidos de mañana con comparación de odds
# ============================================================
# Cache para no gastar API credits
_betfinder_cache = {"data": None, "timestamp": 0}
_CACHE_TTL = 21600  # 6 hours

@app.route("/api/tomorrow")
def api_tomorrow():
    """Trae partidos de mañana con odds de todas las casas y encuentra las mejores."""
    from datetime import datetime, timedelta, timezone
    import requests as req
    import time as _time

    # Check cache first
    if _betfinder_cache["data"] and _time.time() - _betfinder_cache["timestamp"] < _CACHE_TTL:
        cached = _betfinder_cache["data"]
        # If custom date requested, filter cache
        target_date = request.args.get("date", "")
        if target_date and target_date != cached.get("date"):
            pass  # Cache miss, need fresh data
        else:
            return jsonify(cached)

    API_KEY = os.getenv("ODDS_API_KEY", "")
    if not API_KEY:
        return jsonify({"error": "ODDS_API_KEY no configurada", "matches": []})

    # Get all soccer sports
    try:
        r = req.get("https://api.the-odds-api.com/v4/sports/", params={"apiKey": API_KEY}, timeout=10)
        soccer_sports = [s["key"] for s in r.json() if s["key"].startswith("soccer_") and s["active"]]
    except Exception as e:
        return jsonify({"error": str(e), "matches": []})

    # Only fetch popular leagues (stay under API limit)
    PRIORITY_LEAGUES = [
        "soccer_epl", "soccer_spain_la_liga", "soccer_italy_serie_a",
        "soccer_germany_bundesliga", "soccer_france_ligue_one",
        "soccer_uefa_champs_league", "soccer_uefa_europa_league",
        "soccer_brazil_campeonato", "soccer_argentina_primera_division",
        "soccer_mexico_ligamx", "soccer_efl_champ", "soccer_england_efl_cup",
        "soccer_conmebol_copa_libertadores", "soccer_conmebol_copa_sudamericana",
    ]
    soccer_sports = [s for s in soccer_sports if s in PRIORITY_LEAGUES]

    # Get tomorrow's date in Venezuela time (UTC-4)
    VENEZUELA_TZ = timezone(timedelta(hours=-4))
    now_local = datetime.now(VENEZUELA_TZ)
    
    # Accept date parameter (default: tomorrow)
    target_date = request.args.get("date", "")
    if target_date:
        tomorrow = target_date
    else:
        tomorrow = (now_local + timedelta(days=1)).strftime("%Y-%m-%d")
    
    today = now_local.strftime("%Y-%m-%d")

    # Fetch odds PARALLEL for speed
    from concurrent.futures import ThreadPoolExecutor, as_completed

    sport_names = {
        "soccer_epl": "Premier League",
        "soccer_spain_la_liga": "La Liga",
        "soccer_italy_serie_a": "Serie A",
        "soccer_germany_bundesliga": "Bundesliga",
        "soccer_france_ligue_one": "Ligue 1",
        "soccer_uefa_champs_league": "Champions League",
        "soccer_uefa_europa_league": "Europa League",
        "soccer_brazil_campeonato": "Brasileirao",
        "soccer_argentina_primera_division": "Argentina LPF",
        "soccer_mexico_ligamx": "Liga MX",
        "soccer_efl_champ": "Championship",
        "soccer_england_efl_cup": "EFL Cup",
        "soccer_conmebol_copa_libertadores": "Copa Libertadores",
        "soccer_conmebol_copa_sudamericana": "Copa Sudamericana",
    }

    def fetch_sport(sport):
        try:
            r = req.get(
                f"https://api.the-odds-api.com/v4/sports/{sport}/odds/",
                params={"apiKey": API_KEY, "regions": "eu,uk", "markets": "h2h", "oddsFormat": "decimal"},
                timeout=15,
            )
            if r.status_code == 200:
                return (sport, r.json())
        except Exception:
            pass
        return (sport, [])

    all_matches = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_sport, s): s for s in soccer_sports}
        results = {}
        for future in as_completed(futures):
            sport, data = future.result()
            results[sport] = data

    for sport in soccer_sports:
        matches_data = results.get(sport, [])
        for match in matches_data:
            kickoff = match.get("commence_time", "")
            # Parse kickoff date
            if kickoff:
                try:
                    dt = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
                    match_date = dt.astimezone(VENEZUELA_TZ).strftime("%Y-%m-%d")
                except:
                    match_date = kickoff[:10]
            else:
                match_date = ""
            
            # Show matches for target date (or today + tomorrow if no date specified)
            if match_date == tomorrow or (not target_date and match_date in [today, tomorrow]):
                # Process odds per bookmaker
                bookmakers = []
                all_odds = {"home": [], "draw": [], "away": []}

                for bm in match.get("bookmakers", []):
                    bm_name = bm.get("title", bm.get("key", ""))
                    bm_odds = {}
                    for mk in bm.get("markets", []):
                        for o in mk.get("outcomes", []):
                            name = o["name"]
                            price = o["price"]
                            bm_odds[name] = price

                            if name == match["home_team"]:
                                all_odds["home"].append({"bookmaker": bm_name, "odds": price})
                            elif name == "Draw":
                                all_odds["draw"].append({"bookmaker": bm_name, "odds": price})
                            elif name == match["away_team"]:
                                all_odds["away"].append({"bookmaker": bm_name, "odds": price})

                    if bm_odds:
                        bookmakers.append({"name": bm_name, "odds": bm_odds})

                # Find best odds for each selection
                best = {}
                for sel, odds_list in all_odds.items():
                    if odds_list:
                        best_odds_item = max(odds_list, key=lambda x: x["odds"])
                        worst_odds_item = min(odds_list, key=lambda x: x["odds"])
                        best[sel] = {
                            "odds": best_odds_item["odds"],
                            "bookmaker": best_odds_item["bookmaker"],
                            "worst_odds": worst_odds_item["odds"],
                            "worst_bookmaker": worst_odds_item["bookmaker"],
                            "spread": round(best_odds_item["odds"] - worst_odds_item["odds"], 2),
                            "spread_pct": round((best_odds_item["odds"] / worst_odds_item["odds"] - 1) * 100, 1) if worst_odds_item["odds"] > 0 else 0,
                        }

                # Calculate bookmaker margin (overround)
                if best:
                    implied_total = sum(1/best[s]["odds"] for s in ["home", "draw", "away"] if s in best)
                    margin = round((implied_total - 1) * 100, 1)
                else:
                    margin = 0

                league_name = sport_names.get(sport, sport.replace("soccer_", "").replace("_", " ").title())

                # Calculate value for each selection
                # Filter out exchange odds (Smarkets, Betfair) for value calculation
                REGULAR_BOOKS = {"1xbet", "bet365", "williamhill", "unibet", "pinnacle", "betfair", 
                                 "betclic", "boylesports", "888sport", "betway", "betsson", "marathon bet",
                                 "nordic bet", "leo vegas", "codere", "tipico", "betano", "bet victor",
                                 "matchbook", "c瑯roral", "ladbrokes", "sky bet", "paddy power"}
                
                value_analysis = {}
                if best:
                    # Use conservative odds (not extreme exchange odds) for value calc
                    conservative_best = {}
                    for sel in ["home", "draw", "away"]:
                        if sel in best:
                            # Find odds from regular bookmakers only
                            regular_odds = []
                            for bm in match.get("bookmakers", []):
                                bm_key = bm.get("name", "").lower()
                                if any(rb in bm_key for rb in ["bet365", "1xbet", "williamhill", "unibet", "pinnacle", "betclic"]):
                                    for mk in bm.get("markets", []):
                                        for o in mk.get("outcomes", []):
                                            name_lower = o["name"].lower()
                                            if (sel == "home" and match["home_team"].lower() in name_lower) or \
                                               (sel == "away" and match["away_team"].lower() in name_lower) or \
                                               (sel == "draw" and o["name"] == "Draw"):
                                                regular_odds.append(o["price"])
                            
                            if regular_odds:
                                conservative_best[sel] = {
                                    "odds": max(regular_odds),
                                    "bookmaker": "Mejor casa regular",
                                }
                            else:
                                conservative_best[sel] = best[sel]

                    implied_home = 1 / conservative_best["home"]["odds"] if "home" in conservative_best else 0
                    implied_draw = 1 / conservative_best["draw"]["odds"] if "draw" in conservative_best else 0
                    implied_away = 1 / conservative_best["away"]["odds"] if "away" in conservative_best else 0

                    # Normalize probabilities
                    total_impl = implied_home + implied_draw + implied_away
                    if total_impl > 0:
                        fair_home = implied_home / total_impl
                        fair_draw = implied_draw / total_impl
                        fair_away = implied_away / total_impl
                    else:
                        fair_home = fair_draw = fair_away = 0.33

                    # Value = (fair_prob * best_odds) - 1
                    for sel, fair_prob in [("home", fair_home), ("draw", fair_draw), ("away", fair_away)]:
                        if sel in conservative_best:
                            odds = conservative_best[sel]["odds"]
                            ev = (fair_prob * odds) - 1
                            value_analysis[sel] = {
                                "fair_prob": round(fair_prob * 100, 1),
                                "implied_prob": round((1 / odds) * 100, 1) if odds > 0 else 0,
                                "edge": round(ev * 100, 1),
                                "has_value": ev > 0.03 and odds > 1.1,  # 3% min edge, odds > 1.1
                                "rating": "ALTA" if ev > 0.08 else "MEDIA" if ev > 0.03 else "BAJA",
                                "best_odds": odds,
                                "bookmaker": conservative_best[sel].get("bookmaker", ""),
                            }

                all_matches.append({
                    "home_team": match["home_team"],
                    "away_team": match["away_team"],
                    "league": league_name,
                    "sport_key": sport,
                    "kickoff": kickoff,
                    "num_bookmakers": len(bookmakers),
                    "best": best,
                    "margin": margin,
                    "bookmakers": bookmakers,
                    "value": value_analysis,
                })

    # Sort by league then kickoff
    all_matches.sort(key=lambda x: (x["league"], x["kickoff"]))

    # Find best combinada (accumulator) - top value bets from regular bookmakers
    all_value_picks = []
    for m in all_matches:
        for sel, v in m.get("value", {}).items():
            if v.get("has_value") and m["best"].get(sel):
                # Use conservative odds
                odds = v.get("best_odds", m["best"][sel]["odds"])
                bm = v.get("bookmaker", m["best"][sel]["bookmaker"])
                all_value_picks.append({
                    "match": f"{m['home_team']} vs {m['away_team']}",
                    "selection": sel,
                    "selection_name": m["home_team"] if sel == "home" else m["away_team"] if sel == "away" else "Empate",
                    "odds": odds,
                    "bookmaker": bm,
                    "edge": v["edge"],
                    "rating": v["rating"],
                    "league": m["league"],
                })

    # Sort by edge (best value first)
    all_value_picks.sort(key=lambda x: -x["edge"])

    # Build combinadas (pick top 3-4 value bets)
    combinadas = []
    if len(all_value_picks) >= 2:
        for combo_size in [2, 3, 4]:
            picks = all_value_picks[:combo_size]
            if len(picks) >= combo_size:
                combined_odds = 1
                for p in picks:
                    combined_odds *= p["odds"]
                combined_edge = sum(p["edge"] for p in picks)
                avg_rating = "ALTA" if combined_edge / combo_size > 8 else "MEDIA" if combined_edge / combo_size > 3 else "BAJA"
                combinadas.append({
                    "size": combo_size,
                    "picks": picks,
                    "combined_odds": round(combined_odds, 2),
                    "total_edge": round(combined_edge, 1),
                    "rating": avg_rating,
                    "example_bet": {
                        "stake": 10,
                        "potential_profit": round(10 * combined_odds - 10, 2),
                    },
                })

    result = {
        "date": tomorrow,
        "total_matches": len(all_matches),
        "matches": all_matches,
        "value_picks": all_value_picks[:15],
        "combinadas": combinadas,
        "cached": False,
    }

    # Save to cache
    _betfinder_cache["data"] = result
    _betfinder_cache["timestamp"] = _time.time()

    return jsonify(result)


@app.route("/api/clear-cache", methods=["POST"])
def api_clear_cache():
    """Limpia el cache del Bet Finder."""
    _betfinder_cache["data"] = None
    _betfinder_cache["timestamp"] = 0
    return jsonify({"ok": True, "message": "Cache limpiado"})


@app.route("/api/cache-status")
def api_cache_status():
    """Muestra el estado del cache."""
    import time as _time
    if _betfinder_cache["data"]:
        age = int(_time.time() - _betfinder_cache["timestamp"])
        return jsonify({
            "cached": True,
            "age_seconds": age,
            "age_hours": round(age / 3600, 1),
            "expires_in_hours": round((_CACHE_TTL - age) / 3600, 1),
            "matches": _betfinder_cache["data"].get("total_matches", 0),
        })
    return jsonify({"cached": False})


if __name__ == "__main__":
    print("Sports Analyzer - Centro de datos en http://localhost:5000")
    print(f"  Odds API: {'Activa' if data_mgr.odds.is_configured else 'Demo'}")
    print(f"  Stats API: {'football-data.org' if os.getenv('FOOTBALL_DATA_API_KEY') else 'Estimadas'}")
    app.run(debug=True, host="0.0.0.0", port=5000, load_dotenv=False)
