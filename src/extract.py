import os
import time
import requests
from src.logging_config import logger

def _prepare_headers(headers: dict = None) -> dict:
    """
    Função auxiliar que garante a injeção segura da chave de API (X-Auth-Token)
    nos cabeçalhos da requisição HTTP, caso o usuário não tenha passado manualmente.
    """
    if not headers or "X-Auth-Token" not in headers:
        api_key = os.getenv("API_KEY")
        return {"X-Auth-Token": api_key} if api_key else {}
    return headers

def _fetch_with_retry(url: str, headers: dict, max_retries: int = 3, backoff_factor: int = 2) -> dict:
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Tentativa {attempt} de {max_retries} para a URL: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info("Dados extraídos com sucesso da API.")
                return response.json()
            
            # TRATAMENTO ESPECIAL PARA RATE LIMIT (429):
            # Se o servidor disser "rápido demais", esperamos 60 segundos para o minuto virar
            elif response.status_code == 429:
                logger.warning("Limite de chamadas por minuto atingido (HTTP 429). Aguardando 60 segundos para liberação do token...")
                time.sleep(60)
                continue
            
            elif response.status_code in [500, 502, 503, 504]:
                logger.warning(f"Servidor retornou status instável ({response.status_code}). Tentando novamente...")
            else:
                logger.error(f"Erro fatal na requisição. Status code: {response.status_code} - Resposta: {response.text}")
                response.raise_for_status()

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.warning(f"Falha de conexão ou timeout na tentativa {attempt}: {e}")

        if attempt < max_retries:
            sleep_time = backoff_factor ** attempt
            logger.info(f"Aguardando {sleep_time} segundos antes da próxima tentativa...")
            time.sleep(sleep_time)
        else:
            logger.error("Número máximo de tentativas excedido. Falha na extração.")
            raise Exception(f"Não foi possível extrair os dados para a URL {url} após várias tentativas.")

# =====================================================================
# FUNÇÕES PÚBLICAS DE EXTRAÇÃO (As portas de entrada para o pipeline)
# =====================================================================

def get_league_data(url_or_code: str, headers: dict = None, max_retries: int = 3, backoff_factor: int = 2) -> dict:
    """
    Extrai os dados da TABELA DE CLASSIFICAÇÃO (standings) de um campeonato.
    Mantém compatibilidade total com o código orquestrador existente.
    """
    headers = _prepare_headers(headers)
    
    # Se o usuário passou apenas a sigla (ex: 'PL'), monta o link completo automaticamente
    if not url_or_code.startswith("http"):
        base_url = os.getenv("API_BASE_URL", "https://api.football-data.org/v4")
        url = f"{base_url}/competitions/{url_or_code}/standings"
    else:
        url = url_or_code

    return _fetch_with_retry(url, headers, max_retries, backoff_factor)

def get_league_matches(url_or_code: str, headers: dict = None, max_retries: int = 3, backoff_factor: int = 2) -> dict:
    """
    [NOVO - ETAPA 3] 
    Extrai o calendário e histórico de PARTIDAS (matches) de um campeonato.
    Traz jogos passados (com placar) e jogos futuros agendados.
    """
    headers = _prepare_headers(headers)
    
    if not url_or_code.startswith("http"):
        base_url = os.getenv("API_BASE_URL", "https://api.football-data.org/v4")
        url = f"{base_url}/competitions/{url_or_code}/matches"
    else:
        url = url_or_code

    return _fetch_with_retry(url, headers, max_retries, backoff_factor)