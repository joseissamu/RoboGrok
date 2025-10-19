import subprocess
import time
import json
import os

import pygetwindow as gw
import win32gui
import pyautogui

import psutil
import re
from types import MethodType
from typing import Optional, Callable
from typing_extensions import Self
from datetime import datetime as Datetime
from Constants import question_variable_names, variables_to_questions, absolutePosition, relativePosition, relativeArea
import argparse

def verificaVarEnv(var: str) -> bool:
    """
    Função criada para verificar se uma variável de ambiente existe sem que para isso 
    seja necessário obter o valor dela no meio do código onde esta função é usada.
    """
    return os.getenv(var) is not None

class WindowManager:
    """
    Classe incumbida de realizar todo o gerenciamento de janelas.
    Seu construtor inicializa os atributos com valores padrão e recebe como parâmetro o nome do aplicativo inicializado.
    """
    def __init__(self, app: str):
        self.screen_height = 0
        self.screen_width = 0
        self.app = app
        try:
            self.app_window: gw.Window = gw.getWindowsWithTitle(app)[0]
        except IndexError:
            self.app_window = None
        self.window_position = None
        self.client_left = 0
        self.client_top = 0


    def wait_for_process(self, proc_name:str, proc_title:str="") -> psutil.Process:
        """
        Método responsável por aguardar a abertura do aplicativo especificado.
        Recebe como parâmetro:
        * proc_name: string que armazena o nome do aplicativo em formato .exe;
        * proc_title: string que armazena o título que aparece quando se inicializa o aplicativo.
        """
        if not proc_title:
            proc_title=proc_name

        proc = None
        while not proc:
            for p in psutil.process_iter(attrs=['name']):
                if proc_name.lower() in p.info['name'].lower():
                    proc = p
                    break
            time.sleep(0.5)

        while not self.app_window:
            for win in gw.getWindowsWithTitle(""):
                if proc_name.lower() in win.title.lower():
                    self.app_window = win
                    self.screen_width = win.width
                    self.screen_height = win.height
                    print(f"Janela detectada na posição: ({win.left}, {win.top}) Dimensões: {self.screen_width}x{self.screen_height}")
                    break
            time.sleep(0.5)
        return proc

    def openapp(self, app_path:str, app_title:str="") -> None:
        """
        Método responsável por abrir o aplicativo especificado.
        Recebe como parâmetros:
        * app_path: string que armazena o nome do aplicativo em formato .exe;
        * app_title: string que armazena o título que aparece quando se inicializa o aplicativo.
        """
        if not app_title:
            app_title = app_path
        app_name = app_title if app_title else self.app.lower().strip()
        try:
            window = gw.getWindowsWithTitle(app_name)[0]
            self.app_window = window
        except:
            subprocess.Popen([app_path], shell=True)
            print(f"Aguardando o processo do {self.app} iniciar...")
            self.wait_for_process(self.app)
        
        # self.wait_for_process(f"{self.app.split('\\')[-1]}.exe", app_title)
    
    def closeapp(self) -> None:
        """
        Método responsável por fechar o aplicativo especificado.
        """
        if self.app_window:
            self.app_window.close()
            time.sleep(1)
            print(f"Janela do {self.app} fechada.")
        else:
            print(f"Nenhuma janela do {self.app} encontrada para fechar.")

    def set_app_window(self, position : absolutePosition) -> None:
        """
        Método responsável por confirmar a janela detectada em determinada posição.
        Recebe como parâmetro um objeto do tipo absolutePosition, que armazena as posições x e y.
        """
        x, y = position

        if not self.app:
            for win in gw.getWindowsWithTitle(""):
                if win.left <= x <= win.right and win.top <= y <= win.bottom:
                    
                    break
        else:
            win = gw.getWindowsWithTitle(self.app)[0]
        
        self.app_window = win
        
        if self.app_window:
            # obter o identificador de janela hwnd
            hwnd = self.app_window._hWnd
            #retangulo incluindo as bordas
            #retangulo = win32gui.GetWindowRect(hwnd)
            client_rect = win32gui.GetClientRect(hwnd)
            # converter coordenadas para coordenadas da tela
            client_top_left = win32gui.ClientToScreen(hwnd, (0, 0))
            self.client_left = client_top_left[0]
            self.client_top = client_top_left[1]
            # novas alturas e larguras
            self.screen_width = client_rect[2] - client_rect[0]
            self.screen_height = client_rect[3] - client_rect[1]

        #self.screen_width = win.width
        #self.screen_height = win.height
        print(f"Janela detectada na posição: ({win.left}, {win.top}) Dimensões: {self.screen_width}x{self.screen_height}")


    def detect_window_position(self, app: str = "") -> None:
        """
        Método responsável por detectar a posição da janela do aplicativo.
        Recebe como parâmetro o nome do aplicativo a ter sua janela detectada.
        """
        app_name = app if app else self.app.lower().strip()
        try:
            window = gw.getWindowsWithTitle(app_name)[0]
            print(window.left)
            self.set_app_window((window.left, window.top))
        except IndexError:
            self.window_position = None
            print(f"Window {app_name} position not detected.")


    def get_relative_position(self, position: absolutePosition) -> relativePosition:
        """
        Método responsável por obter a posição relativa da janela a partir da posição absoluta.
        Retorna uma tupla contendo o x e y da posição relativa em um objeto do tipo relativePosition.
        """
        x = position[0] - self.client_left #self.app_window.left
        y = position[1] - self.client_top #self.app_window.top
        if self.screen_width and self.screen_height:
            return (x / self.screen_width, y / self.screen_height)
        return (0, 0)


    def get_absolute_position(self, position: relativePosition) -> absolutePosition:
        """
        Método responsável por obter a posição absoluta da janela a partir da posição relativa.
        Retorna uma tuple contendo o x e o y da posição absoluta em um objeto do tipo absolutePositon
        """
        x = position[0]
        y = position[1]
        width = int(x * self.screen_width) + self.client_left #self.app_window.left
        height = int(y * self.screen_height) + self.client_top #self.app_window.top
        return (width, height)
    
    def toggle_app_window(self) -> None:
        """
        Alterna o estado da janela do aplicativo (minimiza se aberta, restaura se minimizada).
        A janela a ser alternada é a armazenada em self.app_window.
        """
        if self.app_window:
            if self.app_window.isMinimized:
                print(f"Restaurando janela do {self.app_window.title}...")
                self.app_window.restore()
                self.app_window.activate() # foco na janela
            else:
                print(f"Minimizando janela do {self.app_window.title}...")
                self.app_window.minimize()
        else:
            print("Nenhuma janela de aplicativo definida para alternar.")

    def minimize_window(self) -> None:
        if self.app_window:
            self.app_window.minimize()
        else:
            print(f"Nao pude minimizar o app")

    def restore_n_focus_window(self) -> None:
        if self.app_window:
            self.detect_window_position()
            self.app_window.restore()
            self.app_window.activate() # foco na janela
            time.sleep(0.5)
            self.detect_window_position(app=self.app)
        else:
            print(f"Nao pude focar na janela")

# Command Mapping File Handling
class FileManager:
    """
    Classe responsável por toda a manipulação de arquivos existente no projeto.
    Seu construtor recebe como parâmetro uma string referente ao caminho do arquivo.
    """
    
    def __init__(self, file_path: str):
        self.file_path = file_path

    def save_command(self, command: dict) -> None:
        """
        Método responsável por salvar um comando em um arquivo.
        Recebe como parâmetro um dicionário contendo as informações específicas do comando a ser salvo.
        """
        
        try:
            data = []
            if os.path.isfile(self.file_path) and os.path.getsize(self.file_path) > 0:
                with open(self.file_path, "r", encoding="utf-8") as file:
                    data = json.load(file)

            data.append(command)

            with open(self.file_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4)

            print("Comando salvo com sucesso.")
        except (IOError, json.JSONDecodeError) as e:
            print(f"Erro ao salvar comando: {e}")

    def read_command(self, command: dict) -> tuple:
        """
        Método responsável por obter cada dado contido no dicionário command.
        Recebe como parâmetro um dicionário command.
        Retorna uma tupla contendo as informações que estão no dicionário.
        """
        
        return command.get('action'), command.get('position'), command.get('value'), command.get('condition')

    def load_commands(self, action: str) -> list:
        """
        Método responsável por carregar os comandos contidos no arquivo.
        Recebe como parâmetro o nome do arquivo que contém os comandos.
        Retorna uma lista (de dicionários) com todos os comandos contidos no arquivo especificado.
        """
        
        if action:
            self.file_path = action
        if not os.path.isfile(self.file_path) or os.path.getsize(self.file_path) == 0:
            return []
        with open(self.file_path, "r", encoding="utf-8") as file:
            return json.load(file)

class Question:
    """
    Classe cujas instâncias são responsáveis por armazenar todos os dados que serão necessários para determinada ação do robô.
    Seu construtor apenas configura os atributos com seus valores iniciais.
    
    Espera-se que a instanciação seja feita através da classe QuestionBuilder pois,
    combinadas, essas duas classes implementam o padrão Factory Build.
    
    Todos os atributos são escritos com letra minúscula e sem underline.
    """

    def __init__(self, attrs: dict[str, str|int|list[str]] = {}):
        self.attrs = attrs

    def __getattr__(self, name: str):
        if name.lower() == "timenow":
            return Datetime.now().strftime("%d-%m-%Y")
        if name in self.attrs.keys():            
            return self.attrs[name]
        return None

    def toJSON(self) -> str:
        return json.dumps(self.attrs)

class QuestionBuilder:
    """
    Classe responsável pela instanciação de objetos do tipo Question por meio do padrão Factory Build.
    Seu construtor apenas instancia um objeto do tipo Question.
    """

    def __init__(self):
        self.Q = Question()
        self.makeBuilderQuestions()
    
    def makeBuilderQuestions(self) -> None:
        """
        Método responsável por criar os métodos que serão utilizados para atribuir valores aos atributos do objeto Question.
        Utiliza o método makeDecorator para criar os decorators necessários.
        """
        for key, values in variables_to_questions.items():
            def make_func(name: str) -> Callable:
                def method(self: Self, val = None):
                    self.Q.attrs.update({name: val if val else None})
                    return self
                method.__name__ = name
                for value in values:
                    setattr(method, f"is_{value}", True)
                    setattr(method, f"is_action", True)
                return method
            setattr(self, f"get{key}", MethodType(make_func(key), self))


    def build(self) -> Question:
        """
        Método responsável por concluir o Factory Build retornando o atributo Q do tipo Question, já com todos os dados necessários para o robô executar determinada tarefa.
        """
        return self.Q

    def get_possible_questions(self, filter_by_decorator: str = "") -> list[str]:
        """
        Método estático responsável por retornar todos os métodos desta classe que sejam responsáveis por atribuir algum valor a algum atributo do Q (Question).
        Recebe como parâmetro uma string filter_by_decorator que permite que apenas os métodos marcados com determinado decorator sejam listados.
        Retorna uma lista com todos os métodos já filtrados.

        Caso filter_by_decorator não seja especificado, esse filtro não é feito e todos os métodos do tipo ask{algo} serão listados.
        """
        asks = []
        for m in dir(self):
            metodo = getattr(self, m)
            if callable(metodo) and not m.strip().startswith("_"):
                if filter_by_decorator:
                    if hasattr(metodo, f"is_{filter_by_decorator}"):
                        asks.append(m)
                else:
                    asks.append(m)
        return list(map(lambda a: a[3:], asks))

class Comando:
    """
    Classe responsável por abstrair a ideia de comando.
    Na fila de execução do robô, estão presentes somente objetos do tipo Comando.
    Seu construtor recebe como parâmetro um objeto do tipo Question (com as informações pertinentes) e uma string filtro com o nome do endpoint invocado.
    """

    FILTROS = list(question_variable_names.keys())

    def __init__(self, question: Question, filtro: str=""):
        self.question = question
        self.filtro = filtro

    def __getattr__(self, name):
        if hasattr(self.question, name):
            return getattr(self.question, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def merge(self, cmd: Optional[Self] = None):
        """
        Método responsável pelo reaproveitamento de informações oriundas de outro objeto Comando e que não devem ser perdidas no programa pois serão reaproveitadas.
        """
        if cmd is None or cmd.question is None: 
            return  # Não faz nada se cmd ou cmd.question for None
        try:
            for atributo, valor_cmd in vars(cmd.question).items(): 
                valor_self = getattr(self.question, atributo, None)
                # Atualiza apenas se o valor atual for None e o valor do cmd não for None
                if valor_self is None and valor_cmd is not None:
                    setattr(self.question, atributo, valor_cmd)
        except AttributeError as e:
            pass
    
    def toJSON(self) -> str:
        """
        Método responsável por retornar uma string JSON com os dados do comando.
        """
        return json.dumps({
            "question": self.question.toJSON(),
            "filtro": self.filtro
        }, ensure_ascii=False, indent=4)

    @staticmethod
    def from_json(jsoned_comando: str) -> 'Comando':
        """
        Método estático responsável por criar um objeto Comando a partir de uma string JSON.
        Recebe como parâmetro uma string jsoned_comando e retorna um objeto do tipo Comando.
        """
        data = json.loads(jsoned_comando)
        question_data = json.loads(data['question'])
        question = Question(question_data)
        return Comando(question=question, filtro=data['filtro'])


def get_nbots_flag() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--nbots', type=int, help="Número máximo de robôs")
    return parser.parse_args().nbots

def area_add(area1: relativeArea, area2: relativeArea) -> relativeArea:
    pos1: relativePosition = (area1[0][0] + area2[0][0], area1[0][1] + area2[0][1])
    pos2: relativePosition = (area1[1][0] + area2[1][0], area1[1][1] + area2[1][1])
    return (pos1, pos2)

def area_subtract(area1: relativeArea, area2: relativeArea) -> relativeArea:
    pos1: relativePosition = (area1[0][0] - area2[0][0], area1[0][1] - area2[0][1])
    pos2: relativePosition = (area1[1][0] - area2[1][0], area1[1][1] - area2[1][1])
    return (pos1, pos2)

def parse_date(x):
    if isinstance(x, Datetime):
        return x

    cleaned = re.sub(r"[^0-9]", "", x)
    print(f"Cleaned time: {cleaned}")
    if len(cleaned) != 8:
        raise ValueError(f"Data inválida após limpeza: {x} -> {cleaned}")

    return Datetime.strptime(cleaned, "%d%m%Y")

if __name__ == "__main__":
    questionBuilder = QuestionBuilder()
    print(questionBuilder.get_possible_questions("send_chips"))
