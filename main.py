from flask import Flask, request, jsonify
from mistralai import Mistral

app = Flask(__name__)

api_key = 'smKrnj6cMHni2QSNHZjIBInPlyErMHSu'
model = "mistral-small-latest"
client = Mistral(api_key=api_key)

@app.route('/get_products', methods=['POST'])
def get_products():
    user_message = request.json.get('message')
    
    chat_response = client.chat.complete(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Ты профессиональный подборщик продуктов под каждый запрос пользователя, какую-бы тему он не ввёл, ты выдаёшь ему список продуктов питания подходящих по этой теме",
            },
            {
                "role": "user",
                "content": user_message
            },
        ]
    )
    
    return jsonify({
        "response": chat_response.choices[0].message.content
    })

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
