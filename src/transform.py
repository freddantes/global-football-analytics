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
        
        # Recria a coluna adicional esperada pelo teste unitário
        if 'playedGames' in df.columns and 'goalsFor' in df.columns:
            # Evita divisão por zero caso playedGames seja 0
            df['goals_per_game'] = df.apply(
                lambda x: x['goalsFor'] / x['playedGames'] if x['playedGames'] > 0 else 0.0, 
                axis=1
            )

        logger.info("Contrato de dados validado com sucesso e DataFrame processado.")
        return df

    except Exception as e:
        logger.error(f"Falha na validação do contrato de dados ou transformação: {e}")
        raise e