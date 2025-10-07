import sys
from flask import Flask, jsonify, request
from daily import CallClient, Daily, EventHandler

app = Flask(__name__)

# Global client instance
call_client = None

class RoomHandler(EventHandler):
    def __init__(self):
        super().__init__()

    def on_app_message(self, message, sender: str) -> None:
        print(f"Incoming app message from {sender}: {message}")

def join_room(url):
    global call_client
    try:
        Daily.init()
        handler = RoomHandler()
        call_client = CallClient(event_handler=handler)
        call_client.join(url)
        print(f"Joined room: {url}")
    except Exception as e:
        print(f"Error joining room: {e}")
        raise

@app.route("/send_text_message", methods=["POST"])
def send_text_message():
    global call_client
    if not call_client:
        return jsonify({"error": "Not connected to a room"}), 400

    try:
        body = request.json
        conversation_id = body.get("conversation_id")
        properties = body.get("properties", {})
        message = {
            "message_type": "conversation",
            "event_type": "conversation.echo",
            "conversation_id": conversation_id,
            "properties": {
                "modality": properties.get("modality"),
                "text": properties.get("text"),
                "audio": properties.get("audio"),
                "sample_rate": properties.get("sample_rate", 16000),
                "inference_id": properties.get("inference_id"),
                "done": properties.get("done")
            }
        }
        call_client.send_app_message(message)
        return jsonify({"status": "Message sent successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to send message: {str(e)}"}), 500

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <conversation_url>")
        sys.exit(1)

    conversation_url = sys.argv[1]
    try:
        join_room(conversation_url)
        app.run(port=8000, debug=True)
    except Exception as e:
        print(f"Failed to start the application: {e}")
        sys.exit(1)