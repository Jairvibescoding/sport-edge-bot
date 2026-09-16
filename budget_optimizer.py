"""
Optimizador de presupuesto de apuestas.
Dado un bankroll y una lista de value bets, calcula cuánto apostar en cada una.
Usa Kelly Criterion modificado (fracción conservadora) para maximizar crecimiento
minimizando riesgo de quiebra.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import math


@dataclass
class BetRecommendation:
    match: str
    market: str
    selection: str
    odds: float
    probability: float
    edge: float
    kelly_full: float
    kelly_fraction: float
    stake: float
    potential_profit: float
    confidence: str
    bookmaker: str
    ev: float


@dataclass
class BudgetPlan:
    bankroll: float
    kelly_multiplier: float
    max_single_bet_pct: float
    max_total_exposure_pct: float
    total_staked: float
    total_potential_profit: float
    num_bets: int
    risk_level: str
    bets: List[BetRecommendation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def kelly_criterion(probability: float, odds: float) -> float:
    """Kelly fraction completa: f* = (bp - q) / b donde b = odds-1, p = prob, q = 1-p"""
    if odds <= 1 or probability <= 0:
        return 0
    b = odds - 1
    p = probability
    q = 1 - p
    return max(0, (b * p - q) / b)


def optimize_budget(bankroll: float,
                     value_bets: List[Dict[str, Any]],
                     kelly_multiplier: float = 0.25,
                     max_single_bet_pct: float = 0.10,
                     max_total_exposure_pct: float = 0.30,
                     min_edge: float = 3.0,
                     league_avg_goals: float = 2.8) -> BudgetPlan:
    """
    Optimiza el bankroll entre múltiples value bets.

    Args:
        bankroll: Presupuesto total disponible
        value_bets: Lista de value bets con sus datos
        kelly_multiplier: Fracción de Kelly a usar (0.25 = quarter Kelly, más conservador)
        max_single_bet_pct: Máximo % del bankroll en una sola apuesta
        max_total_exposure_pct: Máximo % del bankroll expuesto en total
        min_edge: Edge mínimo para incluir una apuesta (en %)
    """

    if bankroll <= 0:
        return BudgetPlan(
            bankroll=bankroll,
            kelly_multiplier=kelly_multiplier,
            max_single_bet_pct=max_single_bet_pct,
            max_total_exposure_pct=max_total_exposure_pct,
            total_staked=0,
            total_potential_profit=0,
            num_bets=0,
            risk_level="N/A",
            warnings=["Bankroll debe ser mayor a 0"]
        )

    if bankroll < 10:
        risk_level = "CRÍTICO"
    elif bankroll < 50:
        risk_level = "MUY ALTO"
    elif bankroll < 200:
        risk_level = "ALTO"
    elif bankroll < 1000:
        risk_level = "MODERADO"
    else:
        risk_level = "BAJO"

    filtered_bets = [b for b in value_bets if b.get("edge", 0) >= min_edge]
    filtered_bets = sorted(filtered_bets, key=lambda x: -x.get("edge", 0))

    max_single_bet = bankroll * max_single_bet_pct
    max_total_exposure = bankroll * max_total_exposure_pct

    recommendations = []
    total_staked = 0
    warnings = []

    for bet in filtered_bets:
        prob = bet.get("probability", 0) / 100
        odds = bet.get("odds", 1)
        edge = bet.get("edge", 0)

        kelly_full = kelly_criterion(prob, odds)
        kelly_adj = kelly_full * kelly_multiplier

        stake = bankroll * kelly_adj

        if stake < 0.50:
            continue

        if total_staked + stake > max_total_exposure:
            remaining = max_total_exposure - total_staked
            if remaining < 0.50:
                warnings.append(f"Límite de exposición alcanzado ({max_total_exposure_pct*100:.0f}%)")
                break
            stake = remaining

        if stake > max_single_bet:
            stake = max_single_bet

        stake = round(stake, 2)
        potential_profit = round(stake * (odds - 1), 2)

        if edge > 15:
            conf = "ALTA"
        elif edge > 8:
            conf = "MEDIA"
        else:
            conf = "BAJA"

        match_name = bet.get("match", "N/A")
        if match_name == "N/A" and "home_team" in bet:
            match_name = f"{bet['home_team']} vs {bet['away_team']}"

        recommendations.append(BetRecommendation(
            match=match_name,
            market=bet.get("market", "N/A"),
            selection=bet.get("selection", bet.get("market", "N/A")),
            odds=odds,
            probability=prob * 100,
            edge=edge,
            kelly_full=round(kelly_full * 100, 1),
            kelly_fraction=round(kelly_adj * 100, 1),
            stake=stake,
            potential_profit=potential_profit,
            confidence=conf,
            bookmaker=bet.get("bookmaker", "N/A"),
            ev=bet.get("expected_value", edge),
        ))

        total_staked += stake

    total_staked = round(total_staked, 2)
    total_potential_profit = round(sum(b.potential_profit for b in recommendations), 2)

    if total_staked > bankroll:
        warnings.append("¡Exposición total supera el bankroll!")

    pct_exposed = (total_staked / bankroll * 100) if bankroll > 0 else 0

    if pct_exposed < 5:
        warnings.append("Exposición baja - pocas oportunidades de valor detectadas")

    if len(recommendations) > 5:
        warnings.append("Muchas apuestas simultáneas - diversificar riesgo")

    return BudgetPlan(
        bankroll=bankroll,
        kelly_multiplier=kelly_multiplier,
        max_single_bet_pct=max_single_bet_pct,
        max_total_exposure_pct=max_total_exposure_pct,
        total_staked=total_staked,
        total_potential_profit=total_potential_profit,
        num_bets=len(recommendations),
        risk_level=risk_level,
        bets=recommendations,
        warnings=warnings,
    )


def quick_bet_advice(bankroll: float, odds: float, probability: float,
                      match_name: str = "N/A", market: str = "N/A",
                      selection: str = "N/A", bookmaker: str = "N/A") -> Dict:
    """Análisis rápido de una sola apuesta."""
    kelly = kelly_criterion(probability / 100, odds)
    kelly_adj = kelly * 0.25  # quarter Kelly

    stake = round(bankroll * kelly_adj, 2)
    max_bet = round(bankroll * 0.10, 2)

    if stake > max_bet:
        stake = max_bet

    ev = (probability / 100 * odds - 1) * 100
    edge = ev

    if stake < 0.50:
        recommendation = "NO APOSTAR - stake mínimo muy bajo"
    elif ev > 15:
        recommendation = "FUERTE - valor significativo"
    elif ev > 8:
        recommendation = "MEDIA - valor claro"
    elif ev > 3:
        recommendation = "BAJA - valor marginal"
    else:
        recommendation = "NO APOSTAR - sin valor suficiente"

    return {
        "match": match_name,
        "market": market,
        "selection": selection,
        "odds": odds,
        "probability": probability,
        "edge": round(edge, 1),
        "ev": round(ev, 1),
        "kelly_full": round(kelly * 100, 1),
        "kelly_adj": round(kelly_adj * 100, 1),
        "recommended_stake": stake,
        "max_allowed_stake": max_bet,
        "potential_profit": round(stake * (odds - 1), 2),
        "bankroll_used_pct": round(stake / bankroll * 100, 1) if bankroll > 0 else 0,
        "recommendation": recommendation,
        "bookmaker": bookmaker,
    }
