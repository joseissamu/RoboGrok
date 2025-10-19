class Robo:
    def __init__(self, app_name):
        self.app_name = app_name
        print(f"[MOCK] Robo criado para app: {app_name}")

    def add_operation(self, comando):
        print(f"[MOCK] Operação adicionada ao robo {self.app_name}: {comando}")

    def run(self):
        print(f"[MOCK] Robo {self.app_name} executando operação.")