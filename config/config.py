# config.py
import os
from dotenv import load_dotenv

# Carrega as variáveis definidas no arquivo .env para o sistema
load_dotenv()

# Cria constantes que o resto do programa vai usar
API_KEY = os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL")

# Verificação de segurança: Se a chave não estiver no .env, o programa avisa
if not API_KEY:
    raise ValueError("Atenção: A variável API_KEY não foi encontrada no arquivo .env!")

# Dicionário de ligas mantido exatamente no padrão que o seu main.py e UI utilizam
LEAGUES = {
    "Premier League": "PL", 
    "Copa do Mundo": "WC", 
    "Champions League": "CL",
    "Libertadores": "CLI", 
    "Brasileirão Série A": "BSA",
    "Brasileirão Série B": "BSB",  # <-- Série B adicionada aqui
    "La Liga": "PD", 
    "Ligue 1": "FL1", 
    "Serie A Italiana": "SA", 
    "Bundesliga": "BL1"
}