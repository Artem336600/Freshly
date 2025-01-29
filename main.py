from flask import Flask, request, jsonify
from mistralai import Mistral
from flask_cors import CORS
import os

# Инициализация приложения Flask
app = Flask(__name__)
CORS(app)  # Разрешаем кросс-доменные запросы (если нужно)

# Инициализация клиента Mistral с API-ключом
api_key = 'smKrnj6cMHni2QSNHZjIBInPlyErMHSu'
model = "mistral-small-latest"
client = Mistral(api_key=api_key)

@app.route('/get_products', methods=['POST'])
def get_products():
    try:
        # Получаем сообщение от пользователя
        user_message = request.json.get('message')
        
        if not user_message:
            return jsonify({"error": "Пожалуйста, отправьте сообщение."}), 400

        # Запрос к Mistral для получения ответа
        chat_response = client.chat.complete(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Ты профессиональный подборщик продуктов под каждый запрос пользователя, какую-бы тему он не ввёл, ты выдаёшь ему список продуктов питания подходящих по этой теме, выводи только продукты в стобик, никакого лишнего текста, только продукты, выводи в столбик пронумерованными, выводи всегда 20 продуктов. Предлагай только реальные блюда. Из еды ты можешь предлагать только: Говно, говно голубиное, китаец",
                },
                {
                    "role": "user",
                    "content": user_message
                },
            ]
        )
        
        # Отправляем ответ пользователю
        return jsonify({
            "response": chat_response.choices[0].message.content
        })
    
    except Exception as e:
        return jsonify({"error": f"Произошла ошибка: {str(e)}"}), 500

# Запуск сервера
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
