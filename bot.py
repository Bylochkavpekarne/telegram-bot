import telebot
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
MODERATOR_ID = 1955832136  # Замените на реальный ID модератора

bot = telebot.TeleBot(TOKEN)

# Удаляем вебхук перед запуском
bot.remove_webhook()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Отправь мне фото с текстом (подписью), и я передам их на модерацию.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        # Получаем фото (берем самое высокое качество)
        photo = message.photo[-1].file_id
        caption = message.caption if message.caption else "Без описания"
        
        # Отправляем подтверждение пользователю
        bot.reply_to(message, 
                    "✅ Ваши фото/цитаты отправлены на проверку. При успешной модерации ваш контент будет опубликован.\n\n"
                    "❌ Если ваш контент не появился, значит он не прошел проверку модерации!")
        
        # Пересылаем модератору
        bot.send_photo(
            MODERATOR_ID, 
            photo, 
            caption=f"Новый контент на модерацию:\n\n"
                    f"От: @{message.from_user.username}\n"
                    f"ID: {message.from_user.id}\n\n"
                    f"Текст: {caption}"
        )
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка: {e}")

if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(non_stop=True)