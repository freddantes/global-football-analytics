import pandas as pd
import duckdb
import os
import logging
from src.analytics import get_match_predictions

# ==========================================
# CONFIGURAÇÃO DE LOG E AMBIENTE
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - pipeline - %(levelname)s - %(message)s')

def run_backtest():
    logging.info("Iniciando Backtesting para BSA - Temporada 2023")
    
    # 1. Carrega os jogos locais via DuckDB
    # Apontamos para o diretório local onde o backfill salvou os dados
    # local_path = os.path.join("data", "gold", "matches", "**", "*.parquet") # apenas para teste local
    # 1. Carrega os jogos da Nuvem (Produção) via DuckDB
    bucket_path = "gs://futebol-datalake-global-analytics-2026/data/gold/matches/**/*.parquet"
    
    try:
        # Puxa apenas os jogos de 2023 para o backtest direto do Google Cloud
        query = f"""
            SELECT * FROM read_parquet('{bucket_path}')
            WHERE league_code = 'BSA' AND CAST(date AS VARCHAR) LIKE '2023-%'
            ORDER BY date ASC
        """
        df_matches = duckdb.query(query).to_df()
    except Exception as e:
        logging.error(f"Erro ao ler arquivos locais: {e}")
        return

    # ==========================================
    # PARÂMETROS FINANCEIROS (GESTÃO DE BANCA)
    # ==========================================
    banca_inicial = 100.0
    banca_atual = banca_inicial
    total_apostas = 0
    apostas_ganhas = 0
    unidade_aposta = 1.0 # Flat Staking de 1 unidade por aposta de valor

    print(f"💰 Banca Inicial: {banca_inicial} unidades")
    print("-" * 50)
    
    # ==========================================
    # MOTOR DE SIMULAÇÃO (O LOOP DO TEMPO)
    # ==========================================
    for index, match in df_matches.iterrows():
        logging.info("Executando SQL DuckDB para matches (Liga: BSA)")
        
        home_team = match['home_team']
        away_team = match['away_team']
        
        # Verifica se a Pinnacle ofereceu cotação (linha de fechamento) para este jogo
        if 'PSCH' not in match or pd.isna(match['PSCH']):
            continue
            
        odd_pinnacle_home = float(match['PSCH'])
        
        # Chama o motor estatístico de Poisson
        data_do_jogo = match['utc_date']
        preds = get_match_predictions('BSA', home_team, away_team, match_date=data_do_jogo)
        
        if not preds:
            continue
            
        # A probabilidade vem em porcentagem do motor (ex: 45.5), convertemos para decimal (0.455)
        prob_modelo_home = float(preds['home_win_pct']) / 100.0
        
        # ==========================================
        # CÁLCULO DE VALOR E DEPURAÇÃO
        # ==========================================
        # EV = (Probabilidade do Modelo * Odd da Casa) - 1
        ev_home = (prob_modelo_home * odd_pinnacle_home) - 1
        
        # --- JANELA DE DEPURAÇÃO (Nova Lupa) ---
        # Imprime os cálculos dos primeiros 15 jogos analisados
        if index < 30: # Limitador para não inundar o terminal
            print(f"\n⚽ {home_team} x {away_team}")
            print(f"Probabilidade do Modelo (Mandante): {prob_modelo_home:.3f}")
            print(f"Odd da Pinnacle (Mandante): {odd_pinnacle_home}")
            print(f"Valor Esperado (EV): {ev_home:.4f}")
        # ---------------------------------------
        
        # ==========================================
        # LIQUIDAÇÃO DA APOSTA VIRTUAL
        # ==========================================
        # Regra de Ouro: Só entra no mercado se o Valor Esperado for positivo (+EV)
        if ev_home > 0:
            total_apostas += 1
            
            home_goals = match['home_goals']
            away_goals = match['away_goals']
            
            # Verifica o resultado real que aconteceu no passado
            if home_goals > away_goals:
                # Aposta ganha: Lucro = (Odd - 1) * Unidade
                lucro = (odd_pinnacle_home - 1) * unidade_aposta
                banca_atual += lucro
                apostas_ganhas += 1
            else:
                # Aposta perdida: Perde a unidade apostada
                banca_atual -= unidade_aposta

    # ==========================================
    # RELATÓRIO FINAL DE PERFORMANCE
    # ==========================================
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