import telebot
from mistralai import Mistral
import os

# Токены
TELEGRAM_BOT_TOKEN = "7636254297:AAEm_lZy-jTh4Fr4IyPF6E1PnDl2nhST-4s"
MISTRAL_API_KEY = "Gy8V6H6HISYNmSmgV2Qy6jNd5XUD843K"

# Инициализация бота и Mistral
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
mistral_client = Mistral(api_key=MISTRAL_API_KEY)

# Старт для канала
@bot.channel_post_handler(commands=['start'])
def send_welcome_channel(message):
    bot.reply_to(message, "Здарова, пиздец! Я Эполит, деревенский мудила. Ща буду пиздец как комментить всё в вашем сраном канале, держитесь, лошары!")

# Старт для лички
@bot.message_handler(commands=['start'])
def send_welcome_private(message):
    bot.reply_to(message, "Ну чё, привет, чмошник! Я Эполит, быдло с деревни. Пиши, хули, а я буду пиздец как отвечать!")

# Обработка сообщений в канале
@bot.channel_post_handler(content_types=['text'])
def handle_channel_message(message):
    user_message = message.text
    if user_message.startswith('/'):
        return
    reply = get_mistral_response(user_message)
    bot.reply_to(message, reply)

# Обработка личных сообщений
@bot.message_handler(content_types=['text'])
def handle_private_message(message):
    user_message = message.text
    if user_message.startswith('/'):
        return
    reply = get_mistral_response(user_message)
    bot.reply_to(message, reply)

# Функция для ответа от Mistral
def get_mistral_response(user_message):
    prompt = f"""
    отвечай на русском
    отвечай на сообщение как будто ты очень высокомерный мажор и всех презераешь за бедность, а ещё ты ненавидишь цыган и всех с ними сравниваешь, никогда не объясняй свой ответ
    Сообщение: {user_message}
    """
    print(f"Получил хуйню: {user_message}")  # Отладка
    try:
        chat_response = mistral_client.chat.complete(
            model="mistral-medium",  # Можно поменять на mixtral-8x7b, если доступно
            messages=[{"role": "user", "content": prompt}]
        )
        reply = chat_response.choices[0].message.content
        print(f"Отвечаю хуйню: {reply}")  # Отладка
        return reply
    except Exception as e:
        error_msg = f"Ёб твою мать, всё сломалось! Ошибка: {str(e)}"
        print(error_msg)  # Отладка
        return error_msg

# Запуск
if __name__ == "__main__":
    print("Эполит, мать его, активирован!")
    bot.polling(non_stop=True)
