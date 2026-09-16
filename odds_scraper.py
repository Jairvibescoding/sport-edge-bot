import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OddsScraper:
    """Scraper de cuotas de casas de apuestas."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_odds_from_api(self, sport: str = "soccer") -> List[Dict[str, Any]]:
        """
        Obtiene cuotas de una API pública (The Odds API - gratis tier).
        Registrarse en https://the-odds-api.com para API key gratuita.
        """
        api_key = os.getenv("ODDS_API_KEY", "")
        
        if not api_key:
            logger.warning("ODDS_API_KEY no configurada. Usando datos de ejemplo.")
            return self._get_sample_odds()
        
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
            params = {
                'apiKey': api_key,
                'regions': 'us,eu',
                'markets': 'h2h,totals',
                'oddsFormat': 'decimal'
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error obteniendo cuotas: {e}")
            return self._get_sample_odds()
    
    def _get_sample_odds(self) -> List[Dict[str, Any]]:
        """Cuotas de ejemplo para demostración."""
        return [
            {
                'id': 'example_1',
                'sport_key': 'soccer',
                'commence_time': datetime.now().isoformat(),
                'home_team': 'Real Madrid',
                'away_team': 'Barcelona',
                'bookmakers': [
                    {
                        'key': '1xbet',
                        'title': '1xBet',
                        'markets': [
                            {
                                'key': 'h2h',
                                'outcomes': [
                                    {'name': 'Real Madrid', 'price': 1.85},
                                    {'name': 'Draw', 'price': 3.40},
                                    {'name': 'Barcelona', 'price': 4.20}
                                ]
                            },
                            {
                                'key': 'totals',
                                'outcomes': [
                                    {'name': 'Over', 'price': 1.90},
                                    {'name': 'Under', 'price': 1.90}
                                ]
                            }
                        ]
                    },
                    {
                        'key': 'bet365',
                        'title': 'Bet365',
                        'markets': [
                            {
                                'key': 'h2h',
                                'outcomes': [
                                    {'name': 'Real Madrid', 'price': 1.80},
                                    {'name': 'Draw', 'price': 3.50},
                                    {'name': 'Barcelona', 'price': 4.00}
                                ]
                            },
                            {
                                'key': 'totals',
                                'outcomes': [
                                    {'name': 'Over', 'price': 1.85},
                                    {'name': 'Under', 'price': 1.95}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                'id': 'example_2',
                'sport_key': 'soccer',
                'commence_time': datetime.now().isoformat(),
                'home_team': 'Manchester United',
                'away_team': 'Liverpool',
                'bookmakers': [
                    {
                        'key': '1xbet',
                        'title': '1xBet',
                        'markets': [
                            {
                                'key': 'h2h',
                                'outcomes': [
                                    {'name': 'Manchester United', 'price': 2.80},
                                    {'name': 'Draw', 'price': 3.20},
                                    {'name': 'Liverpool', 'price': 2.50}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    
    def compare_odds(self, odds_data: List[Dict]) -> List[Dict]:
        """Compara cuotas entre diferentes casas de apuestas."""
        comparisons = []
        
        for match in odds_data:
            if len(match.get('bookmakers', [])) < 2:
                continue
            
            comparison = {
                'match': f"{match['home_team']} vs {match['away_team']}",
                'commence_time': match.get('commence_time'),
                'markets': {}
            }
            
            for bookmaker in match['bookmakers']:
                for market in bookmaker.get('markets', []):
                    market_key = market['key']
                    
                    if market_key not in comparison['markets']:
                        comparison['markets'][market_key] = {
                            'bookmakers': {},
                            'best_odds': {}
                        }
                    
                    comparison['markets'][market_key]['bookmakers'][bookmaker['title']] = {}
                    
                    for outcome in market['outcomes']:
                        name = outcome['name']
                        price = outcome['price']
                        
                        comparison['markets'][market_key]['bookmakers'][bookmaker['title']][name] = price
                        
                        if name not in comparison['markets'][market_key]['best_odds'] or \
                           price > comparison['markets'][market_key]['best_odds'][name]['price']:
                            comparison['markets'][market_key]['best_odds'][name] = {
                                'price': price,
                                'bookmaker': bookmaker['title']
                            }
            
            comparisons.append(comparison)
        
        return comparisons


def get_odds_scraper() -> OddsScraper:
    """Obtiene una instancia del scraper."""
    return OddsScraper()
