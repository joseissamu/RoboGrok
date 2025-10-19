from index import app_flask
from waitress import serve
import logging
import os

if os.name == 'nt':
    os.system('cls')
else:
    os.system('clear')

logger = logging.getLogger('waitress')
logger.setLevel(logging.INFO)

if __name__ == "__main__":
    port = 8000
    logger.info(f"Iniciando o servidor Flask na porta {port}")

    serve(app_flask, host='0.0.0.0', port=port)