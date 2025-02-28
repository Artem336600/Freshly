from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from supabase import create_client
from mistralai import Mistral

# Данные для подключения к Supabase
SUPABASE_URL = "https://rgyhaiaecqusymobdqdd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJneWhhaWFlY3F1c3ltb2JkcWRkIiwicm9sZSI6InNlcnZpY6Vfcm9sZSIsImlhdCI6MTczODI0NjkyOCwiZXhwIjoyMDUzODIyOTI4fQ.oZe5DEPVuSCAzeKZxLInsF8iJWXBEGS9I9H6gGMBlmc"
api_key = 'smKrnj6cMHni2QSNHZjIBInPlyErMHSu'
model = "mistral-small-latest"
client = Mistral(api_key=api_key)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
CORS(app)

def get_products():
    try:
        response = supabase.table("Freshly_products").select("*").execute()
        print("Products from DB:", response.data)
        return response.data
    except Exception as e:
        print(f"Error fetching products from DB: {str(e)}")
        raise

@app.route('/make_prod', methods=['POST'])
def make_dish():
    try:
        data = request.get_json()
        user_message = data.get('message')
        print("Received message:", user_message)
        
        if not user_message:
            print("No message provided")
            return jsonify({"error": "Ошибка: Введите вопрос."}), 400

        # Получаем все продукты из базы данных
        db_products = get_products()
        if not db_products:
            print("No products in DB")
            return jsonify({"error": "База данных пуста."}), 404

        # Ограничиваем список продуктов для ИИ (до 50)
        db_products_limited = db_products[:50]
        db_products_str = "\n".join([f"{p['name']} (id: {p['id']})" for p in db_products_limited])
        print("Limited products for AI:", db_products_str)
        
        # Формируем строгий промпт для ИИ
        system_message = (
            "Ты помощник, который составляет набор продуктов на основе запроса пользователя. "
            "Тебе дан список всех доступных продуктов. "
            "Проанализируй запрос пользователя и выбери из списка только те продукты, "
            "которые подходят для указанной темы или блюда. "
            "Ответ должен быть СТРОГО в формате JSON: "
            "{\"message\": \"строка с описанием\", \"products\": [{\"id\": число, \"name\": \"строка\"}, ...]}. "
            "Не добавляй лишний текст вне JSON, только сам JSON-объект."
        )
        user_prompt = (
            f"Запрос пользователя: {user_message}\n"
            f"Список всех продуктов:\n{db_products_str}\n\n"
            "Выбери подходящие продукты и верни их в формате JSON, как указано выше."
        )
        print("Prompt length:", len(user_prompt))

        # Отправляем запрос к Mistral
        try:
            chat_response = client.chat.complete(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt}
                ]
            )
            response_text = chat_response.choices[0].message.content.strip()
            print("Raw AI response:", response_text)
        except Exception as e:
            print(f"Error calling Mistral API: {str(e)}")
            return jsonify({"error": f"Ошибка при обращении к ИИ: {str(e)}"}), 500

        # Парсим ответ ИИ как JSON
        try:
            result = json.loads(response_text)
            print("Parsed AI response:", result)
        except json.JSONDecodeError as e:
            print(f"Error parsing AI response as JSON: {str(e)}")
            # Попытка извлечь данные вручную, если JSON невалиден
            if "message" in response_text and "products" in response_text:
                try:
                    # Грубый парсинг для извлечения JSON-подобной структуры
                    import re
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group(0))
                        print("Manually parsed AI response:", result)
                    else:
                        raise ValueError("No JSON-like structure found")
                except Exception as manual_e:
                    print(f"Manual parsing failed: {str(manual_e)}")
                    return jsonify({"error": f"Ошибка: ИИ вернул некорректный JSON: {response_text}"}), 500
            else:
                return jsonify({"error": f"Ошибка: ИИ вернул некорректный JSON: {response_text}"}), 500

        # Проверяем формат результата
        if not isinstance(result, dict) or "message" not in result or "products" not in result:
            print("Invalid AI response format")
            return jsonify({"error": "Ошибка: Некорректный формат ответа от ИИ."}), 500

        # Фильтруем продукты из базы данных
        matched_products = []
        for ai_product in result["products"]:
            for db_product in db_products:
                if str(db_product["id"]) == str(ai_product.get("id", "")) or db_product["name"].lower() == str(ai_product.get("name", "")).lower():
                    matched_products.append(db_product)
                    break
        
        # Формируем итоговый результат
        final_result = {
            "message": result["message"],
            "products": matched_products
        }
        print("Returning:", final_result)
        response = jsonify(final_result)
        print("Response headers:", response.headers)
        return response

    except Exception as e:
        error_response = {"error": f"Произошла ошибка: {str(e)}"}
        print("Error occurred:", error_response)
        return jsonify(error_response), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
