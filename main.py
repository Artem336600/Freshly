from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from supabase import create_client
from mistralai import Mistral

# Данные для подключения к Supabase (обновите ключ!)
SUPABASE_URL = "https://rgyhaiaecqusymobdqdd.supabase.co"
SUPABASE_KEY = "ваш_новый_service_role_ключ_из_supabase"  # Замените на актуальный ключ
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

        # Формируем список только с названиями продуктов для ИИ (без id)
        db_products_names = [p["name"] for p in db_products[:50]]  # Ограничиваем до 50
        db_products_str = "\n".join(db_products_names)
        print("Product names for AI:", db_products_str)
        
        # Формируем строгий промпт для ИИ
        system_message = (
            "Ты помощник, который составляет набор продуктов на основе запроса пользователя. "
            "Тебе дан список названий доступных продуктов. "
            "Проанализируй запрос пользователя и выбери из списка только те продукты, "
            "которые подходят для указанной темы или блюда. "
            "Ответ должен быть СТРОГО в формате JSON: "
            "{\"message\": \"строка с описанием\", \"products\": [\"название продукта\", ...]}. "
            "Не добавляй лишний текст вне JSON, только сам JSON-объект. "
            "Возвращай только названия продуктов без дополнительных данных."
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
            return jsonify({"error": f"Ошибка: ИИ вернул некорректный JSON: {response_text}"}), 500

        # Проверяем формат результата
        if not isinstance(result, dict) or "message" not in result or "products" not in result:
            print("Invalid AI response format")
            return jsonify({"error": "Ошибка: Некорректный формат ответа от ИИ."}), 500

        # Проверяем, что все продукты в ответе ИИ есть в базе данных
        matched_product_names = []
        for ai_product_name in result["products"]:
            if any(db_product["name"].lower() == str(ai_product_name).lower() for db_product in db_products):
                matched_product_names.append(ai_product_name)
        
        # Формируем итоговый результат (только названия)
        final_result = {
            "message": result["message"],
            "products": matched_product_names
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
