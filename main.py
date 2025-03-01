from flask import Flask, request, jsonify, send_from_directory
import requests
import json
import re
import time
from bs4 import BeautifulSoup
import threading
import webbrowser
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.')
SERVER_URL = "https://freshly-production.up.railway.app/make_prod"

def fetch_product_info(product_name, category):
    search_url = f"https://www.google.com/search?q={product_name}+Яндекс+Лавка"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        link = None
        for a in soup.find_all("a", href=True):
            if "lavka.yandex.ru" in a["href"]:
                link = re.sub(r'^/url\?q=([^&]+).*', r'\1', a["href"])
                break

        if not link:
            logger.warning(f"Не найдена ссылка на Яндекс Лавку для '{product_name}'")
            return {
                "name": product_name,
                "category": category,
                "price": "Цена не найдена",
                "description": "Описание отсутствует",
                "image": "https://via.placeholder.com/150"
            }

        product_response = requests.get(link, headers=headers, timeout=10)
        product_soup = BeautifulSoup(product_response.text, 'html.parser')

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

        return {
            "name": product_name,
            "category": category,
            "price": price,
            "description": description,
            "image": img_src
        }
    except Exception as e:
        logger.error(f"Ошибка при получении данных для '{product_name}': {e}")
        return {
            "name": product_name,
            "category": category,
            "price": "Цена не найдена",
            "description": "Описание отсутствует",
            "image": "https://via.placeholder.com/150"
        }

@app.route('/')
def serve_index():
    logger.debug("Запрос к /")
    return send_from_directory('.', 'index.html')

@app.route('/make_prod', methods=['POST'])
def make_prod():
    logger.debug("Запрос к /make_prod")
    data = request.get_json()
    message = data.get('message')
    headers = {"Content-Type": "application/json"}
    response = requests.post(SERVER_URL, headers=headers, json={"message": message})
    if response.status_code == 200:
        return jsonify(response.json())
    logger.error(f"Ошибка сервера: {response.status_code}")
    return jsonify({"error": "Ошибка сервера"}), 500

@app.route('/get_product', methods=['POST'])
def get_product():
    logger.debug("Запрос к /get_product")
    data = request.get_json()
    product_name = data.get('name')
    category = data.get('category')
    product_info = fetch_product_info(product_name, category)
    return jsonify(product_info)

def run_server():
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    logger.info("Локальный сервер запущен на http://localhost:5000")
    time.sleep(3)  # Увеличили задержку до 3 секунд
    webbrowser.open("http://localhost:5000")
