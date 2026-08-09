import pandas as pd
import duckdb
import pytest
import os

def test_no_duplicate_teams_in_gold_layer():
    """
    Garante que não existem registros duplicados para o mesmo time, 
    na mesma liga e na mesma rodada/data, preservando a base histórica 
    necessária para os gráficos de tendência.
    """
    # Caminho base usando padrão glob para abranger as partições Hive (*/**/*.parquet)
    gold_path = os.path.join("data", "gold", "standings", "**", "*.parquet")
    
    # Se a pasta principal da camada Gold não existir, pulamos o teste para não falhar sem dados locais
    if not os.path.exists(os.path.join("data", "gold", "standings")):
        pytest.skip("Pasta da camada Gold não encontrada. Execute o pipeline ETL primeiro.")

    # Lemos os dados particionados usando o DuckDB com suporte a Hive
    try:
        query = f"SELECT * FROM read_parquet('{gold_path}', hive_partitioning=1)"
        df = duckdb.query(query).to_df()
    except Exception as e:
        pytest.fail(f"Falha ao ler os arquivos parquet particionados com DuckDB: {e}")

    # Se por acaso o DataFrame estiver vazio, pulamos o teste
    if df.empty:
        pytest.skip("Nenhum dado encontrado nas partições da camada Gold.")

    # Define dinamicamente as colunas de unicidade considerando a dimensão temporal do histórico
    cols_to_check = ['team_name', 'league_code']
    if 'matchday' in df.columns:
        cols_to_check.append('matchday')
    elif 'date' in df.columns:
        cols_to_check.append('date')

    # Verificamos se há duplicatas reais dentro do mesmo recorte temporal
    duplicatas = df.duplicated(subset=cols_to_check)
    total_duplicatas = duplicatas.sum()
    
    assert total_duplicatas == 0, f"Alerta Crítico: Foram encontradas {total_duplicatas} linhas duplicadas na camada Gold para a mesma chave temporal!"