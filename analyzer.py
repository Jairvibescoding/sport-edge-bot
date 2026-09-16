"""
Motor de análisis con Poisson calibrado con datos reales.
Calcula probabilidades, value bets, y recomienda apuestas.
Versión enhanced: incluye forma reciente, H2H, ventaja local dinámica.
"""

import numpy as np
from scipy.stats import poisson
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


# Promedio de goles de la liga (para ajuste)
LEAGUE_AVG_GOALS = {
    "Premier League": 2.85,
    "La Liga": 2.65,
    "Serie A": 2.70,
    "Bundesliga": 3.10,
    "Ligue 1": 2.60,
    "Champions League": 2.90,
    "Eredivisie": 3.20,
    "MLS": 2.95,
}


@dataclass
class PoissonModel:
    home_lambda: float
    away_lambda: float
    home_win_prob: float = 0.0
    draw_prob: float = 0.0
    away_win_prob: float = 0.0
    over_15: float = 0.0
    over_25: float = 0.0
    over_35: float = 0.0
    btts_prob: float = 0.0
    correct_scores: Dict[str, float] = field(default_factory=dict)
    goal_probs: Dict[str, float] = field(default_factory=dict)


@dataclass
class ValueBet:
    market: str
    selection: str
    odds: float
    probability: float
    expected_value: float
    edge: float
    kelly_fraction: float
    confidence: str
    bookmaker: str = ""


def calculate_poisson(home_lambda: float, away_lambda: float,
                      max_goals: int = 8) -> PoissonModel:
    """Calcula distribución completa de Poisson."""
    model = PoissonModel(home_lambda=home_lambda, away_lambda=away_lambda)

    home_dist = [poisson.pmf(k, home_lambda) for k in range(max_goals + 1)]
    away_dist = [poisson.pmf(k, away_lambda) for k in range(max_goals + 1)]

    home_win = draw = away_win = 0.0
    over_15 = over_25 = over_35 = btts = 0.0
    correct_scores = {}

    for hg in range(max_goals + 1):
        for ag in range(max_goals + 1):
            prob = home_dist[hg] * away_dist[ag]
            correct_scores[f"{hg}-{ag}"] = round(prob, 4)

            if hg > ag:
                home_win += prob
            elif hg == ag:
                draw += prob
            else:
                away_win += prob

            total = hg + ag
            if total > 1.5:
                over_15 += prob
            if total > 2.5:
                over_25 += prob
            if total > 3.5:
                over_35 += prob
            if hg > 0 and ag > 0:
                btts += prob

    model.home_win_prob = round(home_win, 4)
    model.draw_prob = round(draw, 4)
    model.away_win_prob = round(away_win, 4)
    model.over_15 = round(over_15, 4)
    model.over_25 = round(over_25, 4)
    model.over_35 = round(over_35, 4)
    model.btts_prob = round(btts, 4)
    model.correct_scores = dict(sorted(correct_scores.items(), key=lambda x: -x[1])[:10])

    model.goal_probs = {
        "0": round(sum(home_dist[h] * away_dist[0] for h in range(max_goals + 1)), 4),
        "1": round(sum(home_dist[h] * away_dist[1] for h in range(max_goals + 1)) +
                    home_dist[0] * away_dist[1], 4),
        "2": round(sum(home_dist[h] * away_dist[a]
                        for h in range(max_goals + 1)
                        for a in range(max_goals + 1) if h + a == 2), 4),
        "3": round(sum(home_dist[h] * away_dist[a]
                        for h in range(max_goals + 1)
                        for a in range(max_goals + 1) if h + a == 3), 4),
        "4+": round(1 - sum(
            home_dist[h] * away_dist[a]
            for h in range(max_goals + 1)
            for a in range(max_goals + 1) if h + a <= 3
        ), 4),
    }

    return model


def _get_stat(stats, key, default=0):
    """Get a stat value from either a dict or a dataclass object."""
    if isinstance(stats, dict):
        return stats.get(key, default)
    return getattr(stats, key, default)


def calibrate_lambdas(home_team_stats, away_team_stats,
                       league: str = "Premier League",
                       home_advantage: float = 1.15) -> Tuple[float, float]:
    """
    Calcula lambdas de Poisson basado en datos reales del equipo.
    home_advantage = factor de ventaja local (default 15%)
    Acepta dicts o dataclass TeamStats.
    """
    league_avg = LEAGUE_AVG_GOALS.get(league, 2.8) / 2  # promedio por equipo

    if home_team_stats and away_team_stats:
        home_attack = _get_stat(home_team_stats, "avg_goals_for", league_avg)
        home_defense = _get_stat(home_team_stats, "avg_goals_against", league_avg)
        away_attack = _get_stat(away_team_stats, "avg_goals_for", league_avg)
        away_defense = _get_stat(away_team_stats, "avg_goals_against", league_avg)

        if _get_stat(home_team_stats, "home_played", 0) > 3:
            home_attack = _get_stat(home_team_stats, "home_avg_for", home_attack)
            home_defense = _get_stat(home_team_stats, "home_avg_against", home_defense)
        if _get_stat(away_team_stats, "away_played", 0) > 3:
            away_attack = _get_stat(away_team_stats, "away_avg_for", away_attack)
            away_defense = _get_stat(away_team_stats, "away_avg_against", away_defense)

        home_lambda = (home_attack * away_defense) / league_avg * home_advantage
        away_lambda = (away_attack * home_defense) / league_avg

    elif home_team_stats:
        home_lambda = _get_stat(home_team_stats, "avg_goals_for", league_avg) * home_advantage
        away_lambda = league_avg

    elif away_team_stats:
        home_lambda = league_avg * home_advantage
        away_lambda = _get_stat(away_team_stats, "avg_goals_for", league_avg)

    else:
        home_lambda = league_avg * home_advantage
        away_lambda = league_avg

    return round(home_lambda, 3), round(away_lambda, 3)


def calibrate_from_odds(odds_1x2: dict, home_advantage: float = 1.15) -> Tuple[float, float]:
    """
    Calibra lambdas de Poisson a partir de cuotas del mercado (1X2).
    Usa las probabilidades implicitas como base y ajusta con ventaja local.
    """
    try:
        p_home_implied = 1 / float(odds_1x2.get("1", 2.0))
        p_draw_implied = 1 / float(odds_1x2.get("X", 3.0))
        p_away_implied = 1 / float(odds_1x2.get("2", 4.0))
    except (ValueError, ZeroDivisionError):
        return 1.4, 1.1  # defaults

    # Normalizar (quitar margen de la casa)
    total = p_home_implied + p_draw_implied + p_away_implied
    if total <= 0:
        return 1.4, 1.1

    p_home = p_home_implied / total
    p_draw = p_draw_implied / total
    p_away = p_away_implied / total

    # Estimar lambdas a partir de probabilidades Poisson
    # Buscar lambda que mejor ajusta las 3 probabilidades
    # Usar la relacion p_home/p_away como ratio de fuerza
    best_err = 999
    best_h, best_a = 1.4, 1.1

    for h_lambda in [i * 0.1 for i in range(5, 40)]:  # 0.5 to 4.0
        for a_lambda in [i * 0.1 for i in range(3, 35)]:  # 0.3 to 3.5
            model = calculate_poisson(h_lambda, a_lambda)
            err = abs(model.home_win_prob - p_home) + abs(model.draw_prob - p_draw) + abs(model.away_win_prob - p_away)
            if err < best_err:
                best_err = err
                best_h = h_lambda
                best_a = a_lambda

    # Aplicar ventaja local
    best_h *= home_advantage

    return round(best_h, 3), round(best_a, 3)


def find_value_bets(model: PoissonModel, odds_data: Dict[str, Dict[str, float]],
                    min_edge: float = 0.03) -> List[ValueBet]:
    """
    Encuentra value bets comparando probabilidades de Poisson vs cuotas reales.
    odds_data: {"bookmaker_name": {"selection": odds}}
    """
    probability_map = {
        "home": model.home_win_prob,
        "draw": model.draw_prob,
        "away": model.away_win_prob,
        "over_15": model.over_15,
        "under_15": 1 - model.over_15,
        "over_25": model.over_25,
        "under_25": 1 - model.over_25,
        "over_35": model.over_35,
        "under_35": 1 - model.over_35,
        "btts_yes": model.btts_prob,
        "btts_no": 1 - model.btts_prob,
    }

    value_bets = []
    seen = set()

    for bookmaker_name, selections in odds_data.items():
        for selection, odds in selections.items():
            key = f"{selection}_{bookmaker_name}"
            if key in seen or odds <= 1:
                continue
            seen.add(key)

            prob = probability_map.get(selection.lower(), 0)
            if prob <= 0:
                continue

            ev = (prob * odds) - 1
            edge = ev * 100

            if ev > min_edge:
                kelly = (prob * odds - 1) / (odds - 1) if odds > 1 else 0

                if ev > 0.15:
                    confidence = "ALTA"
                elif ev > 0.08:
                    confidence = "MEDIA"
                else:
                    confidence = "BAJA"

                value_bets.append(ValueBet(
                    market=selection,
                    selection=selection,
                    odds=odds,
                    probability=round(prob * 100, 1),
                    expected_value=round(ev * 100, 1),
                    edge=round(edge, 1),
                    kelly_fraction=round(kelly * 100, 1),
                    confidence=confidence,
                    bookmaker=bookmaker_name,
                ))

    return sorted(value_bets, key=lambda x: -x.expected_value)


def monte_carlo_simulation(home_lambda: float, away_lambda: float,
                           simulations: int = 10000) -> Dict[str, float]:
    """Simulación Monte Carlo para validar el modelo Poisson."""
    np.random.seed(42)
    home_goals = np.random.poisson(home_lambda, simulations)
    away_goals = np.random.poisson(away_lambda, simulations)

    total = home_goals + away_goals

    return {
        "home_win": round(float(np.mean(home_goals > away_goals)) * 100, 1),
        "draw": round(float(np.mean(home_goals == away_goals)) * 100, 1),
        "away_win": round(float(np.mean(home_goals < away_goals)) * 100, 1),
        "over_25": round(float(np.mean(total > 2.5)) * 100, 1),
        "btts": round(float(np.mean((home_goals > 0) & (away_goals > 0))) * 100, 1),
        "avg_total_goals": round(float(np.mean(total)), 2),
        "avg_home_goals": round(float(np.mean(home_goals)), 2),
        "avg_away_goals": round(float(np.mean(away_goals)), 2),
    }


# ============================================================
# ENHANCED POISSON MODEL
# ============================================================

def calculate_dynamic_home_advantage(home_team_stats: Any, default: float = 1.15) -> float:
    """
    Calcula ventaja local dinámica basada en el historial local del equipo.
    Si el equipo tiene buen rendimiento en casa, la ventaja sube.
    Si es malo en casa, la ventaja baja.
    """
    if not home_team_stats:
        return default

    home_played = _get_stat(home_team_stats, "home_played", 0)
    home_wins = _get_stat(home_team_stats, "wins", 0)  # fallback to total
    home_goals_for = _get_stat(home_team_stats, "home_goals_for", 0)
    home_goals_against = _get_stat(home_team_stats, "home_goals_against", 0)

    if home_played < 3:
        return default

    # Calculate home win rate
    # We approximate from total wins if home_wins not directly available
    total_played = _get_stat(home_team_stats, "played", 1)
    total_wins = _get_stat(home_team_stats, "wins", 0)
    win_rate = total_wins / total_played if total_played > 0 else 0.33

    # Home goals ratio
    home_gf_avg = home_goals_for / home_played if home_played > 0 else 1.3
    home_ga_avg = home_goals_against / home_played if home_played > 0 else 1.1
    home_goal_diff = home_gf_avg - home_ga_avg

    # Dynamic advantage: ranges from 1.05 to 1.25
    if home_goal_diff > 0.8 and win_rate > 0.6:
        advantage = 1.22  # Very strong at home
    elif home_goal_diff > 0.4 and win_rate > 0.5:
        advantage = 1.18  # Strong at home
    elif home_goal_diff > 0:
        advantage = 1.15  # Average home advantage
    elif home_goal_diff > -0.4:
        advantage = 1.10  # Below average at home
    else:
        advantage = 1.05  # Poor at home

    logger.debug(f"Dynamic home advantage: {advantage} (GD/home: {home_goal_diff:.2f}, WR: {win_rate:.2f})")
    return round(advantage, 3)


def calculate_enhanced_poisson(
    home_team_stats: Any,
    away_team_stats: Any,
    league: str = "Premier League",
    home_form: Optional[Dict] = None,
    away_form: Optional[Dict] = None,
    h2h_data: Optional[Dict] = None,
    use_dynamic_home_advantage: bool = True,
) -> Tuple[PoissonModel, Dict[str, Any]]:
    """
    Calcula lambdas de Poisson enhanced combinando:
    1. Base Poisson de estadísticas de la temporada
    2. Multiplicador de forma reciente (últimos 5 partidos pesados 2x)
    3. Factor H2H (historial de enfrentamientos)
    4. Ventaja local dinámica (basada en récord local del equipo)

    Retorna: (PoissonModel, factors_dict)
    """
    # Step 1: Base lambdas from season stats
    if use_dynamic_home_advantage:
        home_advantage = calculate_dynamic_home_advantage(home_team_stats)
    else:
        home_advantage = 1.15

    base_home_lambda, base_away_lambda = calibrate_lambdas(
        home_team_stats, away_team_stats, league, home_advantage
    )

    logger.debug(f"Base lambdas: home={base_home_lambda}, away={base_away_lambda} (HA={home_advantage})")

    # Step 2: Form multipliers
    from form_scraper import calculate_form_factors
    home_form_factors = calculate_form_factors(home_form)
    away_form_factors = calculate_form_factors(away_form)

    home_form_mult = home_form_factors["form_multiplier"]
    away_form_mult = away_form_factors["form_multiplier"]

    logger.debug(f"Form multipliers: home={home_form_mult} ({home_form_factors['form_quality']}), "
                 f"away={away_form_mult} ({away_form_factors['form_quality']})")

    # Step 3: H2H factor
    from head2head import calculate_h2h_factor
    if h2h_data:
        h2h_factors = calculate_h2h_factor(h2h_data, is_home_team=True)
        h2h_factor = h2h_factors["h2h_factor"]
    else:
        h2h_factors = {"h2h_factor": 1.0, "h2h_confidence": "sin datos", "h2h_record": "N/A"}
        h2h_factor = 1.0

    logger.debug(f"H2H factor: {h2h_factor}")

    # Step 4: Apply all factors
    # enhanced_home_lambda = base_home_lambda * form_multiplier_home * h2h_factor * home_advantage
    # Note: home_advantage is already baked into base_home_lambda via calibrate_lambdas,
    # so we don't multiply it again unless we want extra boost
    enhanced_home_lambda = base_home_lambda * home_form_mult * h2h_factor
    enhanced_away_lambda = base_away_lambda * away_form_mult * (1.0 / h2h_factor if h2h_factor != 0 else 1.0)

    # Clamp lambdas to reasonable range (0.3 - 4.5)
    enhanced_home_lambda = max(0.3, min(4.5, enhanced_home_lambda))
    enhanced_away_lambda = max(0.3, min(4.5, enhanced_away_lambda))

    logger.debug(f"Enhanced lambdas: home={enhanced_home_lambda:.3f}, away={enhanced_away_lambda:.3f}")

    # Calculate probabilities with enhanced lambdas
    model = calculate_poisson(enhanced_home_lambda, enhanced_away_lambda)

    # Build factors summary
    factors = {
        "base_home_lambda": base_home_lambda,
        "base_away_lambda": base_away_lambda,
        "enhanced_home_lambda": round(enhanced_home_lambda, 3),
        "enhanced_away_lambda": round(enhanced_away_lambda, 3),
        "home_advantage": home_advantage,
        "home_form": {
            "multiplier": home_form_mult,
            "string": home_form_factors.get("form_string", ""),
            "quality": home_form_factors.get("form_quality", "sin datos"),
            "win_rate": home_form_factors.get("win_rate_last_5", 0),
            "streak": home_form_factors.get("streak", "none"),
        },
        "away_form": {
            "multiplier": away_form_mult,
            "string": away_form_factors.get("form_string", ""),
            "quality": away_form_factors.get("form_quality", "sin datos"),
            "win_rate": away_form_factors.get("win_rate_last_5", 0),
            "streak": away_form_factors.get("streak", "none"),
        },
        "h2h": h2h_factors,
        "adjustments": {
            "form_effect_home": round((home_form_mult - 1.0) * 100, 1),
            "form_effect_away": round((away_form_mult - 1.0) * 100, 1),
            "h2h_effect": round((h2h_factor - 1.0) * 100, 1),
        },
    }

    return model, factors
