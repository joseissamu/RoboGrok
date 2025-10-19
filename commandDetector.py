from typing import Optional

import pyautogui
import logging
import sys
import os
from time import sleep
from dotenv import load_dotenv
from pynput.mouse import Listener as MouseListener, Button
from pynput.keyboard import Key, KeyCode, Events, Listener as KeyboardListener

from utils import WindowManager, FileManager, QuestionBuilder, verificaVarEnv, area_subtract
from Constants import *
from overlayCreator import TransparentOverlay


class Detector:
    """
    Classe responsável pela detecção dos comandos enviados pelo usuário para treinar o robô.
    Seu construtor recebe como parâmetros:
    * app: string com o nome do aplicativo.
    * chosen_feature: string com a feature escolhida pelo usuário.
    """

    def __init__(self, app:str, mode:str, chosen_feature:str):
        self.app = app
        load_dotenv()
        self.env_vars = {'1': ('USER','Usuario'), '2': ('PASSWORD', 'Senha')}
        self.mode_active = mode
        self.chosen_feature = chosen_feature
        self.set_auxiliary_classes()
        self.set_empty_values()
        self.setup_logging()
        
        print(f"Modo: {self.mode_active}. Detecção inicial: {self.detection_mode}")
        print("Pressione CTRL para alternar.")
        self.run()

    def set_empty_values(self) -> None:
        """
        Método responsável por inicializar atributos vazios da instância.
        """
        self.text_detection_active : bool = False
        self.text_buffer: str = "" # TEXT Mode
        self.app_window: bool = False
        self.var_base: Optional[str] = None # SCROLL Mode
        self.running = True
        self.detection_mode: int = MODES.COLOR

    def set_auxiliary_classes(self) -> None:
        """
        Método responsável por instanciar classes auxiliares em atributos da instância do tipo Detector.
        """
        self.window_manager = WindowManager(self.app)
        if self.mode_active == 'test':
            self.app = 'Test'
            file_path = "Mapeamentos/" + f"{self.app.strip().lower()}Base/Base.txt"
        elif self.chosen_feature.lower() == 'base':
            file_path = "Mapeamentos/" + f"{self.app.strip().lower()}/Base/Base.txt"
        else:
            file_path = "Mapeamentos/" + f"{self.app.strip().lower()}/{self.chosen_feature[-3:]}/{self.chosen_feature[:-3]}.txt"
        self.file_manager = FileManager(file_path)
        self.transparent_overlay = TransparentOverlay(duration=30)

    def setup_logging(self, log_path: Optional[str] = None, log_level: int = logging.INFO) -> None:
        logger_name = f"CommandLogger_{self.app}_{id(self)}"
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(log_level)
        self.logger.propagate = False

        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        log_path = f"/logs/Command{self.app}{self.chosen_feature}.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        already_added = any(
            isinstance(h, logging.FileHandler) and
            os.path.abspath(getattr(h, 'baseFilename', '')) == os.path.abspath(log_path)
            for h in self.logger.handlers
        )

        if not already_added:
            file_handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            self.logger.info("FORCE: Log handler configurado e testado com sucesso.")
            file_handler.flush()


# =======================    EVENTOS DE DETECÇÃO    =======================#

    def on_click(self, x, y, button: Button, pressed: bool) -> None:
        """
        Método que reage ao evento de click do usuário.
        """
        position = (x, y)
        if not self.app_window and pressed:
            self.window_manager.set_app_window(position)
            self.app_window = True

    def on_key_press(self, key: Optional[Key | KeyCode]) -> None:
        """
        Método que reage ao evento de pressionamento de teclas pelo usuário.
        """
        if key in alts:
            self.running = False
            return

        if key in ctrls:
            mode = self.text_menu(ctrl=True)
            self.detection_mode = MODES(mode-1)
            print(f"Modo de detecção alterado para: {self.detection_mode.name}")

        if self.app_window:
            if key == Key.esc:
                sleep(0.3)
                if self.detection_mode == MODES.CLICK:
                    self.click_detection(pyautogui.position())
            
                elif self.detection_mode == MODES.TEXT:
                    text = self.text_detection()
                    self.file_manager.save_command({"action": "write", "position": (0, 0), "value": text})
                
                elif self.detection_mode == MODES.COLOR:
                    cor, rel = self.color_detection()
                    self.file_manager.save_command({"action": "color", "position": rel, "value": cor})
                    
                elif self.detection_mode == MODES.READ:
                    var_name = self.read_var_detection()
                    area = self.read_detection()
                    self.file_manager.save_command({"action": "read", "position": area, "value": var_name})

                elif self.detection_mode == MODES.COMPARE:
                        type1, var1 = self.compare_detection()
                        type2, var2 = self.compare_detection()
                        compare_type = self.compare_type_menu()
                        self.file_manager.save_command({
                            "action": "compare",
                            "position": (0, 0),
                            "value": (type1 + type2, compare_type, var1, var2)
                        })
                elif self.detection_mode == MODES.SCROLL:
                        var_base = self.scroll_detection_menu()
                        scroll_pos = self.read_detection()
                        base_area, anchors, question, extra_area = self.scroll_area_detection()
                        self.file_manager.save_command({
                            "action": "scroll",
                            "position": (0, 0),
                            "value": [var_base, scroll_pos, base_area, anchors, question, extra_area]
                        })

        else:
            self.logger.warning("Janela não detectada. Clique na janela para defini-la.")


    def on_key_release(self, key):
        """
        Método que reage ao evento de despressionar uma tecla.
        """
        pass

#=======================    DETECÇÃO DE COMANDOS    =======================#
    # CLICK
    def click_detection(self, position: tuple[int,int]) -> None:
        """
        Método que detecta um click feito pelo usuário.
        """
        condition = None
        rel = self.window_manager.get_relative_position(position)
        print("Deseja adicionar uma condição de cor? (s/n): ")
        add_condition = self.confirmation_detection(('s', 'n'))

        if add_condition:
            cond_pos: relativePosition = self.rel_position_detection(Key.shift)
            abs_pos = self.window_manager.get_absolute_position(cond_pos)
            cond_cor: color = pyautogui.pixel(abs_pos[0], abs_pos[1])
            condition = (cond_pos, cond_cor)
    
        self.file_manager.save_command({"action": "click", "position": rel, "condition": condition})
        self.logger.info(f"Posição de clique registrada: {rel}")

    # COLOR / CONDITION
    def color_detection(self) -> tuple[color, relativePosition]:
        """
        Método responsável pela detecção de cores na tela.
        """
        pos = pyautogui.position()
        rel = self.window_manager.get_relative_position(pos)
        color = pyautogui.pixel(pos[0], pos[1])
        self.logger.info(f"Cor detectada: {color} na posição: {rel}")
        return color, rel

    # TEXT / VARIABLE
    def text_detection(self) -> str:
        """
        Método responsável pelo treino de escrita do robô.
        """
        var_type = self.text_menu()            
        if var_type == 1: 
            self.logger.info("Digite o texto (pressione ESC quando terminar):")
            texto = ''
            while True:
                with Events() as events:
                    event = events.get(1.0)
                    if event is None:
                        continue
                    elif event.key in alts:
                        self.running = False
                    elif event.key == Key.esc:
                        self.logger.info(f'Texto detectado: {texto}')
                    elif hasattr(event.key, 'char') and event.key.char: 
                        texto += event.key.char 

        elif var_type == 2: 
            env_var = self.show_env_menu()
            self.logger.info(f"Variável de ambiente '{env_var}' configurada para escrita")
            self.text_detection_active = False
            return f"${self.app.upper().removesuffix('POKER')}_{env_var}"

        elif var_type == 3: 
            question  = self.questions_menu('Input')
            self.logger.info(f"Pergunta '{question}' configurada para escrita")
            self.text_detection_active = False
            return '.' + question
        return ''

    # READ / AREA
    def read_var_detection(self) -> str:
        """
        Método responsável por detectar uma variável do tipo ID, CLUB, PERIOD, etc.
        """
        print("Determine a variável a ser lida:")
        var_type = self.questions_menu(self.chosen_feature[:-3])
        self.logger.info(f"Variável '{var_type}' configurada para leitura")
        self.text_detection_active = False
        return var_type

    def read_detection(self) -> relativeArea:
        """
        Método responsável por indicar ao robô a região da tela em que deve ser feita a leitura de determinado texto.
        Recebe como parâmetro um objeto do tipo absolutePosition.
        """        
        read_area: relativeArea = ((0, 0), (0, 0))
        while read_area[0] == read_area[1]:
            rel1 = self.rel_position_detection(Key.shift)
            rel2 = self.rel_position_detection(Key.shift)
            read_area = (rel1, rel2)
            if read_area[0] == read_area[1]:
                print("Os pontos definidos são iguais, reiniciando detecção de área.")
            else:
                print(f"Área de leitura definida: {read_area}")
        return read_area

    # COMPARE / AREA CONDITION
    def compare_detection(self) -> tuple[str, str|relativeArea]:
        """
        Método responsável pela detecção de comparações.
        """
        print("Pressione 1 para selecionar a área de leitura ou 2 para selecionar variável interna.")
        while True:
            with Events() as events:
                event = events.get(1.0)
                if event is None:
                    continue
                key = event.key
                if key in alts:
                    self.running = False
                    return '', ''

                if hasattr(key, "char") and key.char: 
                    if key.char == '1': 
                        self.text_detection_active = False
                        area = self.read_detection()
                        return 'R', area
                    elif key.char == '2': 
                        question = self.questions_menu('Input')
                        self.text_detection_active = False
                        return 'Q', question
                else:
                    print("Pressione 1 ou 2 para selecionar o tipo de variável.")

    def compare_type_menu(self) -> str:
        """
        Método responsável por mostrar o menu de tipos de comparação.
        """
        while True:
            option = self.text_menu()
            if option in comparisons:
                return comparisons[option]
            else:
                print("Seleção inválida (1-7). Tente novamente.")

    # SCROLL
    def scroll_detection_menu(self) -> str:
        """
        Método responsável por indicar ao robô que deve realizar um scroll na tela.
        """
        print("Selecione a variável de comparação")
        var_base = self.questions_menu('Input')
        return var_base

    def scroll_area_detection(self) -> tuple[relativeArea, list[relativePosition], Optional[str], Optional[relativeArea]]:
        """
        Método responsável por indicar ao robô que deve realizar a detecção de uma região de scroll.
        """
        question: Optional[str] = None
        anchors: list[relativePosition] = []
        rel_extra_area: Optional[relativeArea] = None

        # Regioes de leitura
        base_area = self.read_detection()
        self.logger.info(f"Região de comparação registrada: {base_area}")
        top_left = self.window_manager.get_absolute_position(base_area[0])
        bottom_right = self.window_manager.get_absolute_position(base_area[1])
        width = bottom_right[0] - top_left[0]
        height = bottom_right[1] - top_left[1]
        
        while True:
            print("Deseja adicionar mais areas de leitura? (s/n): ")
            continua = self.confirmation_detection(('s', 'n'))
            if continua:
                print("Pressione SHIFT para selecionar a região de relativa a 1° de comparação.")
                overlay_window = self.transparent_overlay.follow_mouse_overlay(width, height)
                extra_area_anchor = self.rel_position_detection(Key.shift)
                anchors.append(extra_area_anchor)
                overlay_window.destroy()
            else:
                break
        # Leitura de var interna
        sleep(0.3)
        print("Deseja adicionar leitura de variável interna? (s/n): ")
        leitura_extra = self.confirmation_detection(('s', 'n'))
        if leitura_extra:
            question = self.questions_menu(self.chosen_feature[:-3])
            extra_area = self.read_detection()
            rel_extra_area = area_subtract(extra_area, (base_area))

        return (base_area, anchors, question, rel_extra_area)


#=======================    METÓDOS AUXILIARES PARA DETECÇÕES    =======================#
    def abs_position_detection(self, key: Key) -> absolutePosition:
        """
         Método responsável por detectar uma posição absoluta.
        """
        print(f"Pressione {key.name.capitalize()} para selecionar a posição.")
        while True:
            with Events() as events:
                event = events.get(1.0)
                if event is None:
                    continue
                if event.key in alts:
                    self.running = False
                if event.key == key:
                    pos = pyautogui.position()
                    sleep(0.3)
                    return pos
    
    def rel_position_detection(self, key: Key) -> relativePosition:
        """
        Método responsável por detectar uma posição relativa.
        """
        pos = self.abs_position_detection(key)
        rel = self.window_manager.get_relative_position(pos)
        return rel
    
    def confirmation_detection(self, options: tuple[str, str]) -> bool:
        """
        Método responsável por confirmar uma ação com o usuário.
        Recebe como parâmetro uma tupla de strings com as opções de confirmação.
        """
        confirm = options[0].lower()
        deny = options[1].lower()
        while True:
            with Events() as events:
                event = events.get(1.0)
                if event is None:
                    continue
                elif event.key in alts:
                    self.running = False
                if hasattr(event.key, "char") and event.key.char.lower() == confirm:
                    return True
                elif hasattr(event.key, "char") and event.key.char.lower() == deny:
                    return False

    def relative_area(self, read_area: list[tuple[int, int]]) -> relativeArea:
        """
        Método responsável por retornar a área relativa da região de leitura.
        """
        top_left, bottom_right = self.order_window_positions(read_area[0], read_area[1])
        rel_left = self.window_manager.get_relative_position(top_left)
        rel_right = self.window_manager.get_relative_position(bottom_right)
        return (rel_left, rel_right)


    def text_menu(self, ctrl: Optional[bool] = None) -> int:
        """
        Método responsável por mostrar o menu de detecção de texto.
        """
        if ctrl:
            for mode in MODES:
                if mode == self.detection_mode:
                    print(f"[{mode.value+1}] {mode.name} (ATIVO)")
                else:
                    print(f"[{mode.value+1}] {mode.name}")
            max = len(MODES)
    
        elif self.detection_mode == MODES.TEXT:
            print("Detecção de texto ativa.")
            print("[1] Digitar texto manualmente")
            print("[2] Selecionar variável da .env")
            print("[3] Selecionar ID, CLUB, PERIOD, etc.")
            self.text_detection_active = True
            max = 3
        
        elif self.detection_mode == MODES.COMPARE:
            print("Selecione o tipo de comparação:")
            print("[1] Igual")
            print("[2] Diferente")
            print("[3] Maior que")
            print("[4] Menor que")
            print("[5] Maior ou igual a")
            print("[6] Menor ou igual a")
            print("[7] Periodo")
            max = 7

        while True:
            with Events() as events:
                event = events.get(1.0)
                if event is None:
                    continue
                elif event.key in alts:
                    self.running = False
                if isinstance(event, events.Press):
                    if event.key == Key.esc:
                        self.logger.info("Seleção cancelada")
                        return 0
                    if hasattr(event.key, "char") and event.key.char.isdigit(): 
                        option = int(event.key.char) 
                        if 1 <= option <= max:
                            return option


    def questions_menu(self, put_type:str) -> str:
        """
        Método responsável por mostrar o menu de questions que permite o usuário escolher as informações a serem substituídas na execução do robô.
        """
        self.logger.info('\nSelecione o que escrever')
        self.logger.info(f"Tipo de entrada: {(featureToQuestion[put_type])}")
        possible_questions = QuestionBuilder().get_possible_questions(put_type)
        for i in range(len(possible_questions)):
            self.logger.info(f"[{i}] {possible_questions[i]}")
        self.logger.info("[ESC] Voltar")
        while True:
            if put_type == 'Input':
                with Events() as events:
                    event = events.get(1.0)
                    if event is None:
                        continue
                    elif event.key in alts:
                        self.running = False
                    if event.key == Key.esc:
                        self.logger.info("Seleção cancelada")
                    if hasattr(event.key, "char") and event.key.char.isnumeric() and int(event.key.char) in range(len(possible_questions)): 
                        question = possible_questions[int(event.key.char)] 
                        self.logger.info(f"Variável selecionada: {question}")
                        return '.' + question
                    else:
                        self.logger.warning("Seleção inválida")
            else:
                with Events() as events:
                    event = events.get(1.0)
                    if event is None:
                        continue
                    elif event.key in alts:
                        self.running = False
                    if event.key == Key.esc:
                        self.logger.info("Seleção cancelada")
                    if hasattr(event.key, "char") and event.key.char.isnumeric() and int(event.key.char) in range(len(possible_questions)): 
                        question = possible_questions[int(event.key.char)] 
                        self.logger.info(f"Variável selecionada: {question}")
                        return '.' + question
                    else:
                        self.logger.warning("Seleção inválida")


    def show_env_menu(self) -> str:
        """
        Método responsável por mostrar ao usuário o menu que permite ao usuário escolher informações da .env a serem usadas pelo robô em um momento específico.
        """
        self.logger.info("\nSelecione o  que escrever")
        for key, (var, desc) in self.env_vars.items():
            self.logger.info(f"[{key}] {desc}")
        self.logger.info("[ESC] Voltar")

        while True:
            with Events() as events:
                event = events.get(1.0)
                if event is None:
                    continue
                if event.key in alts:
                    self.running = False
                if isinstance(event, events.Press):
                    if event.key == Key.esc:
                        self.logger.info("Seleção cancelada")
                        return ''
                    if hasattr(event.key, "char") and event.key.char in self.env_vars: 
                        var = self.env_vars[event.key.char][0] 
                        if verificaVarEnv(var):
                            self.logger.info(f"Variável '{var}' configurada para escrita")
                            return f'${var}'
                        else:
                            self.logger.warning(f"Variável '{var}' não encontrada no .env")
                        return ''


    def order_window_positions(self, pos1:absolutePosition, pos2:absolutePosition) -> list[absolutePosition]:
        """
        Método responsável pela ordenação de janelas.
        """
        x1, y1 = pos1
        x2, y2 = pos2
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)
        return [(left, top) , (right, bottom)]


    def run(self) -> None:
        """
        Método loop de detecção.
        """
        with MouseListener(on_click=self.on_click) as ml, KeyboardListener(on_press=self.on_key_press, on_release=self.on_key_release) as kl:
            while self.running:
                ml.join(timeout=0.1)
                kl.join(timeout=0.1)
                if not self.running:
                    break


def main():
    """
    Método principal do treinamento do robô.
    """
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')
    feature_types = {1: "Nav", 2: "Act", 3:  "Ret"}
    app_input = "Defina o aplicativo:\n" + "\n".join([f"[{i+1}] {app}" for i, app in apps.items()]) + "\n[Any]Teste\n\n"
    app_input = int(input(app_input).strip().lower()) - 1
    if app_input >= len(apps):
        app = "Test"
        mode_str = "test"
        chosen_feature = "base"
    else:
        app = apps[app_input]
        mode = int(input("Defina o modo:\n[0] Base\n[1] Passivo\n[2] Ativo\n").strip())
        chosen_feature = None
        if mode == 0:
            mode_str = "base"
            chosen_feature = "base"
            buffer = ""
            for i, feature in feature_base.items():
                buffer += f"[{i}] {feature}\n"
        if mode == 1:
            mode_str = "passive"
            buffer = ""
            for i, feature in feature_passive.items():
                buffer += f"[{i}] {feature}\n"
            buffer += "\n"
            chosen_feature = feature_passive[int(input(buffer).strip())]
        elif mode == 2:
            mode_str = "active"
            buffer = ""
            for i, feature in feature_active.items():
                buffer += f"[{i}] {feature}\n"
            buffer += "\n"
            chosen_feature = feature_active[int(input(buffer).strip())]
        
        if mode_str != "base":
            feature_type = int(input((f"Defina o tipo de feature:\n[1] Navegação\n[2] Ação\n[3] Retorno\n\n")).strip())
            if feature_type == 3:
                chosen_feature = abas[chosen_feature]
            print(f"Feature escolhida: {chosen_feature}")
            chosen_feature += feature_types[feature_type][:3]
            print(f"Feature completa: {chosen_feature}")
    Detector(app, mode_str, chosen_feature if chosen_feature else None)

if __name__ == "__main__":
    
    main()
