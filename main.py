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

# Функция для получения списка продуктов
def get_products():
    response = supabase.table("Freshly_products").select("name, description, kbju, secondary_tags").execute()
    return response.data

# Функция для выполнения запроса к /make_prod внутри кода
def call_make_prod(user_message):
    system_message = "По запросу пользователя ты должен выводить наборы еды по заданной теме. Перечисли только названия продуктов (каждое с новой строки)."
    chat_response = client.chat.complete(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
    )
    return chat_response.choices[0].message.content

@app.route('/get_products_info', methods=['POST'])
def get_products_info():
    try:
        # Получаем данные из POST-запроса (ожидаем поле "message" для /make_prod)
        data = request.get_json()
        user_message = data.get('message')

        if not user_message:
            return jsonify({"error": "Ошибка: Введите сообщение для поиска продуктов."}), 400

        # Получаем ответ от /make_prod
        make_prod_response = call_make_prod(user_message)
        requested_products = [line.strip() for line in make_prod_response.split('\n') if line.strip()]

        # Получаем продукты из базы
        products = get_products()
        if not products:
            return jsonify({"error": "Продукты в базе не найдены."}), 404

        # Формируем описания и проверяем совпадения с помощью Mistral
        product_descriptions = []
        found_products = []
        
        for product in products:
            product_details = (
                f"Название: {product.get('name', 'Без названия')}, "
                f"Описание: {product.get('description', 'Нет описания')}, "
                f"кбжу: {product.get('кбжу', 'Не указано')}, "
                f"Дополнительные теги: {product.get('secondary_tags', 'Не указано')}"
            )

            # Проверяем, соответствует ли продукт одному из запрошенных
            system_message_match = (
                "Ты эксперт по продуктам. Определи, соответствует ли продукт из данных ниже одному из запрошенных продуктов. "
                "Запрошенные продукты:\n" + "\n".join(requested_products) + "\n"
                "Если да, укажи, какому именно продукту он соответствует (напиши только название), иначе напиши 'Нет совпадения'."
            )
            match_response = client.chat.complete(
                model=model,
                messages=[
                    {"role": "system", "content": system_message_match},
                    {"role": "user", "content": product_details}
                ]
            )
            match_result = match_response.choices[0].message.content.strip()

            # Генерируем описание продукта
            system_message_desc = "Ты эксперт по продуктам. Опиши продукт на русском языке в одном-двух предложениях на основе предоставленных данных."
            desc_response = client.chat.complete(
                model=model,
                messages=[
                    {"role": "system", "content": system_message_desc},
                    {"role": "user", "content": product_details}
                ]
            )

            product_info = {
                "name": product.get("name"),
                "description": desc_response.choices[0].message.content,
                "kbju": product.get("кбжу"),
                "secondary_tags": product.get("secondary_tags"),
                "matched_to": match_result if match_result != "Нет совпадения" else None
            }
            product_descriptions.append(product_info)

            if match_result != "Нет совпадения":
                found_products.append(match_result)

        # Проверяем, все ли запрошенные продукты найдены
        missing_products = [prod for prod in requested_products if prod not in found_products]
        all_found = len(missing_products) == 0

        # Формируем ответ
        response = {
            "products": product_descriptions,
            "requested_products": requested_products,
            "found_products": list(set(found_products)),  # Убираем дубликаты
            "missing_products": missing_products,
            "all_products_found": all_found
        }

        if all_found:
            response["message"] = "Все запрошенные продукты найдены!"

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": f"Произошла ошибка: {str(e)}"}), 500

@app.route('/make_prod', methods=['POST'])
def make_dish():
    try:
        data = request.get_json()
        user_message = data.get('message')

        if not user_message:
            return jsonify({"error": "Ошибка: Введите вопрос."}), 400

        system_message = "По запросу пользователя ты должен выводить наборы еды по заданной теме. Перечисли только названия продуктов (каждое с новой строки)."
        chat_response = client.chat.complete(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
        )

        return jsonify({"response": chat_response.choices[0].message.content})

    except Exception as e:
        return jsonify({"error": f"Произошла ошибка: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
