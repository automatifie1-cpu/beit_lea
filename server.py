from flask import Flask, request, jsonify
from google_sheets_utils import *
from whatsApp import *
import config

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True) or {}

    # Try to extract WhatsApp message text and sender
    incoming_message = None
    user_phone = None
    text_body = None

    for entry in data.get('entry', []):
        for change in entry.get('changes', []):
            value = change.get('value', {})
            messages = value.get('messages') or []
            if messages:
                candidate = messages[0]
                user_phone = candidate.get('from')
                text_body = (candidate.get('text') or {}).get('body')
                incoming_message = candidate
                break
        if incoming_message:
            break

    if not incoming_message:
        return jsonify({'status': 'no message'}), 200

    # Print or log the message and sender (for demo)
    print(f"Received WhatsApp message from {user_phone}: {text_body}")


    if (not check_if_phone_number_exists(user_phone)):
        send_message(user_phone, config.WELCOME_MESSAGE)
    else:
        add_new_request(user_phone, incoming_message)
        send_message(user_phone, config.RETURNING_MESSAGE)




    return jsonify({'status': 'received'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)