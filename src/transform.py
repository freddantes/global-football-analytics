# src/transform.py
import duckdb
import pandas as pd
from src.schemas import StandingRowSchema, MatchRowSchema
from src.logging_config import logger

# =====================================================================
# 1. PROCESSAMENTO DE TABELA DE CLASSIFICAÇÃO (Standings com DuckDB)
# =====================================================================
def process_standings(raw_data: dict) -> pd.DataFrame:
    try:
        standings = raw_data.get('standings')
        if not standings or len(standings) == 0:
            logger.warning("Nenhum dado de classificação encontrado no payload.")
            return None

        standings_list = standings[0].get('table', [])
        if not standings_list:
            return None
        
        processed_data = []
        for row in standings_list:
            item = {
                "position": row.get("position"),
                "team": row.get("team", {}).get("name"),
                "crest": row.get("team", {}).get("crest"),
                "points": row.get("points"),
                "playedGames": row.get("playedGames"),
                "won": row.get("won"),
                "draw": row.get("draw"),
                "lost": row.get("lost"),
                "goalsFor": row.get("goalsFor"),
                "goalsAgainst": row.get("goalsAgainst"),
                "goalDifference": row.get("goalDifference")
            }
            validated_row = StandingRowSchema(**item)
            processed_data.append(validated_row.model_dump())
            
        df_temp = pd.DataFrame(processed_data)
        if 'team' in df_temp.columns:
            df_temp = df_temp.rename(columns={'team': 'team_name'})

        # Processamento analítico via SQL com DuckDB em memória
        con = duckdb.connect(database=':memory:')
        
        query = """
        SELECT 
            *,
            CASE WHEN playedGames > 0 THEN CAST(goalsFor AS DOUBLE) / playedGames ELSE 0.0 END AS goals_per_game,
            CASE WHEN playedGames > 0 THEN CAST(points AS DOUBLE) / (playedGames * 3) ELSE 0.0 END AS points_pct
        FROM df_temp
        """
        
        df = con.execute(query).fetchdf()
        con.close()

        logger.info("Contrato de dados de classificação validado e transformado via DuckDB com sucesso.")
        return df

    except Exception as e:
        logger.error(f"Falha na validação ou transformação de standings: {e}")
        raise e


# =====================================================================
# 2. PROCESSAMENTO DE PARTIDAS (Matches com DuckDB)
# =====================================================================
def process_matches(raw_data: dict) -> pd.DataFrame:
    """
    Transforma o JSON bruto de partidas em um DataFrame analítico.
    Achatamos os dados aninhados e criamos variáveis quantitativas usando DuckDB SQL.
    """
    try:
        matches = raw_data.get('matches', [])
        if not matches:
            logger.warning("Nenhum jogo encontrado no payload da API.")
            return None

        processed_data = []
        for row in matches:
            score = row.get("score", {})
            full_time = score.get("fullTime", {})
            home_dict = row.get("homeTeam", {})
            away_dict = row.get("awayTeam", {})
            
            item = {
                "match_id": row.get("id"),
                "utc_date": row.get("utcDate"),
                "status": row.get("status"),
                "matchday": row.get("matchday"),
                "home_team": home_dict.get("name") or "A Definir",
                "away_team": away_dict.get("name") or "A Definir",
                "home_goals": full_time.get("home"),
                "away_goals": full_time.get("away"),
                "winner": score.get("winner")
            }
            
            validated_row = MatchRowSchema(**item)
            processed_data.append(validated_row.model_dump())

        df_temp = pd.DataFrame(processed_data)

        # Processamento de Feature Engineering via SQL com DuckDB em memória
        con = duckdb.connect(database=':memory:')

        query = """
        SELECT 
            match_id,
            CAST(utc_date AS TIMESTAMP) AS utc_date,
            status,
            matchday,
            home_team,
            away_team,
            home_goals,
            away_goals,
            winner,
            (home_goals + away_goals) AS total_goals,
            (home_goals - away_goals) AS goal_difference,
            CASE WHEN winner = 'HOME_TEAM' THEN 1 ELSE 0 END AS home_win,
            CASE WHEN winner = 'AWAY_TEAM' THEN 1 ELSE 0 END AS away_win,
            CASE WHEN winner = 'DRAW' THEN 1 ELSE 0 END AS draw
        FROM df_temp
        """

        df = con.execute(query).fetchdf()
        con.close()

        logger.info(f"Contrato de partidas validado via DuckDB. {len(df)} jogos processados com sucesso.")
        return df

    except Exception as e:
        logger.error(f"Falha na validação ou transformação de partidas (matches): {e}")
        raise e