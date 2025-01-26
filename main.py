from flask import Flask, request, jsonify
import openai
import os
from flask_cors import CORS

# Настройка клиента OpenAI
openai.api_key = "sk-aitunnel-KWqlBaHF6iwBKoPQ0NAtIXEKglXEFDk2"
openai.api_base = "https://api.aitunnel.ru/v1"

app = Flask(__name__)
CORS(app)

port = int(os.environ.get("PORT", 8080))

@app.route('/', methods=['POST'])
def generate_product_set():
    try:
        # Получение JSON-данных из запроса
        data = request.json
        user_message = data.get('message', 'Подбери интересные блюда и ингредиенты на любую тему')

        # Генерация ответа
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": (
                    "Ты — эксперт по кулинарии. Твоя задача: на любой запрос пользователя предлагать блюда, ингредиенты и рецепты, "
                    "адаптируя ответ к теме или запросу. Примеры запросов и твоих ответов:\n"
                    "- Запрос: 'Америка 70-х'\n"
                    "  Ответ: 'Попробуйте приготовить хот-доги, кукурузный хлеб и фруктовый желейный десерт. Для хот-догов вам понадобятся: сосиски, булочки, горчица, кетчуп и солёные огурцы.'\n"
                    "- Запрос: 'Атака титанов'\n"
                    "  Ответ: 'Рекомендуется блюдо, похожее на стейк из аниме: возьмите говядину, картофель, морковь и специи.'\n"
                    "- Запрос: 'Утка по-пекински'\n"
                    "  Ответ: 'Вам понадобятся утка, соевый соус, мёд, рисовая мука и огурцы. Рецепт: обмажьте утку соусом, запекайте на 200°С и подавайте с блинами и овощами.'\n"
                    "Теперь отвечай так на любой запрос!"
                )},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500
        )

        # Получение ответа
        response_message = completion.choices[0].message['content'].strip()
        print(response_message)

        # Возврат ответа
        return jsonify({
            "user_message": user_message,
            "response": response_message
        })

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=port)
