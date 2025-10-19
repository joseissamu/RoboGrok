import os
import time
import json

os.environ["N_BOTS"] = "3"

from mock_task import process_command

def send_task(bot_id, action, priority):
    comando = {
        "App": f"app_{bot_id}",
        "Action": action,
        "BotId": bot_id
    }
    from mock_utils import Comando
    c = Comando.from_json(
        json.dumps({
            "question": json.dumps(comando),
            "filtro": "Input"
        })
    )
    print(f"Enviando tarefa para bot_{bot_id} com prioridade {priority} e ação {action}")
    process_command.apply_async(
        args=[c.toJSON()],
        queue=f"bot_{bot_id}",
        priority=priority
    )

if __name__ == "__main__":
    for bot_id in range(1, 4):
        for priority in [2, 1, 0]:  # 0 = mais alta
            send_task(bot_id, f"acao_p{priority}", priority)
            time.sleep(0.1)
    print("Tarefas enviadas. Observe a ordem de execução nos prints dos workers.")