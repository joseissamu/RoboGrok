# utils/gui_lock.py
import redis
import time

# Conecte-se ao seu Redis. Use as mesmas configurações do seu broker Celery.
# É uma boa prática carregar isso a partir de variáveis de ambiente.
REDIS_CLIENT = redis.Redis(host='localhost', port=6379, db=0)
LOCK_KEY = "pyautogui_lock" # Nome da chave que representará a trava
LOCK_TIMEOUT = 60 # Segundos que a trava irá expirar, para evitar deadlocks

class GUiLock:
    """
    Um gerenciador de contexto para um lock distribuído usando Redis,
    garantindo que apenas uma tarefa de pyautogui execute por vez.
    """
    def __init__(self, timeout=30, retry_interval=0.5):
        self.timeout = timeout
        self.retry_interval = retry_interval

    def __enter__(self):
        start_time = time.monotonic()
        while time.monotonic() - start_time < self.timeout:
            # Tenta adquirir a trava. SETNX (SET if Not eXists) é atômico.
            # 'ex=LOCK_TIMEOUT' faz a chave expirar para evitar travas permanentes.
            if REDIS_CLIENT.set(LOCK_KEY, "locked", nx=True, ex=LOCK_TIMEOUT):
                return self # Lock adquirido com sucesso
            time.sleep(self.retry_interval) # Espera e tenta novamente
        raise TimeoutError("Não foi possível adquirir a trava da GUI.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Libera a trava ao sair do bloco 'with'
        REDIS_CLIENT.delete(LOCK_KEY)