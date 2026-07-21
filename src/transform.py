import pandas as pd
from src.schemas import StandingRowSchema
from src.logging_config import logger

def process_standings(raw_data: dict) -> pd.DataFrame:
    try:
        # Verifica se os dados de standings estão vazios ou ausentes
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
            
            # Validação via Pydantic por linha (Contrato de Dados)
            validated_row = StandingRowSchema(**item)
            processed_data.append(validated_row.model_dump())
            
        df = pd.DataFrame(processed_data)
        
        # Ajusta o nome da coluna para atender ao teste unitário existente ('team_name')
        if 'team' in df.columns:
            df = df.rename(columns={'team': 'team_name'})
        
        # Recria as colunas adicionais esperadas pelos testes unitários
        if 'playedGames' in df.columns and 'goalsFor' in df.columns:
            df['goals_per_game'] = df.apply(
                lambda x: x['goalsFor'] / x['playedGames'] if x['playedGames'] > 0 else 0.0, 
                axis=1
            )
            
        if 'playedGames' in df.columns and 'points' in df.columns:
            # Aproveitamento em formato decimal (ex: 18 / 30 = 0.6)
            df['points_pct'] = df.apply(
                lambda x: x['points'] / (x['playedGames'] * 3) if x['playedGames'] > 0 else 0.0, 
                axis=1
            )

        logger.info("Contrato de dados validado com sucesso e DataFrame processado.")
        return df

    except Exception as e:
        logger.error(f"Falha na validação do contrato de dados ou transformação: {e}")
        raise e