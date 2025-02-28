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

        db_products_names = [p["name"] for p in db_products]
        db_products_str = "\n".join(db_products_names)
        
        # Формируем промпт для ИИ
        instructions = []
        total_required = 0
        for category in DISH_CATEGORIES:
            count = category_counts.get(category, 0)
            if count > 0:
                instructions.append(f"выбери ровно {count} продукт(ов) из списка для категории '{category}'")
                total_required += count
        
        system_message = (
            f"Ты помощник по подбору еды для Smart Food Ecosystem. "
            f"При подборк блюд выкручивай стереотипы на максимум. "
            f"Тебе дан список названий доступных продуктов. "
            f"Выбери продукты ТОЛЬКО из этого списка, строго следуя инструкциям: "
            f"{'; '.join(instructions)}. "
            f"Учитывай теги: {', '.join(tags) if tags else 'нет тегов'} (если тег не указан, игнорируй его; используй логику для соответствия). "
            f"Учитывай пожелания: '{wishes}' (если пусто, игнорируй). "
            f"Ответ должен быть СТРОГО в формате JSON: "
            f"\"message\": \"Подобраны продукты\", \"products\": [{{\"name\": \"название продукта\", \"img\": \"URL изображения\"}}, ...]}}. "
            f"Возвращай ровно {total_required} продуктов, не больше и не меньше. Если не можешь найти продукт, выбери подходящий из списка."
        )
        user_prompt = (
            f"Запрос пользователя: {user_message}\n"
            f"Список всех продуктов:\n{db_products_str}\n\n"
            f"Выбери продукты согласно инструкциям выше и верни их в формате JSON."
        )
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

        # Фильтруем и дополняем продукты из базы
        matched_products = []
        for ai_product in result["products"]:
            for db_product in db_products:
                if db_product["name"].lower() == str(ai_product["name"]).lower():
                    matched_products.append({
                        "name": db_product["name"],
                        "img": db_product.get("img", "")
                    })
                    break

        # Если ИИ вернул меньше, чем нужно, дополняем случайными продуктами
        if len(matched_products) < total_required:
            print(f"AI returned {len(matched_products)} products, required {total_required}. Adding fallback products.")
            remaining = total_required - len(matched_products)
            available_products = [p for p in db_products if p["name"] not in [m["name"] for m in matched_products]]
            if available_products:
                random_products = random.sample(available_products, min(remaining, len(available_products)))
                for p in random_products:
                    matched_products.append({
                        "name": p["name"],
                        "img": p.get("img", "")
                    })

        final_result = {
            "message": result["message"],
            "products": matched_products[:total_required]
        }
        print("Returning:", final_result)
        return jsonify(final_result)

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return jsonify({"error": f"Произошла ошибка: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
