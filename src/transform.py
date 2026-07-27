import pandas as pd
from src.schemas import StandingRowSchema, MatchRowSchema
from src.logging_config import logger

# =====================================================================
# 1. PROCESSAMENTO DE TABELA DE CLASSIFICAÇÃO (Standings)
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
            
        df = pd.DataFrame(processed_data)
        
        if 'team' in df.columns:
            df = df.rename(columns={'team': 'team_name'})
        
        if 'playedGames' in df.columns and 'goalsFor' in df.columns:
            df['goals_per_game'] = df.apply(
                lambda x: x['goalsFor'] / x['playedGames'] if x['playedGames'] > 0 else 0.0, 
                axis=1
            )
            
        if 'playedGames' in df.columns and 'points' in df.columns:
            df['points_pct'] = df.apply(
                lambda x: x['points'] / (x['playedGames'] * 3) if x['playedGames'] > 0 else 0.0, 
                axis=1
            )

        logger.info("Contrato de dados de classificação validado com sucesso.")
        return df

    except Exception as e:
        logger.error(f"Falha na validação ou transformação de standings: {e}")
        raise e


# =====================================================================
# 2. PROCESSAMENTO DE PARTIDAS (Matches) - NOVO!
# =====================================================================
def process_matches(raw_data: dict) -> pd.DataFrame:
    """
    Transforma o JSON bruto de partidas em um DataFrame analítico.
    Achatamos os dados aninhados e criamos variáveis quantitativas (Feature Engineering).
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
            
            # Extraímos os dicionários dos times com segurança
            home_dict = row.get("homeTeam", {})
            away_dict = row.get("awayTeam", {})
            
            item = {
                "match_id": row.get("id"),
                "utc_date": row.get("utcDate"),
                "status": row.get("status"),
                "matchday": row.get("matchday"),
                # O operador 'or' garante que se get("name") retornar None ou string vazia,
                # o Python assumirá automaticamente o texto "A Definir"
                "home_team": home_dict.get("name") or "A Definir",
                "away_team": away_dict.get("name") or "A Definir",
                "home_goals": full_time.get("home"),
                "away_goals": full_time.get("away"),
                "winner": score.get("winner")
            }
            
            # Validação linha a linha pelo Pydantic (permite None para jogos futuros)
            validated_row = MatchRowSchema(**item)
            processed_data.append(validated_row.model_dump())

        df = pd.DataFrame(processed_data)

        # -----------------------------------------------------------------
        # ENGENHARIA DE ATRIBUTOS (Feature Engineering para Ciência de Dados)
        # -----------------------------------------------------------------
        # 1. Converte a data texto de ISO 8601 para tipo Datetime real do Pandas
        df['utc_date'] = pd.to_datetime(df['utc_date'], errors='coerce')

        # 2. Total de gols no jogo (se o jogo for futuro, resultará em NaN automaticamente)
        df['total_goals'] = df['home_goals'] + df['away_goals']
        df['goal_difference'] = df['home_goals'] - df['away_goals']

        # 3. Variáveis Dummy (0 ou 1) para modelagem quantitativa de apostas / prop bets
        # Exemplo: Se winner == 'HOME_TEAM', home_win vira 1, senão vira 0.
        df['home_win'] = (df['winner'] == 'HOME_TEAM').astype(int)
        df['away_win'] = (df['winner'] == 'AWAY_TEAM').astype(int)
        df['draw'] = (df['winner'] == 'DRAW').astype(int)

        logger.info(f"Contrato de partidas validado. {len(df)} jogos processados com sucesso.")
        return df

    except Exception as e:
        logger.error(f"Falha na validação ou transformação de partidas (matches): {e}")
        raise e