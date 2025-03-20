import asyncio
import logging
from aiogram import Bot

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен вашего бота
TOKEN = "7539383210:AAGPIzLaR7Fb8xBtsmEAmV0LTws5Rj17O0k"
CHANNEL_ID = "@freshlyoffical"  # ID вашего канала

# Функция для отсчета до микро дропа
async def countdown_to_drop():
    bot = Bot(token=TOKEN, timeout=30)
    try:
        # Начальное значение: 0%
        total_seconds = 300  # 5 минут в секундах
        elapsed_seconds = 0  # Прошедшее время
        percentage = 0  # Начальный процент
        last_percentage = -1  # Последний отправленный процент

        # Отправляем начальное сообщение
        message = await bot.send_message(CHANNEL_ID, f"Микро дроп: {percentage}%")
        message_id = message.message_id

        logging.info(f"Начальный отсчет отправлен: {percentage}%")

        while elapsed_seconds < total_seconds:
            await asyncio.sleep(1)  # Ждем 1 секунду
            elapsed_seconds += 1  # Увеличиваем прошедшее время
            percentage = int((elapsed_seconds / total_seconds) * 100)  # Вычисляем процент

            # Редактируем сообщение только если процент изменился
            if percentage != last_percentage:
                try:
                    await bot.edit_message_text(
                        chat_id=CHANNEL_ID,
                        message_id=message_id,
                        text=f"Микро дроп: {percentage}%"
                    )
                    logging.info(f"Обновлен процент: {percentage}%")
                    last_percentage = percentage  # Обновляем последний отправленный процент
                except Exception as e:
                    logging.error(f"Ошибка при редактировании сообщения: {e}")

        # Завершающее сообщение
        await bot.edit_message_text(
            chat_id=CHANNEL_ID,
            message_id=message_id,
            text="ДРОП"
        )
        logging.info("Отсчет завершен: ДРОП")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
    finally:
        await bot.session.close()

# Запуск бота
async def main():
    await countdown_to_drop()

if __name__ == "__main__":
    asyncio.run(main())
