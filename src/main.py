import time
import os
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

from src.extract import get_league_data, get_league_matches
from src.transform import process_standings, process_matches
from src.load import save_hive_partition
from src.logging_config import logger

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')

LEAGUES = {
    "Premier League": "PL",
    "Copa do Mundo": "WC",
    "Champions League": "CL",
    "Mundial de Clubes": "FCWC",
    "Libertadores": "CLI",
    "Brasileirão Série A": "BSA",
    "La Liga": "PD",
    "Ligue 1": "FL1",
    "Serie A Italiana": "SA",
    "Bundesliga": "BL1"
}

def run_pipeline():
    api_key = os.getenv("API_KEY")
    today = datetime.now().strftime("%Y-%m-%d")
    
    logger.info("Iniciando execução do pipeline (Hive Partitioning).")
    
    if not api_key:
        logger.error("API_KEY não encontrada nas variáveis de ambiente.")
        return

    for name, code in LEAGUES.items():
        logger.info(f"--- Processando competição: {name} ({code}) ---")
        try:
            # ETAPA A: CLASSIFICAÇÃO
            raw_standings = get_league_data(code)
            df_standings = process_standings(raw_standings)
            
            if df_standings is not None:
                df_standings['league_code'] = code
                df_standings['league_name'] = name
                save_hive_partition(df_standings, "standings", today)
            
            time.sleep(6)
            
            # ETAPA B: PARTIDAS
            raw_matches = get_league_matches(code)
            df_matches = process_matches(raw_matches)
            
            if df_matches is not None:
                df_matches['league_code'] = code
                df_matches['league_name'] = name
                save_hive_partition(df_matches, "matches", today)
                
            time.sleep(6)
                
        except Exception as e:
            logger.error(f"Falha crítica ao processar {name}: {e}")

    logger.info("Pipeline finalizado com sucesso. Dados organizados em partições Hive.")

if __name__ == "__main__":
    run_pipeline()