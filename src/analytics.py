import os
import math
import numpy as np
import duckdb
import pandas as pd
from src.logging_config import logger

# =====================================================================
# 1. CONSULTAS SQL VIA DUCKDB
# =====================================================================

def query_hive_standings(league_code: str = None) -> pd.DataFrame:
    """Consulta as partições Hive da tabela de classificação."""
    parquet_path = os.path.join("data", "gold", "standings", "**", "*.parquet")
    query = f"SELECT * FROM read_parquet('{parquet_path}', hive_partitioning=1, union_by_name=True)"
    
    if league_code:
        query += f" WHERE league_code = '{league_code.upper()}'"
    query += " ORDER BY points DESC, goalDifference DESC"
    
    try:
        logger.info(f"Executando SQL DuckDB para standings (Liga: {league_code or 'Todas'})")
        return duckdb.query(query).to_df()
    except Exception as e:
        logger.error(f"Erro DuckDB (Standings): {e}")
        return None

def query_hive_matches(league_code: str = None) -> pd.DataFrame:
    """Consulta o histórico de partidas (matches) particionadas no Hive."""
    parquet_path = os.path.join("data", "gold", "matches", "**", "*.parquet")
    query = f"SELECT * FROM read_parquet('{parquet_path}', hive_partitioning=1, union_by_name=True)"
    
    if league_code:
        query += f" WHERE league_code = '{league_code.upper()}'"
    query += " ORDER BY utc_date DESC"
    
    try:
        logger.info(f"Executando SQL DuckDB para matches (Liga: {league_code or 'Todas'})")
        return duckdb.query(query).to_df()
    except Exception as e:
        logger.error(f"Erro DuckDB (Matches): {e}")
        return None

# =====================================================================
# 2. MOTOR ESTATÍSTICO DE POISSON (Com Decaimento Temporal)
# =====================================================================

def _calculate_poisson_probability(lam: float, k: int) -> float:
    """Calcula a probabilidade exata (Poisson) de ocorrer k eventos com média lam."""
    if lam <= 0 or math.isnan(lam):
        return 0.0
    return ((lam ** k) * math.exp(-lam)) / math.factorial(k)

# NOVA ASSINATURA: Adicionamos o parâmetro opcional 'match_date'
def get_match_predictions(league_code: str, home_team: str, away_team: str, match_date: str = None) -> dict:
    """Gera probabilidades de Vitória, Empate, Derrota e Over 2.5 Gols aplicando Time Decay."""
    df = query_hive_matches(league_code)
    
    if df is None or df.empty:
        return None

    # Filtra jogos válidos e DROP NA: Blindagem contra o veneno do 'nan'
    df_finished = df[df['status'].isin(['FINISHED', 'IN_PLAY'])].copy()
    df_finished = df_finished.dropna(subset=['home_goals', 'away_goals'])
    
    # -----------------------------------------------------------------
    # PROTEÇÃO CONTRA VAZAMENTO DE DADOS (TIME TRAVEL)
    # -----------------------------------------------------------------
    df_finished['utc_date'] = pd.to_datetime(df_finished['utc_date'])
    
    # Se uma data de jogo for informada (Backtest), cortamos o passado estritamente ANTES desse jogo
    if match_date:
        current_match_date = pd.to_datetime(match_date)
        df_finished = df_finished[df_finished['utc_date'] < current_match_date]
        data_referencia = current_match_date
    else:
        # Se for o painel ao vivo (Streamlit), a referência é o jogo mais recente da base
        data_referencia = df_finished['utc_date'].max()
    
    # Valida se sobraram jogos suficientes no passado para o cálculo
    if df_finished.empty or len(df_finished) < 20:
        return None

    # -----------------------------------------------------------------
    # INÍCIO DO CÁLCULO DE DECAIMENTO TEMPORAL (TIME DECAY)
    # -----------------------------------------------------------------
    df_finished['dias_atras'] = (data_referencia - df_finished['utc_date']).dt.days
    
    # Evita dias negativos em caso de dados inconsistentes
    df_finished['dias_atras'] = df_finished['dias_atras'].clip(lower=0)
    
    df_finished['peso'] = np.exp(-df_finished['dias_atras'] / 365)

    def media_ponderada(dataframe, coluna):
        """Função auxiliar para calcular a média usando a coluna 'peso'."""
        if dataframe.empty or dataframe['peso'].sum() == 0: 
            return 0.0
        # O NumPy calcula a média perfeitamente agora, pois garantimos que não há NaNs
        return np.average(dataframe[coluna], weights=dataframe['peso'])
    # -----------------------------------------------------------------

    # Médias Globais da Liga Ponderadas
    league_avg_home_goals = media_ponderada(df_finished, 'home_goals')
    league_avg_away_goals = media_ponderada(df_finished, 'away_goals')

    # Força de Ataque/Defesa do Mandante
    home_stats = df_finished[df_finished['home_team'] == home_team]
    if home_stats.empty: return None
    home_scored_avg = media_ponderada(home_stats, 'home_goals')
    home_conceded_avg = media_ponderada(home_stats, 'away_goals')

    # Força de Ataque/Defesa do Visitante
    away_stats = df_finished[df_finished['away_team'] == away_team]
    if away_stats.empty: return None
    away_scored_avg = media_ponderada(away_stats, 'away_goals')
    away_conceded_avg = media_ponderada(away_stats, 'home_goals')

    # Prevenção de divisão por zero
    if league_avg_home_goals == 0 or league_avg_away_goals == 0: return None

    # Cálculo de Força Relativa 
    home_attack_strength = home_scored_avg / league_avg_home_goals
    away_defense_strength = away_conceded_avg / league_avg_home_goals
    
    away_attack_strength = away_scored_avg / league_avg_away_goals
    home_defense_strength = home_conceded_avg / league_avg_away_goals

    # O Lambda (Expected Goals - xG)
    home_expected_goals = home_attack_strength * away_defense_strength * league_avg_home_goals
    away_expected_goals = away_attack_strength * home_defense_strength * league_avg_away_goals

    # Matriz de Probabilidades Poisson
    prob_home_win = 0.0
    prob_away_win = 0.0
    prob_draw = 0.0
    prob_over_2_5 = 0.0

    for i in range(6): 
        for j in range(6): 
            prob_score = _calculate_poisson_probability(home_expected_goals, i) * _calculate_poisson_probability(away_expected_goals, j)
            
            if i > j:
                prob_home_win += prob_score
            elif i < j:
                prob_away_win += prob_score
            else:
                prob_draw += prob_score
                
            if (i + j) > 2.5: 
                prob_over_2_5 += prob_score

    # Normalização
    total_prob = prob_home_win + prob_away_win + prob_draw
    if total_prob == 0: return None
    
    return {
        "home_xg": round(home_expected_goals, 2),
        "away_xg": round(away_expected_goals, 2),
        "home_win_pct": round((prob_home_win / total_prob) * 100, 1),
        "draw_pct": round((prob_draw / total_prob) * 100, 1),
        "away_win_pct": round((prob_away_win / total_prob) * 100, 1),
        "over_2_5_pct": round(prob_over_2_5 * 100, 1)
    }