from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import re
from supabase import create_client
from mistralai import Mistral

# Данные для подключения к Supabase (обновите ключ!)
SUPABASE_URL = "https://rgyhaiaecqusymobdqdd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJneWhhaWFlY3F1c3ltb2JkcWRkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczODI0NjkyOCwiZXhwIjoyMDUzODIyOTI4fQ.oZe5DEPVuSCAzeKZxLInsF8iJWXBEGS9I9H6gGMBlmc"  # Замените на актуальный ключ
api_key = 'smKrnj6cMHni2QSNHZjIBInPlyErMHSu'
model = "mistral-small-latest"
client = Mistral(api_key=api_key)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
CORS(app)

DISH_CATEGORIES = ["Закуски", "Супы", "Основные блюда", "Гарниры", "Десерты", "Напитки", "Салаты", "Блюда на гриле"]

def get_products():
    response = supabase.table("Freshly_products").select("*").execute()
    return response.data

@app.route('/make_prod', methods=['POST'])
def make_dish():
    try:
        data = request.get_json()
        user_message = data.get('message')
        
        if not user_message:
            return jsonify({"error": "Ошибка: Введите вопрос."}), 400

        # Извлекаем количество для каждой категории
        lines = user_message.split('\n')
        category_counts = {}
        for line in lines:
            if "Категории:" in line:
                categories_part = line.split("Категории:")[1].strip()
                categories = categories_part.split(", ")
                for cat in categories:
                    name, count = cat.split(":")
                    category_counts[name.strip()] = int(count.strip())
                break

        db_products = get_products()
        if not db_products:
            return jsonify({"error": "База данных пуста."}), 404

        db_products_names = [p["name"] for p in db_products]
        db_products_str = "\n".join(db_products_names)
        
        instructions = []
        for category in DISH_CATEGORIES:
            count = category_counts.get(category, 0)
            if count > 0:
                instructions.append(f"выбери ровно {count} продукт(ов) для категории '{category}'")
        
        system_message = (
            f"Ты помощник, который составляет набор продуктов на основе запроса пользователя. "
            f"Тебе дан список названий доступных продуктов. "
            f"Проанализируй запрос пользователя и выполни следующие инструкции: "
            f"{'; '.join(instructions)}. "
            f"Ответ должен быть СТРОГО в формате JSON: "
            f"\"message\": \"строка с описанием\", \"products\": [\"название продукта\", ...]}}. "
            f"Не добавляй лишний текст вне JSON, только сам JSON-объект."
        )
        user_prompt = (
            f"Запрос пользователя: {user_message}\n"
            f"Список всех продуктов:\n{db_products_str}\n\n"
            f"Выбери продукты согласно инструкциям выше и верни их в формате JSON."
        )

        chat_response = client.chat.complete(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ]
        )
        response_text = chat_response.choices[0].message.content.strip()

        cleaned_response = re.sub(r'```json\s*|\s*```', '', response_text).strip()
        result = json.loads(cleaned_response)

        if not isinstance(result, dict) or "message" not in result or "products" not in result:
            return jsonify({"error": "Ошибка: Некорректный формат ответа от ИИ."}), 500

        # Формируем результат с названиями и изображениями
        matched_products = []
        for ai_product_name in result["products"]:
            for db_product in db_products:
                if db_product["name"].lower() == str(ai_product_name).lower():
                    matched_products.append({
                        "name": db_product["name"],
                        "img": db_product.get("img", "")  # Берем img, если есть, иначе пустая строка
                    })
                    break

        total_required = sum(category_counts.values())
        if len(matched_products) < total_required:
            return jsonify({"error": f"Ошибка: ИИ вернул меньше продуктов ({len(matched_products)}), чем требуется ({total_required})."}), 500

        final_result = {
            "message": result["message"],
            "products": matched_products[:total_required]
        }
        return jsonify(final_result)

    except Exception as e:
        return jsonify({"error": f"Произошла ошибка: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
