from flask import Flask, request, jsonify
import openai
import os
from flask_cors import CORS

openai.api_key = "your-api-key"  # Укажите ваш ключ API
openai.api_base = "https://api.aitunnel.ru/v1"  # Указываем кастомный URL, если требуется

app = Flask(__name__)

CORS(app)

port = int(os.environ.get("PORT", 8080))

@app.route('/', methods=['POST'])
def generate_fact():
    try:
        data = request.json
        user_message = data.get('message', 'Скажи интересный факт')

        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_message}],
            max_tokens=500
        )

        # Получаем и сразу декодируем текст
        response_message = completion.choices[0].message['content']
        # Декодируем строку, чтобы избежать unicode escape
        response_message = response_message.encode('utf-8').decode('utf-8')

        return jsonify({
            "user_message": user_message,
            "response": response_message
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=port)
