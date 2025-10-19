import os
import sys
import pyautogui
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

import operator
import logging
import pytesseract
from PIL import ImageFilter
import requests
from time import sleep
from datetime import timedelta, datetime
from typing import Optional, Any

from utils import WindowManager, FileManager, Question, QuestionBuilder, Comando, area_add, parse_date
from overlayCreator import TransparentOverlay
from Constants import featureToQuestion,abas, actionToMode, id_app_correspondence, color, condition, absolutePosition, relativePosition, relativeArea
from dotenv import load_dotenv


def better_emit(record, handler, log_dir):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    handler._original_emit(record)

class Robo:
    """
    Classe que define todo o comportamento do robo.

    :param app_name: nome do aplicativo a ser inicializado
    :type app_name: str
    :param win_manager: Responsável por realizar todas as operações referentes a janelas
    :type win_manager: WindowManager
    :param questions: Objeto que armazena todas as informações que o robô precisará para cumprir sua missão.
    :type questions: Question
    """

    def __init__(self, app_name: str, chosen_feature: str='Base'):
        self.app = app_name
        self.transparent_overlay = TransparentOverlay(box_size=10, duration=5)
        self.retries = 0
        self.commands: list[dict] = []
        self.command_list: list[Comando] = []
        self.operations_list: list[str] = []
        self.questions = Question()
        self.window_manager = WindowManager(app=app_name)
        self.window_manager.detect_window_position(app=app_name)
        self.chosen_feature = chosen_feature
        self.setup_logging()

        self.file_manager = FileManager("Mapeamentos/" + f"{self.app.lower().strip()}BaseCommands.txt")

    def setup_logging(self, log_level: int = logging.INFO) -> None:
        logger_name = f"RoboLogger_{self.app}_{id(self)}"
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(log_level)
        self.logger.propagate = False

        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        self.log_dir = f"log/{self.app.capitalize()}/{datetime.now().strftime('%d.%m.%Y')}"

        # Console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
    def set_log_file(self, log_level: int = logging.INFO):
        # File
        file_handler = next((h for h in self.logger.handlers if isinstance(h, logging.FileHandler)), None)
        if file_handler:
            file_handler.close()
            self.logger.removeHandler(file_handler)

        log_filename = f"{self.chosen_feature}_{datetime.now().strftime('%H.%M.%S')}.log"
        log_path = os.path.join(self.log_dir, log_filename)

        file_handler = logging.FileHandler(log_path, encoding="utf-8", delay=True)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        # Can be made better with a custom FileHandler Class (NOT THE ONE FOR COMMAND MAPPING)
        setattr(file_handler, '_original_emit', file_handler.emit) # Ugly as can be, but seems to work
        file_handler.emit = lambda record, handler=file_handler, log_dir=self.log_dir: better_emit(record, handler, log_dir) # I was wrong this is uglier than the last line, but also seems to work
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(log_level)

        self.logger.addHandler(file_handler)
        self.logger.info(f"Started new log for action: {self.chosen_feature}")

    def open_app(self):
        """
        Método responsável por abrir o aplicativo.
        """
        app_path = f"{self.app}.lnk"
        self.logger.info(f"Iniciando o aplicativo {self.app}...")
        if not os.path.exists(app_path):
            self.logger.error(f"Arquivo {app_path} não encontrado.")
            raise FileNotFoundError(f"Arquivo {app_path} não encontrado.")
        else:
            self.window_manager.openapp(app_path, self.app)
            sleep(4)
            self.window_manager.detect_window_position(app=self.app)
            self.logger.info(f"{self.app} iniciado com sucesso.")

    def follow_command(self, position: relativePosition, action: str, value: color | str, condition) -> None:
        """
        Método responsável por fazer com que o robô siga o passo a passo de determinado comando.
        Para isso, faz a verificação de qual foi o comando solicitado.
        
        :param position: Objeto que armazena a posicao da janela
        :type position: relativePosition
        :param action: Indica tipo de ação a ser realizada (click, write, ...)
        :param value: Informação necessária para o robo agir(cor para modo color detection, e valor a escrito em modo write)
        :type value: color | str
        :param condition: Condição(cor em posição) sob a comando de click deve ser executado
        :type condition: tuple[relativePosition, color]
        :return None:
        """
        if position and not action == 'read':
            position = self.window_manager.get_absolute_position(position)

        if action == 'click':
            self.click_action(position, condition) 

        elif action == 'write':
            self.clear_action()
            if value[0] == '.':
                value = str(value[1:]).lower().capitalize()
                value = str(getattr(self.questions, value))
            self.secure_write(value) 

        elif action == 'color':
            self.color_detection_action(position, value) 

        elif action == 'paramChange':
            self.param_change_action(value)

        elif action == 'read':
            value = str(value)
            read_value = self.read_action(tuple(position)) 
            if not getattr(self.questions, value, None): 
                self.questions.attrs[value] = [] 
            self.questions.attrs[value].append(read_value) 
        
        elif action == 'compare_variables':
            self.compare_action(value) 
            
        elif action == "scroll":
            self.scroll_action(tuple(value)) 

        elif action == 'webhook':
            self.export_action()
    
        sleep(0.1)


    def click_action(self, position: relativePosition, condition: Optional[condition] = None) -> None:
        """
        Método responsável por realizar o clique em uma determinada posição relativa a tela do windowManager.
        
        :param position: posição a ser clicada
        :type position: relativePosition
        :param condition: condição a ser verificada antes do clique
        :type condition: tuple[relativePosition, color]
        :return: None
        """

        self.transparent_overlay.create_overlay(position[0], position[1], callback=self.on_overlay_closed)
        i=0
        if condition:
            condition_pos = self.window_manager.get_absolute_position(condition[0])
            self.transparent_overlay.create_overlay(condition_pos[0], condition_pos[1], callback=self.on_overlay_closed)
            condition_color = condition[1]
            while i<1:
                expected_color : color = condition_color
                detected_color = pyautogui.pixel(condition_pos[0], condition_pos[1])
                self.logger.info(f"Detecting condition at {condition_pos}, expecting {expected_color} x detected {detected_color}")
                if self.color_detection_action(condition_pos, expected_color, conditional=True):
                    self.transparent_overlay.create_overlay(position[0], position[1], callback=self.on_overlay_closed)
                    pyautogui.moveTo(position, duration=0.3)
                    pyautogui.click()
                    self.logger.info(f"Clicked at {position}")
                    break
                sleep(0.1)
                i+=1
            if i==2:
                self.logger.warning("Condition not met, moving on.")
        else:
            pyautogui.moveTo(position, duration=0.3)
            pyautogui.click()
            self.logger.info(f"Clicked at {position}")

    def color_detection_action(self, position: absolutePosition, expected_color: color, conditional: bool = False) -> bool:
        """
        Método responsável por realizar a detecção de cor em uma determinada posição relativa a tela do windowManager.
        
        :param position: posição a ser verificada
        :type position: relativePosition
        :param expected_color: cor esperada na posição
        :type expected_color: color
        """
        self.transparent_overlay.create_overlay(position[0], position[1], callback=self.on_overlay_closed)
        for _ in range(20):
            detected_color = pyautogui.pixel(position[0], position[1])
            self.logger.info(f"Detecting color at {position}, expecting {expected_color} x detected {detected_color}")
            specific_range = 10
            total_range = 20
            if all(abs(detected_color[i] - expected_color[i]) <= specific_range for i in range(3)) and \
                sum(abs(detected_color[i] - expected_color[i]) for i in range(3)) <= total_range:
                self.logger.info(f"Color {detected_color} detected within range.")
                self.retires = 0
                return True
            sleep(0.3)
        else:
            self.logger.warning("Color not detected within range after 20 attempts.")
            if not conditional:
                self.retry_action()
            return False


    def retry_action(self) -> None:
        """
        Método responsável por redefinir o estado da operação atual.
        """
        self.retries += 1

        if self.retries >= 3:
            self.command_list.pop(0)
            self.logger.error(f"Failed to perform operation {self.chosen_feature} after 3 retries. Moving to next operation.")
            return

        self.logger.warning(f"Retrying operation {self.chosen_feature} ({self.retries}°/3 try)")
        self.questions.attrs.update({"Ok": f'Could not perform operation {self.chosen_feature}'})
        self.commands = []
        self.operations_list = []
        self.window_manager.closeapp()
        self.open_app()
        self.next_operation()
        return

    def read_action(self, value: relativeArea) -> str:
        """
        Método responsável por realizar a leitura de um texto exibido no aplicativo.
        
        :param value: coordenadas da bounding box a ser lida
        :type value: tuple[absolutePosition, absolutePosition]
        :param param: parâmetro a ser atualizado
        :type param: str
        :return: texto lido
        :rtype: str
        """
        
        self.logger.info(f"Reading action with value: {value}")
        if not value or len(value) != 2:
            self.logger.error(f"Improper value for read action in {self.chosen_feature} mapping.")
            raise ValueError("Invalid value for read action. Expected a tuple of two tuples.")

        bbr = [(value[0][0], value[0][1]), (value[1][0], value[1][1])]
        pos = self.window_manager.get_absolute_position(bbr[0])\
            + (self.window_manager.get_absolute_position(bbr[1]))
        self.logger.info(f"Calculated position for reading: {pos}")
        pos = self.get_bbox(pos)
        width = pos[2] - pos[0]
        height = pos[3] - pos[1]

        bbox = (pos[0], pos[1], width, height)
        for _ in range(1):
            overlay_window = self.transparent_overlay.create_rectangle_window((pos[0], pos[1]), (pos[2], pos[3]))
            try:
                save_path = f"read_imgs/{self.app}/{self.chosen_feature[:-3]}.png"
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                screenshot = pyautogui.screenshot(region=bbox)
                screenshot.save(save_path)
                print(f"Screenshot taken with bounding box: {bbox},\nsaved to {save_path}")
                screenshot = screenshot.filter(ImageFilter.SHARPEN)
                screenshot = screenshot.convert("RGB")
                treated_save_path = save_path.replace("read_imgs/", "treated_imgs/")
                os.makedirs(os.path.dirname(treated_save_path), exist_ok=True)
                screenshot.save(treated_save_path)
                self.logger.info(f"Screenshot also saved to {treated_save_path}")

                text = pytesseract.image_to_string(screenshot, config="--psm 6").strip()
                if text:
                    self.logger.info(f"Extracted Text: {text}")
                    overlay_window.destroy()
                    return text
                self.logger.warning("OCR returned empty text, retrying...")
                sleep(0.3)
            except Exception as e:
                print(f"OCR failed, Exception: {e}, retrying...")
                sleep(0.3)

        self.logger.warning("Failed to extract text after retries.")
        overlay_window.destroy()
        return ""

    def compare_action(self, value: tuple[str, str, str|relativeArea, str|relativeArea]) -> dict[str, Any]:
        """
        Compara duas variáveis e atualiza o estado da pergunta com o resultado.

        :param value: Lista contendo:\n
            - value[0]: Tipos de origem das variáveis ('R' para leitura, 'Q' para pergunta)\n
            - value[1]: Operador de comparação como string ('==', '!=', '<', '>', '<=', '>=')\n
            - value[2]: Nome ou posição da primeira variável\n
            - value[3]: Nome ou posição da segunda variável\n
        """
        # Mapeamento dos operadores
        operadores = {
            '==': operator.eq,
            '!=': operator.ne,
            '<': operator.lt,
            '<=': operator.le,
            '>': operator.gt,
            '>=': operator.ge,
            'periodo': lambda y, x: (dx := parse_date(x)) >= (dy := parse_date(y)) and dy <= dx - timedelta(days=7)
        }

        if value[1].lower() not in operadores:
            self.logger.error(f"Unsupported comparison operator: {value[1]}")
            raise ValueError(f"Unsupported comparison operator: {value[1]}")

        variaveis = []
        retorno = {}


        for idx, origem in enumerate(value[0].lower()): 
            if origem == 'r':
                pos = value[2 + idx]
                read_var = self.read_action(pos)
                retorno.update({f"r{idx}": read_var})
            elif origem == 'q':
                var = getattr(self.questions, value[2 + idx], "")
                retorno.update({f"q{idx}": var})
                print(f"Question Variable: {var}")
            else:
                self.logger.error(f"Invalid variable type: {origem}")
                raise ValueError(f"Invalid variable type: {origem}")

        variaveis = list(retorno.values())
        self.logger.info(f"Comparing variables: {variaveis[0]} {value[1]} {variaveis[1]}")
        resultado = operadores[value[1].lower()](variaveis[0], variaveis[1])

        if resultado:
            self.logger.info(f"Comparrison successful: {variaveis[0]} {value[1]} {variaveis[1]}")
        else:
            self.logger.warning(f"Comparison failed: {variaveis[0]} {value[1]} {variaveis[1]}")

        self.questions.attrs.update({"Ok": resultado})
        self.logger.info(f"Comparison result: {resultado}")
        return retorno

    def scroll_action(self, value: tuple[str, relativeArea, relativeArea, list[relativePosition], str, relativeArea]) -> None:
        """
        Método responsável por realizar a ação de rolagem na tela.

        :param value: Lista contendo:\n
            - value[0]: Base da variável a ser lida\n
            - value[1]: Posições de rolagem (inicial e final)\n
            - value[2]: Área base a ser lida e comparada\n
            - value[3]: Posição de âncora às áreas extras\n
            - value[4]: Nome da variável a ser lida\n
            - value[5]: Área extra a ser lida (Relativo a <base_area>)\n
        """
        var_base: str = value[0].lower().strip()
        scroll_pos: relativeArea = value[1]
        base_area: relativeArea = value[2]
        anchors: list[relativePosition] = value[3]
        extra_area = value[5]

        abs_scroll = (self.window_manager.get_absolute_position(scroll_pos[0]), self.window_manager.get_absolute_position(scroll_pos[1]))
        self.logger.info(f"Scroll action with var_base: {var_base}, read_areas: {base_area}, scroll_pos: {scroll_pos}")

        first_value = self.read_action(base_area)
        print(f"Base Area: {base_area}")
        last_value = ''
        
        anchors.reverse()
        anchors.append(base_area[0])
        anchors.reverse()

        while first_value != last_value:
            for i, anchor in enumerate(anchors):
                next_area = ((base_area[0][0], anchor[1]), (base_area[1][0], base_area[1][1] - base_area[0][1] + anchor[1]))
                if i == 0:
                    first_value = self.read_action(next_area)
                print(next_area)
                #TODO: Add comp type in Command Detection
                read_dict = self.compare_action(("QR", 'periodo', var_base[1:], next_area))
                read_compare_var = read_dict[[k for k in read_dict if k.startswith('r')][0]]
                if extra_area:
                    read_save_var = self.read_action(area_add(next_area, extra_area))
                    if not getattr(self.questions, value[4], None):
                        self.questions.attrs[value[4]] = [read_save_var]
                    else:
                        self.questions.attrs[value[4]].append(read_save_var)
                if self.questions.attrs.get("Ok", False):
                    self.click_action(next_area, condition=None)
                    break
            else:
                pyautogui.moveTo(abs_scroll[0])
                pyautogui.mouseDown(button='left')
                pyautogui.moveTo(abs_scroll[1], duration=0.75)
                pyautogui.sleep(0.3)
                pyautogui.mouseUp(button='left')


    def clear_action(self) -> None:
        """
        Método responsável por limpar o texto da área selecionada na tela.
        """
        self.logger.info("Clearing text area.")
        pyautogui.press('backspace', presses=20, interval=0.05)


    def export_action(self) -> None:
        """
        Método responsável por exportar dados salvos pelo robô via webhook.
        """
        self.commands = []
        load_dotenv()
        webhook_url = os.getenv("WEBHOOK_URL")

        data_to_export: dict[str, str] = {}
        self.logger.info(f"Gathering data for feature: {self.chosen_feature}")
        question_variable_names: list[str] = QuestionBuilder().get_possible_questions(featureToQuestion.get(self.chosen_feature, ""))
        self.logger.info(f"Exporting data for questions: {question_variable_names}")
        
        for question in question_variable_names:
            value = getattr(self.questions, question.capitalize(), None)
            if value:
                data_to_export[question] = value

        if data_to_export:
            self.logger.info(f"Sending data to webhook: {data_to_export}")
            try:
                # Send the data as a JSON POST request
                response = requests.post(webhook_url, json=data_to_export, headers={'Content-Type': 'application/json'}) 
                response.raise_for_status()  # Raises an exception for bad status codes (4xx or 5xx)
                self.logger.info(f"Webhook sent successfully! Status code: {response.status_code}")

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error sending webhook: {e}")
        else:
            self.logger.warning("No data was collected to send to the webhook.")
        
        self.logger.info(f"Action finished, removing action: {self.command_list[0].question.attrs['Action']} from execution list.")
        self.command_list.pop(0)
        if not self.command_list:
            from task import manage_buffer_transfer
            manage_buffer_transfer.apply_async()
        self.next_operation()

    def get_bbox(self, pos: tuple[int, int, int, int]) -> tuple:
        """
        Método responsável por ordenar as coordenadas da bounding box para extração de imagens.
                
        :param pos: tupla de coordenadas em formato (x1, x2, y1, y2)
        :return: tupla das coordenadas ordernadas em (esquerda, topo, direita, fundo)
        :rtype: tuple[int]
        """
        left = min(pos[0], pos[2])
        top = min(pos[1], pos[3])
        right = max(pos[0], pos[2])
        bottom = max(pos[1], pos[3])

        return (left, top, right, bottom)


    def secure_write(self, reference: str):
        """
        Método responsável por escrever informações sigilosas sem que elas fiquem desorganizadas pelo resto do código
        :param reference: string a ser escrita
        :type reference: str
        :return: None
        """
        if reference.startswith('"') and reference.endswith('"'):
            sleep(0.2)
            pyautogui.write(reference[1:-1])
            self.logger.info(f"Wrote text")
        elif reference.startswith('$'):
            var = self.app.upper().removesuffix("POKER") + "_" + reference[1:]
            value = os.getenv(var)
            if value:
                sleep(0.2)
                pyautogui.write(value)
                self.logger.info(f"Wrote [env_var]")
            else:
                with open('.env', 'r') as env_file:
                    print(env_file.read())
                self.logger.warning(f"Failed to write {reference}")
                self.logger.warning(f"Environment variable {var} not found.")
                raise ValueError(f"Missing required environment variable: {var}")
        else:
            sleep(0.2)
            pyautogui.write(reference)
            self.logger.info(f"Wrote '{reference}'")


    def param_change_action(self, value) -> None:        
        for key in self.questions.attrs.keys():
            if key != "Timenow":
                self.questions.attrs.update({key: []})

        self.chosen_feature = value.get('Action', self.chosen_feature).strip().capitalize()
        self.questions.attrs.update({"Ok": "Ok"})
        for key, val in value.items():
            self.questions.attrs.update({key: val})
            self.logger.info(f"Updated {key} to {val}")

        self.logger.info(f"Updating operation with values: {value}")
        logging.shutdown()


    def add_operation(self, cmd: Comando) -> None:
        """
        Método responsável por adicionar uma operação à lista de comandos do robô.
        :param cmd: Comando a ser adicionado
        :type cmd: Comando        
        """
        
        self.command_list.append(cmd)
        if not self.commands:
            self.logger.info(f"Adding starting operation: {cmd.question.attrs}")
            self.next_operation()
        else:
            self.logger.info(f"Adding operation: {cmd.question.attrs}") 


    def next_operation(self) -> None:
        """
        Método responsável por adicionar uma operação a lista interna do robô.
        """
        self.set_log_file()
        if not self.command_list:
            self.logger.info("No more commands in queue.")
            return
        cmd = self.command_list[0]
        params: dict[str, str] = {}

        operation = getattr(cmd,'Action')
        mode = actionToMode[operation]
        aba = abas[operation]
        questions = QuestionBuilder().get_possible_questions(featureToQuestion.get('Input', ''))
        self.logger.info(f"Performing operation: {operation} in screen: {aba}")
        for question in questions:
            params.update({question: getattr(cmd.question, question.capitalize(), '')})
        params.update({"chosen_feature": operation})
        print(f"Params: {params}")

        print(aba, operation)
        nav_path = f"Mapeamentos/{self.app.lower().strip()}/Nav/{aba}.txt"
        act_path = f"Mapeamentos/{self.app.lower().strip()}/Act/{operation}.txt"

        param_command = {"action": "paramChange", "value": params}
        self.commands.append(param_command)

        finish_command = {"action": "webhook", "value": params}
        
        if not self.operations_list:
            base_path = f"Mapeamentos/{self.app.lower().strip()}/Base/Base.txt"
            self.logger.info(f"Loading Base commands from {base_path}")
            self.commands.extend(self.file_manager.load_commands(action=base_path))
            self.logger.info(f"Loaded Base commands")
            self.commands.extend(self.file_manager.load_commands(action=nav_path))
            self.commands.extend(self.file_manager.load_commands(action=act_path))
            self.logger.info(f"Loaded new commands")

        elif aba != abas[self.operations_list[-1]]:
            return_path = "Mapeamentos/" + f"{self.app.lower().strip()}/Ret/{abas[self.operations_list[-1]]}.txt"
            self.commands.extend(self.file_manager.load_commands(action=return_path))
            self.logger.info(f"Loaded return commands for {abas[self.operations_list[-1]]}")
            self.commands.extend(self.file_manager.load_commands(action=nav_path))
            self.commands.extend(self.file_manager.load_commands(action=act_path))
            self.logger.info(f"Loaded new commands")

        else:
            self.commands.extend(self.file_manager.load_commands(action=act_path))

        self.commands.extend([finish_command])
        if len(self.operations_list) >= 2:
            self.operations_list[0] = self.operations_list[1]
            self.operations_list[1] = operation
        else:
            self.operations_list.append(operation)

        print(f"Command List: {self.commands}")
        self.run()

    def on_overlay_closed(self):
        pass

    def navigate(self, *commands) -> None:
        """
        Método responsável por invocar, para cada comando da lista de comandos, o método responsável pela a execução.
        """
        for command in commands:
            action, position, value, condition = self.file_manager.read_command(command)
            self.follow_command(position, action, value, condition)
        if self.command_list:
            self.navigate(*self.commands)
            
    def run(self) -> None:
        """
        Método responsável por invocar o método de navegação com os comandos passados como parâmetros.
        """
        self.open_app()
        print("Starting Robot...")
        self.navigate(*self.commands)
        self.logger.info("Robot completed all operations. Exiting...")


if __name__ == "__main__":
   robo = Robo(app_name="PPPOKER", chosen_feature="Base")
