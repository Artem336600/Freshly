from flask import Flask, request, jsonify
from openai import OpenAI

# Настройка клиента OpenAI
client = OpenAI(
    api_key="sk-aitunnel-KWqlBaHF6iwBKoPQ0NAtIXEKglXEFDk2",  # Ваш ключ
    base_url="https://api.aitunnel.ru/v1/",
)

app = Flask(__name__)

# Эндпоинт для генерации ответа
@app.route('/generate-fact', methods=['POST'])
def generate_fact():
    try:
        # Получение JSON-данных из запроса
        data = request.json
        user_message = data.get('message', 'Скажи интересный факт')  # Сообщение от пользователя

        # Генерация ответа через OpenAI API
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": user_message}],
            max_tokens=500,  # Укажите нужное количество токенов
            model="gpt-4o-mini"  # Модель
        )

        # Получение текста ответа
        response_message = completion.choices[0].message.content

        # Возврат ответа в формате JSON
        return jsonify({
            "user_message": user_message,
            "response": response_message
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Запуск сервера
if __name__ == '__main__':
    app.run(debug=True)
