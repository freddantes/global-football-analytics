
import pandas as pd
import pytest
import os

def test_no_duplicate_teams_in_gold_layer():
    # Caminho fictício para o seu arquivo final gerado pelo pipeline
    # Ajuste para apontar para um arquivo parquet gerado pelo seu ambiente de desenvolvimento
    file_path = "data/gold/championship_data.parquet"
    
    # Se o arquivo não existir (ex: pipeline não rodou), pulamos o teste para não falhar à toa
    if not os.path.exists(file_path):
        pytest.skip(f"Arquivo {file_path} não encontrado para teste de qualidade.")

    # Lemos os dados estruturados
    df = pd.read_parquet(file_path)

    # Verificamos se há duplicatas na combinação de chaves que deveria ser única
    # Ajuste 'team_name' e 'league_code' para os nomes reais das suas colunas
    duplicatas = df.duplicated(subset=['team_name', 'league_code'])
    
    # A soma de valores 'True' (duplicados) deve ser zero
    total_duplicatas = duplicatas.sum()
    
    assert total_duplicatas == 0, f"Alerta Crítico: Foram encontradas {total_duplicatas} linhas duplicadas no arquivo Parquet!"