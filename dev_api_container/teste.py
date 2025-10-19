from flask import Flask, request

app_flask = Flask(__name__)

@app_flask.route('/questions/action', methods=['POST'])
def questions_action():
    data = request.get_json()
    print(data)
    return data, 200

if __name__ == '__main__':
    app_flask.run(debug=True, port=5001)