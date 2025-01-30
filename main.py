from flask import Flask, request, jsonify
from mistralai import Mistral
from flask_cors import CORS
import os
from supabase import create_client

# 🔥 Вставь сюда свои данные из Supabase
SUPABASE_URL = "https://rgyhaiaecqusymobdqdd.supabase.co"  # Твой API URL
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJneWhhaWFlY3F1c3ltb2JkcWRkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzgyNDY5MjgsImV4cCI6MjA1MzgyMjkyOH0.rUUTC4oMhBBxAoHR9MNSlV8YpAz4FwRU1p4RaQBhY70"  # Твой API Key

# Подключение к Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Инициализация приложения Flask
app = Flask(__name__)
CORS(app)  # Разрешаем кросс-доменные запросы (если нужно)

# Инициализация клиента Mistral с API-ключом
api_key = 'smKrnj6cMHni2QSNHZjIBInPlyErMHSu'
model = "mistral-small-latest"
client = Mistral(api_key=api_key)

# Функция для получения списка продуктов из базы данных
def get_available_products():
    response = supabase.table("products").select("*").execute()
    return response.data

@app.route('/get_products', methods=['POST'])
def get_products():
    try:
        # Получаем сообщение от пользователя
        user_message = request.json.get('message')

        if not user_message:
            return jsonify({"error": "Пожалуйста, отправьте сообщение."}), 400

        # Получаем список доступных продуктов из базы данных
        products = get_available_products()

        # Если продукты не найдены
        if not products:
            return jsonify({"error": "Не удалось получить продукты из базы данных."}), 500

        # Формируем список продуктов для передачи в запрос к ИИ
        products_list = "\n".join([f"{i+1}. {product['name']}" for i, product in enumerate(products)])  # product['name'] - это название продукта

        # Формируем запрос для ИИ
        user_message_with_products = f"Вот список доступных продуктов:\n{products_list}\nКакие наборы можно из них составить?"

        # Запрос к Mistral для получения ответа
        chat_response = client.chat.complete(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Ты профессиональный подборщик продуктов под каждый запрос пользователя, какую-бы тему он не ввёл, ты выдаёшь ему список продуктов питания подходящих по этой теме, выводи только продукты в столбик, пронумерованными, выводи всегда 20 продуктов."
                },
                {
                    "role": "user",
                    "content": user_message_with_products
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
