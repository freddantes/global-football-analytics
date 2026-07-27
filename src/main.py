import os
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
import time

# Importação dos módulos do pipeline
from src.extract import get_league_data, get_league_matches
from src.transform import process_standings, process_matches
from src.load import save_data, save_consolidated_data, save_consolidated_matches
from src.logging_config import logger

# Carrega as variáveis de ambiente
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
    
    logger.info("Iniciando execução do pipeline de dados (Standings & Matches).")
    
    if not api_key:
        logger.error("API_KEY não encontrada nas variáveis de ambiente.")
        return

    processed_standings_dfs = []
    processed_matches_dfs = []

    for name, code in LEAGUES.items():
        logger.info(f"--- Processando competição: {name} ({code}) ---")
        try:
            # -------------------------------------------------------------
            # ETAPA A: CLASSIFICAÇÃO (Standings)
            # -------------------------------------------------------------
            raw_standings = get_league_data(code)
            df_standings = process_standings(raw_standings)
            if df_standings is not None:
                df_standings['league_code'] = code
                df_standings['league_name'] = name
                save_data(df_standings, f"{code}_standings", today)
                processed_standings_dfs.append(df_standings)
            
            # Pausa de 6 segundos para respeitar o Rate Limit da API gratuita
            time.sleep(6)
            
            # ETAPA B: PARTIDAS
            raw_matches = get_league_matches(code)
            df_matches = process_matches(raw_matches)
            if df_matches is not None:
                df_matches['league_code'] = code
                df_matches['league_name'] = name
                save_data(df_matches, f"{code}_matches", today)
                processed_matches_dfs.append(df_matches)
            
            # Nova pausa ao terminar a liga antes de ir para a próxima
            time.sleep(6)
                
        except Exception as e:
            logger.error(f"Falha crítica ao processar {name}: {e}")

    # Gera os dois grandes arquivos consolidados na raiz de data/gold
    if processed_standings_dfs:
        save_consolidated_data(processed_standings_dfs)
    if processed_matches_dfs:
        save_consolidated_matches(processed_matches_dfs)

    logger.info("Pipeline finalizado com sucesso absoluto.")

if __name__ == "__main__":
    run_pipeline()