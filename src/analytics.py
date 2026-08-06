import os
import math
import duckdb
import pandas as pd
from src.logging_config import logger

# =====================================================================
# 1. CONSULTAS SQL VIA DUCKDB (Corrigidas para Múltiplos Schemas)
# =====================================================================

def query_hive_standings(league_code: str = None) -> pd.DataFrame:
    """Consulta as partições Hive da tabela de classificação."""
    parquet_path = os.path.join("data", "gold", "standings", "**", "*.parquet")
    
    # Adicionado o union_by_name=True para resolver conflitos de schema entre partições vazias e preenchidas
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
    
    # Adicionado o union_by_name=True
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
# 2. MOTOR ESTATÍSTICO DE POISSON (NOVO! - ETAPA 7)
# =====================================================================

def _calculate_poisson_probability(lam: float, k: int) -> float:
    """
    Função matemática auxiliar (privada).
    Calcula a probabilidade exata de um time marcar 'k' gols, 
    sabendo que a sua média esperada é 'lam' (Lambda).
    """
    if lam <= 0:
        return 0.0
    return ((lam ** k) * math.exp(-lam)) / math.factorial(k)

def get_match_predictions(league_code: str, home_team: str, away_team: str) -> dict:
    """
    Consome o histórico via DuckDB e aplica modelagem quantitativa para gerar 
    probabilidades de Vitória, Empate, Derrota e Over 2.5 Gols.
    """
    # Usamos a sua própria função otimizada para trazer os dados da liga!
    df = query_hive_matches(league_code)
    
    if df is None or df.empty:
        return None

    # Separamos apenas os jogos que já terminaram para calcular médias reais
    df_finished = df[df['status'].isin(['FINISHED', 'IN_PLAY'])]
    
    if df_finished.empty or len(df_finished) < 20:
        return None # Histórico insuficiente para uma amostragem estatística segura

    # 1. Médias Globais da Liga (Quantos gols mandantes e visitantes marcam em média no campeonato?)
    league_avg_home_goals = df_finished['home_goals'].mean()
    league_avg_away_goals = df_finished['away_goals'].mean()

    # 2. Força de Ataque/Defesa do Mandante (Jogando em Casa)
    home_stats = df_finished[df_finished['home_team'] == home_team]
    if home_stats.empty: return None
    home_scored_avg = home_stats['home_goals'].mean()
    home_conceded_avg = home_stats['away_goals'].mean()

    # 3. Força de Ataque/Defesa do Visitante (Jogando Fora)
    away_stats = df_finished[df_finished['away_team'] == away_team]
    if away_stats.empty: return None
    away_scored_avg = away_stats['away_goals'].mean()
    away_conceded_avg = away_stats['home_goals'].mean()

    # 4. Cálculo de Força Relativa 
    # (Se o time marca mais que a média da liga, a força é > 1. Se marca menos, < 1)
    home_attack_strength = home_scored_avg / league_avg_home_goals
    away_defense_strength = away_conceded_avg / league_avg_home_goals
    
    away_attack_strength = away_scored_avg / league_avg_away_goals
    home_defense_strength = home_conceded_avg / league_avg_away_goals

    # 5. O Lambda (Gols Esperados ou "xG" para a partida específica)
    home_expected_goals = home_attack_strength * away_defense_strength * league_avg_home_goals
    away_expected_goals = away_attack_strength * home_defense_strength * league_avg_away_goals

    # 6. Criação da Matriz de Probabilidades (Placares de 0x0 até 5x5)
    prob_home_win = 0.0
    prob_away_win = 0.0
    prob_draw = 0.0
    prob_over_2_5 = 0.0

    # O laço testa todas as combinações de gols até 5.
    for i in range(6): # Mandante faz 0, 1, 2, 3, 4 ou 5 gols
        for j in range(6): # Visitante faz 0, 1, 2, 3, 4 ou 5 gols
            prob_score = _calculate_poisson_probability(home_expected_goals, i) * _calculate_poisson_probability(away_expected_goals, j)
            
            if i > j:
                prob_home_win += prob_score
            elif i < j:
                prob_away_win += prob_score
            else:
                prob_draw += prob_score
                
            if (i + j) > 2.5: # 3 gols ou mais no total
                prob_over_2_5 += prob_score

    # Normalizamos para garantir que a soma das 3 colunas dê 100%
    total_prob = prob_home_win + prob_away_win + prob_draw
    
    return {
        "home_xg": round(home_expected_goals, 2),
        "away_xg": round(away_expected_goals, 2),
        "home_win_pct": round((prob_home_win / total_prob) * 100, 1),
        "draw_pct": round((prob_draw / total_prob) * 100, 1),
        "away_win_pct": round((prob_away_win / total_prob) * 100, 1),
        "over_2_5_pct": round(prob_over_2_5 * 100, 1)
    }