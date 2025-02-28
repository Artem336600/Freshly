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
    try:
        response = supabase.table("Freshly_products").select("*").execute()
        print("Products from DB:", len(response.data))
        return response.data
    except Exception as e:
        print(f"Error fetching products: {str(e)}")
        raise

def find_similar_product(requested_name, category, available_products, used_products):
    """Ищет похожий продукт по названию или описанию."""
    keywords = requested_name.lower().split()
    fallback_candidates = []
    for p in available_products:
        if p["name"] in used_products:
            continue
        name_lower = p["name"].lower()
        desc_lower = p.get("description", "").lower()
        if any(kw in name_lower or kw in desc_lower for kw in keywords):
            fallback_candidates.append(p)
    if not fallback_candidates and category:  # Если нет прямого совпадения, ищем по категории
        category_keywords = category.lower().split()
        for p in available_products:
            if p["name"] in used_products:
                continue
            name_lower = p["name"].lower()
            desc_lower = p.get("description", "").lower()
            if any(kw in name_lower or kw in desc_lower for kw in category_keywords):
                fallback_candidates.append(p)
    return random.choice(fallback_candidates) if fallback_candidates else None

@app.route('/make_prod', methods=['POST'])
def make_dish():
    try:
        data = request.get_json()
        user_message = data.get('message')
        print("Received message:", user_message)
        
        if not user_message:
            return jsonify({"error": "Ошибка: Введите вопрос."}), 400

        # Разбираем сообщение пользователя
        lines = user_message.split('\n')
        category_counts = {}
        tags = []
        wishes = ""

        for line in lines:
            if "Категории:" in line:
                categories_part = line.split("Категории:")[1].strip()
                categories = categories_part.split(", ")
                for cat in categories:
                    name, count = cat.split(":")
                    category_counts[name.strip()] = int(count.strip())
            elif "Теги:" in line:
                tags_part = line.split("Теги:")[1].strip()
                tags = [tag.strip() for tag in tags_part.split(",")] if tags_part else []
            elif "Пожелания:" in line:
                wishes = line.split("Пожелания:")[1].strip()

        # Формируем промпт для ИИ (без списка продуктов)
        instructions = []
        total_required = 0
        for category in DISH_CATEGORIES:
            count = category_counts.get(category, 0)
            if count > 0:
                instructions.append(f"{count} продукт(ов) для категории '{category}'")
                total_required += count
        
        system_message = (
            f"Ты креативный помощник по подбору еды для Smart Food Ecosystem. "
            f"Сформируй продуктовые наборы на основе запроса пользователя, не зная доступных продуктов. "
            f"Следуй этим инструкциям: {'; '.join(instructions)}. "
            f"Учитывай теги: {', '.join(tags) if tags else 'нет тегов'} (применяй логику соответствия). "
            f"Учитывай пожелания: '{wishes}' (если пусто, игнорируй). "
            f"Ответ должен быть СТРОГО в формате JSON: "
            f"\"message\": \"Подобраны продукты\", \"products\": [{{\"name\": \"название продукта\", \"category\": \"категория\"}}, ...]}}. "
            f"Возвращай ровно {total_required} продуктов, придумывая их названия на основе категорий, тегов и пожеланий."
        )
        user_prompt = f"Запрос пользователя: {user_message}"
        print("Prompt length:", len(user_prompt))

        # Отправляем запрос к Mistral
        chat_response = client.chat.complete(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ]
        )
        response_text = chat_response.choices[0].message.content.strip()
        print("Raw AI response:", response_text)

        cleaned_response = re.sub(r'```json\s*|\s*```', '', response_text).strip()
        result = json.loads(cleaned_response)
        print("Parsed AI response:", result)

        if not isinstance(result, dict) or "message" not in result or "products" not in result:
            return jsonify({"error": "Ошибка: Некорректный формат ответа от ИИ."}), 500

        # Получаем продукты из базы
        db_products = get_products()
        if not db_products:
            return jsonify({"error": "База данных пуста."}), 404

        db_products_dict = {p["name"].lower(): p for p in db_products}
        matched_products = []
        used_product_names = set()

        # Подбираем реальные продукты или замены
        for ai_product in result["products"]:
            requested_name = ai_product["name"]
            category = ai_product["category"]
            product_name_lower = requested_name.lower()

            # Проверяем, есть ли точное совпадение
            if product_name_lower in db_products_dict and product_name_lower not in used_product_names:
                db_product = db_products_dict[product_name_lower]
                matched_products.append({
                    "name": db_product["name"],
                    "img": db_product.get("img", "")
                })
                used_product_names.add(product_name_lower)
            else:
                # Ищем похожий продукт
                available_products = [p for p in db_products if p["name"].lower() not in used_product_names]
                similar_product = find_similar_product(requested_name, category, available_products, used_product_names)
                if similar_product:
                    matched_products.append({
                        "name": similar_product["name"],
                        "img": similar_product.get("img", "")
                    })
                    used_product_names.add(similar_product["name"].lower())
                else:
                    # Если нет похожего, берем случайный
                    remaining = [p for p in db_products if p["name"].lower() not in used_product_names]
                    if remaining:
                        random_product = random.choice(remaining)
                        matched_products.append({
                            "name": random_product["name"],
                            "img": random_product.get("img", "")
                        })
                        used_product_names.add(random_product["name"].lower())

        final_result = {
            "message": "Подобраны продукты из доступных вариантов",
            "products": matched_products[:total_required]
        }
        print("Returning:", final_result)
        return jsonify(final_result)

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return jsonify({"error": f"Произошла ошибка: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
