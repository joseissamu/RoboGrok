# webhook_receiver.py
from flask import Flask, request, jsonify

# Create a new Flask application
app = Flask(__name__)

# Define an endpoint that accepts POST requests at the /webhook URL
@app.route('/webhook', methods=['POST'])
def webhook_listener():
    """
    This function waits for incoming webhooks.
    """
    print("\n--- Webhook Received! ---")
    
    # Check if the incoming request has JSON data
    if request.is_json:
        data = request.get_json()
        print("Data received:")
        print(data)
        return jsonify({"status": "success", "data_received": data}), 200
    else:
        print("Error: Request was not in JSON format.")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

if __name__ == '__main__':
    # Run the app on a different port to avoid conflicts with your main API.
    # Port 5005 is a good choice.
    print("Local webhook receiver is running on http://localhost:5005")
    app.run(port=5005, host='0.0.0.0', debug=True)