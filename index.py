from flask import Flask, request, jsonify
from utils import QuestionBuilder, Comando
from Constants import actions_priorities
from task import process_command
from robo import Robo

app_flask = Flask(__name__)



@app_flask.route('/robo/<int:bot_id>/questions/input', methods=['POST'])
def questions_action(bot_id: int):
    data = request.get_json()
    possible_questions = QuestionBuilder().get_possible_questions('Input')
    possible_questions = [q.lower() for q in possible_questions]
    if data:
        for item in data:
            question_builder = QuestionBuilder()
            for key, value in item.items():
                key = key.lower()
                if key in possible_questions and value is not None and value != "":
                    question_builder = getattr(question_builder, f"get{key.capitalize()}")(val=value)

            question_builder.Q.attrs.update({'BotId': bot_id})
            #nome_da_fila = f"bot_{bot_id}"
            nome_da_fila = f"bot_queue"

            comando = Comando(question=question_builder.build(), filtro='Input')
            process_command.apply_async(
                args=[comando.toJSON()], # é importante passar para json para serializar o objeto Comando
                queue=nome_da_fila,
                priority=actions_priorities[comando.question.Action]
            )

            print(f"Tarefa para o bot {bot_id} enfileirada na fila '{nome_da_fila}'")

            print(comando.question.attrs)
        return data, 200
    else:
        return jsonify({"error": "Nenhum dado enviado!"}), 400

if __name__ == '__main__':
    app_flask.run(debug=True, port=5001)
    questions_action(1)