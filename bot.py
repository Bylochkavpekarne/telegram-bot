import telebot
import os
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime, timedelta

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
MODERATOR_ID = 1955832136  # Замените на реальный ID модератора

bot = telebot.TeleBot(TOKEN)

# Удаляем вебхук перед запуском
bot.remove_webhook()

# Хранилище для группировки сообщений
user_data = defaultdict(list)
last_message_time = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Отправь мне фото с текстом (подписью), и я передам их на модерацию.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        # Получаем фото (берем самое высокое качество)
        photo = message.photo[-1].file_id
        caption = message.caption if message.caption else "Без описания"
        user_id = message.from_user.id
        
        # Добавляем фото в хранилище
        user_data[user_id].append((photo, caption))
        last_message_time[user_id] = datetime.now()
        
        # Отправляем подтверждение пользователю
        bot.reply_to(message, 
                    "✅ Ваши фото/цитаты отправлены на проверку. При успешной модерации ваш контент будет опубликован.\n\n"
                    "❌ Если ваш контент не появился, значит он не прошел проверку модерации!")
        
        # Проверяем, нужно ли отправлять модератору (ждем 5 секунд для группировки)
        if datetime.now() - last_message_time[user_id] > timedelta(seconds=5):
            send_to_moderator(user_id)
            
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка: {e}")

def send_to_moderator(user_id):
    if user_id not in user_data or not user_data[user_id]:
        return
    
    # Получаем информацию о пользователе
    user = bot.get_chat(user_id)
    username = user.username if user.username else "Нет username"
    
    # Создаем медиагруппу
    media = []
    for i, (photo, caption) in enumerate(user_data[user_id]):
        if i == 0:
            # Первое фото с подписью
            media.append(telebot.types.InputMediaPhoto(
                media=photo,
                caption=f"Новый контент на модерацию от @{username} (ID: {user_id})\n\nТекст: {caption}"
            ))
        else:
            # Остальные фото без подписи (или с кратким описанием)
            media.append(telebot.types.InputMediaPhoto(media=photo))
    
    # Отправляем альбом модератору
    bot.send_media_group(MODERATOR_ID, media)
    
    # Очищаем данные пользователя
    del user_data[user_id]
    del last_message_time[user_id]

# Запускаем проверку каждые 5 секунд
import threading

def check_pending_messages():
    while True:
        now = datetime.now()
        for user_id in list(last_message_time.keys()):
            if now - last_message_time[user_id] > timedelta(seconds=5):
                send_to_moderator(user_id)
        threading.Event().wait(5)

thread = threading.Thread(target=check_pending_messages)
thread.daemon = True
thread.start()

if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(non_stop=True)