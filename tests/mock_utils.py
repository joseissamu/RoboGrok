import json

class Question:
    def __init__(self, attrs=None):
        self.attrs = attrs or {}

    def __getattr__(self, name):
        if name in self.attrs:
            return self.attrs[name]
        raise AttributeError(f"'Question' object has no attribute '{name}'")

    def toJSON(self):
        return json.dumps(self.attrs)

class Comando:
    FILTROS = ["Input", "MakeTransaction", "SeeTransactions", "SeeBalance", "SeeMembers", "SeeClubStats", "SeeRealTimeStats"]

    def __init__(self, question, filtro=""):
        self.question = question
        self.filtro = filtro

    def __getattr__(self, name):
        if hasattr(self.question, name):
            return getattr(self.question, name)
        raise AttributeError(f"'Comando' object has no attribute '{name}'")

    def toJSON(self):
        return json.dumps({
            "question": self.question.toJSON(),
            "filtro": self.filtro
        }, ensure_ascii=False, indent=4)

    @staticmethod
    def from_json(jsoned_comando):
        data = json.loads(jsoned_comando)
        question_data = json.loads(data['question'])
        question = Question(question_data)
        return Comando(question=question, filtro=data['filtro'])