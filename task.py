from celery import Celery
from kombu import Queue
from utils import Comando
from Constants import NUMERO_DE_FILAS_DE_PRIORIDADE_POR_ROBO, id_app_correspondence
from robo import Robo
from dotenv import load_dotenv
import os


load_dotenv()

N_BOTS = int(os.getenv("N_BOTS", 3))  # Número de robôs que serão utilizados. 3 é o valor padrão

app_celery = Celery(
    'tasks',
    backend='redis://localhost:6379/0',
    broker='redis://localhost:6379/0'
)

app_celery.conf.broker_transport_options = {
    'priority_steps': list(range(NUMERO_DE_FILAS_DE_PRIORIDADE_POR_ROBO)),
    'queue_order_strategy': 'priority',
}

# Para que tarefas de alta prioridade não fiquem presas atrás de tarefas de menor prioridade
app_celery.conf.worker_prefetch_multiplier = 1

app_celery.conf.task_queues = (
    Queue(f'bot_{i}', routing_key=f'bot_{i}') for i in range(N_BOTS+1)  # Cria uma fila para cada robô
)

robo_ppp = Robo("pppoker")
robo_sup = Robo("supremapoker")
robo_bro = Robo("pokerbros")

ROBOS_POR_APP: dict[str, Robo] = {
    "pppoker": robo_ppp,
    "supremapoker": robo_sup,
    "pokerbros": robo_bro
}

@app_celery.task
def process_command(jsoned_comando: str) -> str:
    """
    Função que processa um comando recebido.
    """

    comando = Comando.from_json(jsoned_comando)

    app_name = getattr(comando.question, 'App').strip().lower()

    current_robo = ROBOS_POR_APP.get(app_name)
    if not current_robo:
        return f"Erro: Aplicativo '{app_name}' não reconhecido."

    ROBOS_POR_APP[app_name].window_manager.restore_n_focus_window()
    for robo in ROBOS_POR_APP.values():
        if robo != current_robo:
            robo.window_manager.minimize_window()

    current_robo.add_operation(comando)

    bot_id = getattr(comando.question, 'BotId', 'BotId not found')

    return f"Processando o comando para o app: {app_name} no bot: {bot_id}"

if __name__ == '__main__':
    pass