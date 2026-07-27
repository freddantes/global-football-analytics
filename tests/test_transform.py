import pytest
import pandas as pd
from src.transform import process_standings, process_matches

# =====================================================================
# TESTES DE CLASSIFICAÇÃO
# =====================================================================
def test_process_standings_calculation():
    mock_data = {
        'standings': [{
            'table': [{
                'position': 1,
                'team': {'name': 'Time A'},
                'playedGames': 10,
                'won': 5,
                'draw': 3,
                'lost': 2,
                'goalsFor': 20,
                'goalsAgainst': 10, 
                'goalDifference': 10,
                'points': 18
            }]
        }]
    }
    df = process_standings(mock_data)
    assert df['goals_per_game'].iloc[0] == 2.0
    assert df['points_pct'].iloc[0] == 0.6
    assert 'team_name' in df.columns

def test_process_standings_empty():
    assert process_standings({'standings': []}) is None

# =====================================================================
# TESTES DE PARTIDAS (MATCHES) - NOVO!
# =====================================================================
def test_process_matches_calculations_and_future_games():
    """
    Simula uma partida já finalizada (com placar) e uma partida futura (com gols = None)
    para garantir que a Feature Engineering calcula certo e não quebra com nulos.
    """
    mock_matches_data = {
        'matches': [
            {
                # JOGO 1: Finalizado (Mandante venceu de 3x1)
                "id": 1001,
                "utcDate": "2026-07-20T19:00:00Z",
                "status": "FINISHED",
                "matchday": 1,
                "homeTeam": {"name": "Arsenal"},
                "awayTeam": {"name": "Chelsea"},
                "score": {
                    "winner": "HOME_TEAM",
                    "fullTime": {"home": 3, "away": 1}
                }
            },
            {
                # JOGO 2: Futuro (Placar vazio/None)
                "id": 1002,
                "utcDate": "2026-08-15T15:00:00Z",
                "status": "SCHEDULED",
                "matchday": 2,
                "homeTeam": {"name": "Liverpool"},
                "awayTeam": {"name": "Everton"},
                "score": {
                    "winner": None,
                    "fullTime": {"home": None, "away": None}
                }
            }
        ]
    }

    df = process_matches(mock_matches_data)

    # Verificações do Jogo 1 (Finalizado)
    assert df.loc[df['match_id'] == 1001, 'total_goals'].iloc[0] == 4.0
    assert df.loc[df['match_id'] == 1001, 'goal_difference'].iloc[0] == 2.0
    assert df.loc[df['match_id'] == 1001, 'home_win'].iloc[0] == 1
    assert df.loc[df['match_id'] == 1001, 'away_win'].iloc[0] == 0

    # Verificações do Jogo 2 (Futuro - Não pode ter quebrado o script!)
    assert pd.isna(df.loc[df['match_id'] == 1002, 'total_goals'].iloc[0])
    assert df.loc[df['match_id'] == 1002, 'home_win'].iloc[0] == 0
    assert df.loc[df['match_id'] == 1002, 'status'].iloc[0] == "SCHEDULED"

def test_process_matches_empty():
    assert process_matches({'matches': []}) is None