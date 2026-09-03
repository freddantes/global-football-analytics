import pandas as pd
import duckdb
import os
import logging
from src.analytics import query_hive_matches, get_match_predictions

# ==========================================
# CONFIGURAÇÃO DE LOG E AMBIENTE
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - pipeline - %(levelname)s - %(message)s')

def run_backtest():
    logging.info("Iniciando Backtesting para BSA - Temporada 2023")
    
    bucket_path = "gs://futebol-datalake-global-analytics-2026/data/gold/matches/**/*.parquet"
    
    try:
        # Busca todas as partidas de 2023 para rodar a simulação
        query_2023 = f"""
            SELECT * FROM read_parquet('{bucket_path}')
            WHERE league_code = 'BSA' AND CAST(date AS VARCHAR) LIKE '2023-%'
            ORDER BY date ASC
        """
        df_matches = duckdb.query(query_2023).to_df()
        
        # OTIMIZAÇÃO DE MEMÓRIA: Baixa TODO o histórico geral uma única vez
        logging.info("Carregando base histórica completa na memória...")
        df_historico_completo = query_hive_matches('BSA')
        
    except Exception as e:
        logging.error(f"Erro ao ler arquivos do Data Lake: {e}")
        return

    banca_inicial = 100.0
    banca_atual = banca_inicial
    total_apostas = 0
    apostas_ganhas = 0
    unidade_aposta = 1.0

    print(f"💰 Banca Inicial: {banca_inicial} unidades")
    print("-" * 50)
    
    # Substituímos iterrows por itertuples, que processa linhas como tuplas C e é significativamente mais rápido
    for match in df_matches.itertuples():
        home_team = match.home_team
        away_team = match.away_team
        
        if pd.isna(match.PSCH):
            continue
            
        odd_pinnacle_home = float(match.PSCH)
        data_do_jogo = match.utc_date
        
        # Passamos o DataFrame histórico inteiro como parâmetro para evitar que o motor acione o banco de dados
        preds = get_match_predictions(
            league_code='BSA', 
            home_team=home_team, 
            away_team=away_team, 
            match_date=data_do_jogo,
            historical_df=df_historico_completo
        )
        
        if not preds:
            continue
            
        prob_modelo_home = float(preds['home_win_pct']) / 100.0
        ev_home = (prob_modelo_home * odd_pinnacle_home) - 1
        
        if match.Index < 30: 
            print(f"\n⚽ {home_team} x {away_team}")
            print(f"Probabilidade do Modelo (Mandante): {prob_modelo_home:.3f}")
            print(f"Odd da Pinnacle (Mandante): {odd_pinnacle_home}")
            print(f"Valor Esperado (EV): {ev_home:.4f}")
        
        if ev_home > 0:
            total_apostas += 1
            
            home_goals = match.home_goals
            away_goals = match.away_goals
            
            if home_goals > away_goals:
                lucro = (odd_pinnacle_home - 1) * unidade_aposta
                banca_atual += lucro
                apostas_ganhas += 1
            else:
                banca_atual -= unidade_aposta

    print("-" * 50)
    print("📊 RELATÓRIO FINAL DE BACKTESTING (2023)")
    print(f"Total de Apostas de Valor (+EV) Encontradas: {total_apostas}")
    
    win_rate = (apostas_ganhas / total_apostas * 100) if total_apostas > 0 else 0.0
    print(f"Taxa de Acerto (Win Rate): {win_rate:.2f}%")
    print(f"Banca Final: {banca_atual:.2f} unidades")
    
    roi = ((banca_atual - banca_inicial) / banca_inicial) * 100
    print(f"ROI (Retorno sobre Investimento): {roi:.2f}%")

if __name__ == "__main__":
    run_backtest()