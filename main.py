from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from supabase import create_client

# Данные для подключения к Supabase
SUPABASE_URL = "https://rgyhaiaecqusymobdqdd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJneWhhaWFlY3F1c3ltb2JkcWRkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzgyNDY5MjgsImV4cCI6MjA1MzgyMjkyOH0.rUUTC4oMhBBxAoHR9MNSlV8YpAz4FwRU1p4RaQBhY70"

# Подключение к Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Инициализация приложения Flask и настройка CORS
app = Flask(__name__)
CORS(app)

# Функция для получения списка продуктов с колонками name и img
def get_products():
    # Выбираем только колонки name и img из таблицы Freshly_products
    response = supabase.table("Freshly_products").select("name, img").execute()
    return response.data

@app.route('/get_products_info', methods=['POST'])
def get_products_info():
    try:
        products = get_products()
        if not products:
            return jsonify({"error": "Продукты не найдены."}), 404

        # Формируем список продуктов с полями name и img
        product_info = [
            {
                "name": product.get("name"),
                "img": product.get("img")
            }
            for product in products
        ]
        return jsonify({"products": product_info})
    except Exception as e:
        return jsonify({"error": f"Произошла ошибка: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
