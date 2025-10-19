from enum import IntEnum
from collections import defaultdict
from typing import TypeAlias, Union
from pynput import keyboard

apps = {0:'pppoker', 1:'supremapoker', 2:'pokerbros'}
robot_type = {0: 'passive', 1: 'active'}

# BOT IDs
pppoker_id = 1
supremapoker_id = 2
pokerbros_id = 3

actions_priorities = {
    'base': 0,
    'transaction': 0,
    'balance': 0,
    'members': 0,
    'club_stats': 0,
    'real_time_stats': 0,
    'send_chips': 0,
    'receive_chips': 0
}

NUMERO_DE_FILAS_DE_PRIORIDADE_POR_ROBO = 3 # 0 é a mais alta prioridade, 1 é a média e 2 é a mais baixa
THRESHOLD_CONTINUOS_QUEUE_FLUX = 2  # Threshold baixo para manter fluxo contínuo da queue
TEMPO_MEDIO_TASKS = 5  # Tempo médio de execução de uma task em segundos
BATCH_SIZE = 12  # Tamanho do lote para transferir do buffer para a principal

full_feature_dict: dict[str, list[Union[str, list[str]]]] = {
    'Input': ['', '', 'Input', ["App", "Mode", "Action", "Id", "Listids", "Club", "Chipamount", "Timenow"]],
    'base': ['base', 'clube', '', ['']],
    'transaction': ['passive', 'transacoes', 'seeTransactions', ['Listatransacoes']],
    'balance': ['passive', 'contador', 'seeBalance', ['Saldo']],
    'members': ['passive', 'mesa', 'seeMembers', ['Membros']],
    'club_stats': ['passive', 'membros', 'seeClubStats', ['']],
    'real_time_stats': ['passive', 'dados', 'seeRealTimeStats', ['Ganhos', 'Mãos', 'bb100', 'GanhoMTT', 'Buyinspinup', 'Taxa']],
    'send_chips': ['active', 'contador', 'makeTransaction', ['Ok', 'Saldo']],
    'receive_chips': ['active', 'contador', 'makeTransaction', ['Ok', 'Saldo']]
}


MODE = 0
ABA = 1
QUESTION = 2
VARIABLES = 3

actionToMode: dict[str, str] = {x: y[MODE].strip().lower() for x, y in full_feature_dict.items()}
abas: dict[str, str] = {x: y[ABA] for x, y in full_feature_dict.items()}
featureToQuestion: dict[str, str] = {x: y[QUESTION]  for x, y in full_feature_dict.items()}
question_variable_names: dict[str, list[str]] = {x: y[VARIABLES] for x, y in full_feature_dict.items()}
feature_base: dict[int, str] = {i: x for i, x in enumerate((x for x in full_feature_dict if full_feature_dict[x][MODE] == 'base'), start=1)}
feature_passive: dict[int, str] = {i: x for i, x in enumerate((x for x in full_feature_dict if full_feature_dict[x][MODE] == 'passive'), start=1)}
feature_active: dict[int, str] = {i: x for i, x in enumerate((x for x in full_feature_dict if full_feature_dict[x][MODE] == 'active'), start=1)}


reversed_dict = defaultdict(list)
for original_key, value_list in question_variable_names.items():
    for new_key in value_list:
        reversed_dict[new_key].append(original_key)
variables_to_questions = dict(reversed_dict)

comparisons = {1: '==', 2: '!=', 3: '>', 4: '<', 5: '>=', 6: '<=', 7: 'Periodo'}
class MODES(IntEnum):
    """
    Classe com todos os comandos que o robô pode realizar (fundamentalmente).
    """
    
    COLOR = 0
    CLICK = 1
    TEXT = 2
    READ = 3
    COMPARE = 4
    SCROLL = 5


shifts = [keyboard.Key.shift, keyboard.Key.shift_r, keyboard.Key.shift_l]
ctrls = [keyboard.Key.ctrl, keyboard.Key.ctrl_r, keyboard.Key.ctrl_l]
alts = [keyboard.Key.alt, keyboard.Key.alt_r, keyboard.Key.alt_l]

absolutePosition: TypeAlias = tuple[int, int]
relativePosition: TypeAlias = tuple[float, float]
relativeArea: TypeAlias = tuple[relativePosition, relativePosition]
color: TypeAlias = tuple[int, int, int]
condition : TypeAlias = tuple[relativePosition, color]

id_app_correspondence: dict[str, int] = {
    "pppoker" : 1,
    "supremapoker" : 2,
    "pokerbros" : 3
}

print(shifts[0].name)