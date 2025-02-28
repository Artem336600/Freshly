from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import json
import re
import time
import os
import logging
from mistralai import Mistral
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Данные для подключения к Mistral
api_key = 'smKrnj6cMHni2QSNHZjIBInPlyErMHSu'
model = "mistral-small-latest"
client = Mistral(api_key=api_key)

app = Flask(__name__)
CORS(app, resources={r"/make_prod": {"origins": "*"}})

DISH_CATEGORIES = ["Закуски", "Супы", "Основные блюда", "Гарниры", "Десерты", "Напитки", "Салаты", "Блюда на гриле"]

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/make_prod', methods=['POST', 'OPTIONS'])
def make_dish():
    if request.method == 'OPTIONS':
        return make_response('', 200)

    try:
        data = request.get_json()
        user_message = data.get('message')
        logger.info(f"Received message: {user_message}")
        
        if not user_message:
            logger.warning("No message provided")
            return jsonify({"error": "Ошибка: Введите вопрос."}), 400

        # Формируем промпт для ИИ
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

        # Отправляем запрос к Mistral
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

        # Настройка веб-драйвера
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            logger.info("Chromedriver initialized successfully")
        except WebDriverException as e:
            logger.error(f"Failed to initialize chromedriver: {str(e)}")
            return jsonify({"error": f"Ошибка инициализации chromedriver: {str(e)}"}), 500

        try:
            matched_products = []
            for product in ai_result["products"]:
                user_product = product["name"]
                category = product["category"]
                search_url = f"https://lavka.yandex.ru/search?text={user_product}"
                
                logger.info(f"Searching for: {user_product} at {search_url}")
                driver.get(search_url)
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "cbuk31w"))
                    )
                except TimeoutException as e:
                    logger.warning(f"Timeout waiting for search results for '{user_product}': {str(e)}")
                    product_data = {
                        "name": user_product,
                        "category": category,
                        "price": "Цена не найдена",
                        "description": "Описание отсутствует",
                        "image": "https://via.placeholder.com/150"
                    }
                    matched_products.append(product_data)
                    logger.info(f"Product info: {json.dumps(product_data, ensure_ascii=False)}")
                    continue

                try:
                    element = driver.find_element(By.CLASS_NAME, "cbuk31w.pyi2ep2.l1ucbhj1.v1y5jj7x")
                    link_element = element.find_element(By.CLASS_NAME, "p11oed5n.d1sn7zca")
                    link_href = link_element.get_attribute("href")
                    full_url = link_href if link_href.startswith("https://") else f"https://lavka.yandex.ru{link_href}"
                    link_text = link_element.find_element(By.CLASS_NAME, "l4t8cc8.a1dq5c6d").text

                    logger.info(f"Navigating to product page: {full_url}")
                    driver.get(full_url)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "c17r1xrr"))
                    )

                    product_elements = driver.find_elements(By.CLASS_NAME, "c17r1xrr")
                    price = "Цена не найдена"
                    description = "Описание отсутствует"
                    if product_elements:
                        for elem in product_elements:
                            text_content = elem.text
                            price_match = re.search(r'(\d+\s*₽)', text_content)
                            if price_match:
                                price = price_match.group(1)
                            text_cleaned = re.sub(r'.*₽.*$', '', text_content, flags=re.MULTILINE).strip()
                            text_cleaned = re.sub(r'В корзину', '', text_cleaned).strip()
                            if text_cleaned:
                                description = text_cleaned

                    img_src = "https://via.placeholder.com/150"
                    try:
                        image_container = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CLASS_NAME, "ibhxbmx.p1wkliaw"))
                        )
                        image = image_container.find_element(By.TAG_NAME, "img")
                        img_src = image.get_attribute("src")
                    except TimeoutException as e:
                        logger.warning(f"Image not found for '{link_text}', timeout: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error finding image for '{link_text}': {str(e)}")

                    product_data = {
                        "name": link_text,
                        "category": category,
                        "price": price,
                        "description": description,
                        "image": img_src
                    }
                    matched_products.append(product_data)
                    logger.info(f"Product info: {json.dumps(product_data, ensure_ascii=False)}")

                except Exception as e:
                    logger.error(f"Ошибка при поиске '{user_product}': {str(e)}")
                    product_data = {
                        "name": user_product,
                        "category": category,
                        "price": "Цена не найдена",
                        "description": "Описание отсутствует",
                        "image": "https://via.placeholder.com/150"
                    }
                    matched_products.append(product_data)
                    logger.info(f"Product info: {json.dumps(product_data, ensure_ascii=False)}")

            final_result = {
                "message": "Подобраны продукты с сайта Яндекс Лавка",
                "products": matched_products
            }
            logger.info(f"Returning: {json.dumps(final_result, ensure_ascii=False)}")
            return jsonify(final_result)

        finally:
            driver.quit()

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        return jsonify({"error": f"Произошла ошибка: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
