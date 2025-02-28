from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import re
import random
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

def find_similar_product(requested_name, category, available_products, used_products, wishes=""):
    """Ищет похожий продукт по названию, описанию или тематике пожеланий."""
    keywords = requested_name.lower().split()
    wish_keywords = wishes.lower().split() if wishes else []
    fallback_candidates = []

    # Сначала ищем по ключевым словам из названия
    for p in available_products:
        if p["name"] in used_products:
            continue
        name_lower = p["name"].lower()
        desc_lower = p.get("description", "").lower()
        if any(kw in name_lower or kw in desc_lower for kw in keywords):
            fallback_candidates.append(p)

    # Если ничего не найдено, ищем по категории
    if not fallback_candidates and category:
        category_keywords = category.lower().split()
        for p in available_products:
            if p["name"] in used_products:
                continue
            name_lower = p["name"].lower()
            desc_lower = p.get("description", "").lower()
            if any(kw in name_lower or kw in desc_lower for kw in category_keywords):
                fallback_candidates.append(p)

    # Если есть пожелания (например, "Русская еда"), ищем по ним
    if not fallback_candidates and wish_keywords:
        for p in available_products:
            if p["name"] in used_products:
                continue
            name_lower = p["name"].lower()
            desc_lower = p.get("description", "").lower()
            # Проверяем каждое ключевое слово из пожеланий
            matches_wishes = any(kw in name_lower or kw in desc_lower for kw in wish_keywords)
            is_russian = any(kw in ["русская", "русский", "борщ", "пельмени", "щи"] for kw in wish_keywords)
            if matches_wishes:
                # Исключаем "французские" блюда, если запрос на "русскую" еду
                if is_russian and "француз" not in name_lower:
                    fallback_candidates.append(p)
                elif not is_russian:
                    fallback_candidates.append(p)

    # Возвращаем лучший кандидат или случайный из оставшихся
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

        db_products = get_products()
        if not db_products:
            return jsonify({"error": "База данных пуста."}), 404

        # Формируем промпт для ИИ
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
            f"Учитывай пожелания: '{wishes}' (например, если 'Русская еда', предлагай блюда русской кухни; если пусто, игнорируй). "
            f"Ответ должен быть СТРОГО в формате JSON: "
            f"\"message\": \"Подобраны продукты\", \"products\": [{{\"name\": \"название продукта\", \"category\": \"категория\"}}, ...]}}. "
            f"Возвращай не менее {total_required * 2} продуктов, чтобы дать больше вариантов для выбора."
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

        # Подбираем реальные продукты или замены
        matched_products = []
        used_product_names = set()
        db_products_dict = {p["name"].lower(): p for p in db_products}

        for ai_product in result["products"]:
            requested_name = ai_product["name"]
            category = ai_product["category"]
            product_name_lower = requested_name.lower()

            if product_name_lower in db_products_dict and product_name_lower not in used_product_names:
                db_product = db_products_dict[product_name_lower]
                matched_products.append({
                    "name": db_product["name"],
                    "img": db_product.get("img", "")
                })
                used_product_names.add(product_name_lower)
            else:
                available_products = [p for p in db_products if p["name"].lower() not in used_product_names]
                similar_product = find_similar_product(requested_name, category, available_products, used_product_names, wishes)
                if similar_product:
                    matched_products.append({
                        "name": similar_product["name"],
                        "img": similar_product.get("img", "")
                    })
                    used_product_names.add(similar_product["name"].lower())
            if len(matched_products) >= total_required:
                break

        # Если не хватает продуктов
        if len(matched_products) < total_required:
            print(f"Matched {len(matched_products)} products, required {total_required}. Adding fallback.")
            remaining = total_required - len(matched_products)
            available_products = [p for p in db_products if p["name"].lower() not in used_product_names]
            if available_products:
                random_products = random.sample(available_products, min(remaining, len(available_products)))
                for p in random_products:
                    matched_products.append({
                        "name": p["name"],
                        "img": p.get("img", "")
                    })

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
