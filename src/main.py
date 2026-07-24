import os
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

# Importação dos módulos do pipeline e da configuração de log
from src.extract import get_league_data
from src.transform import process_standings
from src.load import save_data, save_consolidated_data
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
    
    logger.info("Iniciando execução do pipeline de dados.")
    
    if not api_key:
        logger.error("API_KEY não encontrada nas variáveis de ambiente.")
        return

    processed_dfs = []

    for name, code in LEAGUES.items():
        logger.info(f"Processando liga: {name} ({code})")
        try:
            # 1. EXTRACT
            raw_data = get_league_data(code, api_key)
            
            # 2. TRANSFORM
            df = process_standings(raw_data)
            
            # 3. LOAD
            if df is not None:
                # Adicionamos metadados da competição para permitir a consolidação e filtros futuros
                df['league_code'] = code
                df['league_name'] = name
                
                save_data(df, code, today)
                processed_dfs.append(df)
                logger.info(f"Sucesso: Dados de {name} salvos com sucesso.")
            else:
                logger.warning(f"Aviso: Nenhuma tabela encontrada para {name}.")
                
        except Exception as e:
            logger.error(f"Falha crítica ao processar {name}: {e}")

    # Gera o arquivo consolidado na raiz de data/gold para a API FastAPI consumir
    if processed_dfs:
        save_consolidated_data(processed_dfs)
        logger.info("Consolidação dos KPIs finalizada com sucesso.")

    logger.info("Pipeline finalizado.")

if __name__ == "__main__":
    run_pipeline()