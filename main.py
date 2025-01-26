from flask import Flask, request, jsonify
import openai
import os
from flask_cors import CORS

# Настройка клиента OpenAI
openai.api_key = "sk-aitunnel-KWqlBaHF6iwBKoPQ0NAtIXEKglXEFDk2"
openai.api_base = "https://api.aitunnel.ru/v1"

app = Flask(__name__)
CORS(app)

# Получение порта из переменных окружения
port = int(os.environ.get("PORT", 8080))

@app.route('/', methods=['POST'])
def generate_product_set():
    try:
        # Получение JSON-данных из запроса
        data = request.json
        user_message = data.get('message', 'Предложи набор продуктов для ужина')  # Запрос пользователя

        # Генерация ответа с предложением набора продуктов
        completion = openai.ChatCompletion.create(
            model="gpt-4",  
            messages=[
                {"role": "system", "content": "Ты помощник, который предлагает оптимальные наборы продуктов для еды."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500  
        )

        # Получение текста ответа
        response_message = completion.choices[0].message['content'].strip()
        print(response_message)

        # Возврат ответа в формате JSON
        return jsonify({
            "user_message": user_message,
            "response": response_message
        })

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=port)
