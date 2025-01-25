from flask import Flask, request, jsonify
import openai
import os
from flask_cors import CORS  # Импортируем CORS

# Настройка клиента OpenAI
openai.api_key = "sk-aitunnel-KWqlBaHF6iwBKoPQ0NAtIXEKglXEFDk2"  # Ваш ключ
openai.api_base = "https://api.aitunnel.ru/v1/"  # Указываем кастомный URL, если требуется

app = Flask(__name__)

# Разрешаем все домены для CORS (по умолчанию открываем доступ всем)
CORS(app)

# Получение порта из переменных окружения, или использование порта по умолчанию
port = int(os.environ.get("PORT", 8080))

# Эндпоинт для генерации ответа
@app.route('/', methods=['POST'])
def generate_fact():
    try:
        # Получение JSON-данных из запроса
        data = request.json
        user_message = data.get('message', 'Скажи интересный факт')  # Сообщение от пользователя

        # Генерация ответа через OpenAI API
        completion = openai.ChatCompletion.create(
            model="gpt-4",  # Укажите модель
            messages=[{"role": "user", "content": user_message}],
            max_tokens=500  # Укажите нужное количество токенов
        )

        # Получение текста ответа
        response_message = completion.choices[0].message['content'] if 'content' in completion.choices[0].message else "Error in response"

        # Возврат ответа в формате JSON
        return jsonify({
            "user_message": user_message,
            "response": response_message
        })

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": str(e)}), 500

# Запуск сервера
if __name__ == '__main__':
    # Привязка к адресу 0.0.0.0 для доступа извне
    app.run(host="0.0.0.0", port=port)
