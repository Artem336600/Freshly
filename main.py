from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from supabase import create_client
from mistralai import Mistral

SUPABASE_URL = "https://rgyhaiaecqusymobdqdd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJneWhhaWFlY3F1c3ltb2JkcWRkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczODI0NjkyOCwiZXhwIjoyMDUzODIyOTI4fQ.oZe5DEPVuSCAzeKZxLInsF8iJWXBEGS9I9H6gGMBlmc"
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

def compare_products(ai_generated_list, db_products):
    try:
        matched_products = []
        system_message = "Сравни список запрошенных продуктов с продуктами из базы данных и определи, какие из них максимально близки по смыслу или названию. Возвращай только те продукты из базы данных, которые соответствуют запрошенным. Запрошенные продукты могут не совпадать буквально с названиями в базе данных, используй логику и контекст."
        ai_list_str = ", ".join(ai_generated_list[:10])  # Ограничим до 10 продуктов
        db_products_str = "\n".join([f"{p['name']} (id: {p['id']})" for p in db_products])
        comparison_prompt = f"Запрошенные продукты: {ai_list_str}\nПродукты из базы данных:\n{db_products_str}\n\nКакие продукты из базы данных соответствуют запрошенным?"
        print("Comparison prompt length:", len(comparison_prompt))

        chat_response = client.chat.complete(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": comparison_prompt}
            ]
        )
        response_text = chat_response.choices[0].message.content
        print("AI comparison response:", response_text)

        for product in db_products:
            if str(product['id']) in response_text or product['name'].lower() in response_text.lower():
                matched_products.append(product)
        
        return matched_products
    except Exception as e:
        print(f"Error in compare_products: {str(e)}")
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

        system_message = "По запросу пользователя сформируй список продуктов для закусок (максимум 10 позиций), которые подходят для заданной темы или блюда. Верни только названия продуктов в виде списка, например: ['яблоко', 'мука', 'сахар']."
        chat_response = client.chat.complete(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
        )
        generated_products_text = chat_response.choices[0].message.content
        print("Generated products text:", generated_products_text)
        
        try:
            if generated_products_text.startswith('['):
                generated_products = eval(generated_products_text)
            else:
                generated_products = generated_products_text.split(', ')
            generated_products = [str(p).strip() for p in generated_products[:10]]  # Ограничим до 10 и уберем лишние пробелы
        except Exception as e:
            print("Parse error:", str(e))
            generated_products = generated_products_text.split(', ')[:10]
        print("Parsed generated products:", generated_products)

        db_products = get_products()
        if not db_products:
            print("No products in DB")
            return jsonify({"error": "База данных пуста."}), 404

        matched_products = compare_products(generated_products, db_products)
        print("Matched products:", matched_products)
        
        if not matched_products:
            result = {"message": "Подходящих продуктов в базе данных не найдено.", "products": []}
            print("Returning empty result:", result)
            return jsonify(result)

        product_info = [{key: value for key, value in product.items()} for product in matched_products]
        result = {
            "message": f"Найдены подходящие продукты для запроса '{user_message}'",
            "products": product_info
        }
        print("Returning:", result)
        return jsonify(result)
    except Exception as e:
        error_response = {"error": f"Произошла ошибка: {str(e)}"}
        print("Error occurred:", error_response)
        return jsonify(error_response), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
