import pytest
from unittest.mock import patch
from src.extract import get_league_data

@patch('src.extract.requests.get')
def test_get_league_data_success(mock_get):
    # 1. PREPARAÇÃO (Arrange): Configuramos o dublê para fingir que a API respondeu com sucesso (Status 200)
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "competition": {"name": "Premier League"},
        "standings": [
            {
                "type": "TOTAL",
                "table": [
                    {"position": 1, "team": {"name": "Flamengo"}, "points": 45}
                ]
            }
        ]
    }

    # 2. AÇÃO (Act): Chamamos a função real passando uma sigla, fazendo-a usar o mock do requests.get
    resultado = get_league_data("PL")

    # 3. VERIFICAÇÃO (Assert): Garantimos que o resultado contém os dados esperados
    assert resultado is not None
    assert "standings" in resultado
    assert resultado["standings"][0]["table"][0]["team"]["name"] == "Flamengo"
    
    # Garantimos que a requisição HTTP foi chamada exatamente 1 vez
    mock_get.assert_called_once()