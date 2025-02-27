from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from supabase import create_client
from mistralai import Mistral

# Данные для подключения к Supabase
SUPABASE_URL = "https://rgyhaiaecqusymobdqdd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJneWhhaWFlY3F1c3ltb2JkcWRkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczODI0NjkyOCwiZXhwIjoyMDUzODIyOTI4fQ.oZe5DEPVuSCAzeKZxLInsF8iJWXBEGS9I9H6gGMBlmc"
api_key = 'smKrnj6cMHni2QSNHZjIBInPlyErMHSu'
model = "mistral-small-latest"
client = Mistral(api_key=api_key)
# Подключение к Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Инициализация приложения Flask и настройка CORS
app = Flask(__name__)
CORS(app)

# Функция для получения списка продуктов со всеми колонками
def get_products():
    # Выбираем все колонки из таблицы Freshly_products
    response = supabase.table("Freshly_products").select("*").execute()
    return response.data

def iterate_products():
    products = get_products()
    for product in products:
        pass

@app.route('/get_products_info', methods=['POST'])
def get_products_info():
    try:
        products = get_products()
        if not products:
            return jsonify({"error": "Продукты не найдены."}), 404

        # Возвращаем все данные о продуктах как есть
        product_info = [
            {key: value for key, value in product.items()}
            for product in products
        ]
        return jsonify({"products": product_info})
    except Exception as e:
        return jsonify({"error": f"Произошла ошибка: {str(e)}"}), 500


@app.route('/make_prod', methods=['POST'])
def make_dish():
    try:
        # Получаем данные из POST-запроса (ожидаем JSON с полем, например, "message")
        data = request.get_json()
        user_message = data.get('message')

        # Проверяем, что сообщение не пустое
        if not user_message:
            return jsonify({"error": "Ошибка: Введите вопрос."}), 400

        # Формируем системное сообщение
        system_message = "По запросу пользователя ты должен выводить наборы еды по заданной теме, выводи только еду через запятую"
        
        # Отправляем запрос к Mistral
        chat_response = client.chat.complete(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": user_message
                },
            ]
        )

        # Возвращаем ответ в формате JSON
        return jsonify({
            "response": chat_response.choices[0].message.content
        })

    except Exception as e:
        return jsonify({"error": f"Произошла ошибка: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
