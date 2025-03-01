from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import json
import re
import logging
from mistralai import Mistral

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Данные для подключения к Mistral
api_key = 'smKrnj6cMHni2QSNHZjIBInPlyErMHSu'
model = "mistral-small-latest"
client = Mistral(api_key=api_key)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

DISH_CATEGORIES = ["Закуски", "Супы", "Основные блюда", "Гарниры", "Десерты", "Напитки", "Салаты", "Блюда на гриле"]

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/make_prod', methods=['POST', 'OPTIONS'])
def make_prod():
    if request.method == 'OPTIONS':
        return make_response('', 200)

    try:
        data = request.get_json()
        user_message = data.get('message')
        logger.info(f"Received message: {user_message}")
        
        if not user_message:
            logger.warning("No message provided")
            return jsonify({"error": "Ошибка: Введите вопрос."}), 400

        system_message = (
            f"Ты помощник по подбору еды для Smart Food Ecosystem. "
            f"На основе запроса пользователя сформируй продуктовый набор, придумывая названия продуктов. "
            f"Учитывай категории, теги и пожелания из запроса. "
            f"Ответ должен быть в формате JSON: "
            f"\"message\": \"Подобраны продукты\", \"products\": [{{\"name\": \"название продукта\", \"category\": \"категория\"}}, ...]}}. "
            f"Если в запросе указаны категории с количеством, возвращай точное число продуктов для каждой категории. "
            f"Если категорий нет, возвращай минимум 3 продукта."
        )
        user_prompt = f"Запрос пользователя: {user_message}"
        logger.info(f"Prompt length: {len(user_prompt)}")

        chat_response = client.chat.complete(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ]
        )
        response_text = chat_response.choices[0].message.content.strip()
        logger.info(f"Raw AI response: {response_text}")

        cleaned_response = re.sub(r'```json\s*|\s*```', '', response_text).strip()
        ai_result = json.loads(cleaned_response)
        logger.info(f"Parsed AI response: {json.dumps(ai_result, ensure_ascii=False)}")

        if not isinstance(ai_result, dict) or "message" not in ai_result or "products" not in ai_result:
            logger.error("Invalid AI response format")
            return jsonify({"error": "Ошибка: Некорректный формат ответа от ИИ."}), 500

        return jsonify(ai_result)

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        return jsonify({"error": f"Произошла ошибка: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
