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
from selenium.common.exceptions import WebDriverException

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

        # Настройка веб-драйвера
        chrome_options = Options()
        # Закомментируем headless для теста
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            logger.info("Chromedriver initialized successfully")
        except WebDriverException as e:
            logger.error(f"Failed to initialize chromedriver: {str(e)}")
            return jsonify({"error": f"Ошибка инициализации chromedriver: {str(e)}"}), 500

        try:
            matched_products = []
            start_time = time.time()

            for product in ai_result["products"]:
                if time.time() - start_time > 120:
                    logger.warning("Превышен общий лимит времени парсинга")
                    break

                user_product = product["name"]
                category = product["category"]
                search_url = f"https://lavka.yandex.ru/search?text={user_product}"
                
                logger.info(f"Searching for: {user_product} at {search_url}")
                driver.get(search_url)
                time.sleep(5)  # Ждём загрузки страницы поиска

                page_source = driver.page_source
                logger.info(f"Page source excerpt for '{user_product}': {page_source[:1000]}")

                if "Are you not a robot?" in page_source:
                    logger.warning(f"Captcha detected for '{user_product}'")
                    product_data = {
                        "name": user_product,
                        "category": category,
                        "price": "Цена не найдена (капча)",
                        "description": "Описание отсутствует (капча)",
                        "image": "https://via.placeholder.com/150"
                    }
                    matched_products.append(product_data)
                    continue

                try:
                    element = driver.find_element(By.CLASS_NAME, "cbuk31w.pyi2ep2.l1ucbhj1.v1y5jj7x")
                    link_element = element.find_element(By.TAG_NAME, "a")
                    link_href = link_element.get_attribute("href")
                    full_url = link_href if link_href.startswith("https://") else f"https://lavka.yandex.ru{link_href}"
                    link_text = link_element.text.strip() or user_product

                    logger.info(f"Navigating to product page: {full_url}")
                    driver.get(full_url)
                    time.sleep(10)  # Ждём загрузки страницы товара

                    page_source = driver.page_source
                    logger.info(f"Product page source for '{link_text}': {page_source[:2000]}")  # Увеличим отрывок для отладки

                    price = "Цена не найдена"
                    try:
                        price_element = driver.find_element(By.CLASS_NAME, "c17r1xrr")
                        price_text = price_element.text
                        price_match = re.search(r'(\d+\s*₽)', price_text)
                        price = price_match.group(1) if price_match else "Цена не найдена"
                    except:
                        logger.warning(f"Price element 'c17r1xrr' not found for '{link_text}'")

                    description = "Описание отсутствует"
                    try:
                        desc_element = driver.find_element(By.CLASS_NAME, "c17r1xrr")
                        description = re.sub(r'.*₽.*$', '', desc_element.text, flags=re.MULTILINE).strip()
                        description = re.sub(r'В корзину', '', description).strip() or "Описание отсутствует"
                    except:
                        logger.warning(f"Description element 'c17r1xrr' not found for '{link_text}'")

                    img_src = "https://via.placeholder.com/150"
                    try:
                        image_container = driver.find_element(By.CLASS_NAME, "ibhxbmx.p1wkliaw")
                        img_src = image_container.find_element(By.TAG_NAME, "img").get_attribute("src")
                    except:
                        logger.warning(f"Image element 'ibhxbmx.p1wkliaw' not found for '{link_text}'")

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
