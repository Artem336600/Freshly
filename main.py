from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import json
import re
import time
import os
import logging
import random
from mistralai import Mistral
from requests_html import HTMLSession

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Данные для подключения к Mistral
api_key = 'smKrnj6cMHni2QSNHZjIBInPlyErMHSu'
model = "mistral-small-latest"
client = Mistral(api_key=api_key)

# Список прокси (обновите с рабочими)
PROXY_LIST = [
    "http://190.61.88.147:8080",
    "http://185.199.229.156:7492",
    # Добавьте свои прокси
]

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

@app.route('/get_product', methods=['POST', 'OPTIONS'])
def get_product():
    if request.method == 'OPTIONS':
        return make_response('', 200)

    try:
        data = request.get_json()
        user_product = data.get('name')
        category = data.get('category')
        logger.info(f"Fetching product: {user_product} in category: {category}")

        if not user_product or not category:
            logger.warning("Name or category missing")
            return jsonify({"error": "Ошибка: Укажите название продукта и категорию."}), 400

        session = HTMLSession()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        proxies = {"http": random.choice(PROXY_LIST)} if PROXY_LIST else None
        search_url = f"https://lavka.yandex.ru/search?text={user_product}"

        response = session.get(search_url, headers=headers, proxies=proxies, timeout=10)
        response.html.render(timeout=20)  # Рендеринг JavaScript
        logger.info(f"Response status for '{user_product}': {response.status_code}")

        if response.status_code != 200:
            logger.warning(f"Failed to fetch page for '{user_product}': Status {response.status_code}")
            product_data = {
                "name": user_product,
                "category": category,
                "price": "Цена не найдена",
                "description": "Описание отсутствует",
                "image": "https://via.placeholder.com/150"
            }
            return jsonify(product_data)

        soup = response.html
        logger.info(f"Page excerpt for '{user_product}': {soup.text[:1000]}")

        if "Are you not a robot?" in soup.text:
            logger.warning(f"Captcha detected for '{user_product}'")
            product_data = {
                "name": user_product,
                "category": category,
                "price": "Цена не найдена (капча)",
                "description": "Описание отсутствует (капча)",
                "image": "https://via.placeholder.com/150"
            }
            return jsonify(product_data)

        product_div = soup.find("div", class_="cbuk31w pyi2ep2 l1ucbhj1 v1y5jj7x")
        if not product_div:
            logger.warning(f"No product found for '{user_product}'")
            product_data = {
                "name": user_product,
                "category": category,
                "price": "Цена не найдена",
                "description": "Описание отсутствует",
                "image": "https://via.placeholder.com/150"
            }
            return jsonify(product_data)

        name = product_div.find("span", class_="l4t8cc8 a1dq5c6d").text.strip()
        link = product_div.find("a")["href"]
        full_url = link if link.startswith("https://") else f"https://lavka.yandex.ru{link}"

        product_response = session.get(full_url, headers=headers, proxies=proxies, timeout=10)
        product_response.html.render(timeout=20)
        product_soup = product_response.html

        price = "Цена не найдена"
        price_elem = product_soup.find("div", class_="c17r1xrr")
        if price_elem:
            price_text = price_elem.text
            price_match = re.search(r'(\d+\s*₽)', price_text)
            price = price_match.group(1) if price_match else "Цена не найдена"

        description = "Описание отсутствует"
        if price_elem:
            description = re.sub(r'.*₽.*$', '', price_elem.text, flags=re.MULTILINE).strip()
            description = re.sub(r'В корзину', '', description).strip() or "Описание отсутствует"

        img_src = "https://via.placeholder.com/150"
        img_elem = product_soup.find("div", class_="ibhxbmx p1wkliaw")
        if img_elem:
            img = img_elem.find("img")
            if img and "src" in img.attrs:
                img_src = img["src"]

        product_data = {
            "name": name,
            "category": category,
            "price": price,
            "description": description,
            "image": img_src
        }
        logger.info(f"Product info: {json.dumps(product_data, ensure_ascii=False)}")
        return jsonify(product_data)

    except Exception as e:
        logger.error(f"Error fetching '{user_product}': {str(e)}")
        product_data = {
            "name": user_product,
            "category": category,
            "price": "Цена не найдена",
            "description": "Описание отсутствует",
            "image": "https://via.placeholder.com/150"
        }
        return jsonify(product_data)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
