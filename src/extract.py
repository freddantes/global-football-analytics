import time
import requests
from src.logging_config import logger

def fetch_data(url: str, headers: dict, max_retries: int = 3, backoff_factor: int = 2) -> dict:
    """
    Faz requisições HTTP para a API com uma estratégia de retry e exponential backoff.
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Tentativa {attempt} de {max_retries} para a URL: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            
            # Se a requisição for bem-sucedida, retorna o JSON
            if response.status_code == 200:
                logger.info("Dados extraídos com sucesso da API.")
                return response.json()
            
            # Se o erro for do tipo servidor (5xx) ou Too Many Requests (429), vale a pena tentar de novo
            elif response.status_code in [429, 500, 502, 503, 504]:
                logger.warning(f"Servidor retornou status {response.status_code}. Tentando novamente em breve...")
            else:
                # Erros de cliente que não adianta repetir (ex: 400 Bad Request, 403 Forbidden, 404 Not Found)
                logger.error(f"Erro fatal na requisição. Status code: {response.status_code} - Resposta: {response.text}")
                response.raise_for_status()

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.warning(f"Falha de conexão ou timeout na tentativa {attempt}: {e}")

        # Se chegou aqui, a tentativa falhou. Aguarda antes de tentar novamente (Exponential Backoff)
        if attempt < max_retries:
            sleep_time = backoff_factor ** attempt
            logger.info(f"Aguardando {sleep_time} segundos antes da próxima tentativa...")
            time.sleep(sleep_time)
        else:
            logger.error("Número máximo de tentativas excedido. Falha na extração.")
            raise Exception("Não foi possível extrair os dados da API após várias tentativas.")