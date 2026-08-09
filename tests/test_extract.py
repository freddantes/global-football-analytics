
import pytest
from unittest.mock import patch
# Substitua 'src.extract' pelo caminho real onde sua função de extração está
from src.extract import extract_data_from_api 

# O decorador @patch substitui a biblioteca 'requests.get' por um "dublê" (mock_get)
@patch('src.extract.requests.get')
def test_extract_data_success(mock_get):
    # 1. PREPARAÇÃO (Arrange): Configuramos o dublê para fingir que a API respondeu com sucesso (Status 200)
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "response": [
            {"team": {"name": "Flamengo"}, "league": {"id": 71}}
        ]
    }

    # 2. AÇÃO (Act): Chamamos a nossa função real. Ela acha que está falando com a internet, mas falará com o dublê.
    resultado = extract_data_from_api("url_falsa", "token_falso")

    # 3. VERIFICAÇÃO (Assert): Garantimos que o resultado da nossa função contém os dados esperados.
    assert resultado is not None
    assert len(resultado["response"]) == 1
    assert resultado["response"][0]["team"]["name"] == "Flamengo"
    
    # Garantimos que a biblioteca de rede foi chamada exatamente 1 vez
    mock_get.assert_called_once()