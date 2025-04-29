import telebot
import os
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime, timedelta
import threading

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
MODERATOR_ID = 1955832136  # Замените на реальный ID модератора

bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

# Хранилище для группировки сообщений
user_data = defaultdict(list)
last_message_time = {}
pending_confirmation = defaultdict(bool)

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
        
        # Если это первое фото в альбоме, запускаем таймер подтверждения
        if not pending_confirmation[user_id]:
            pending_confirmation[user_id] = True
            threading.Timer(3.0, send_user_confirmation, args=[user_id]).start()
            
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка: {e}")

def send_user_confirmation(user_id):
    """Отправляет одно подтверждение на весь альбом"""
    if user_id not in user_data or not user_data[user_id]:
        return
    
    count = len(user_data[user_id])
    if count > 1:
        text = f"✅ Ваш альбом из {count} фото отправлен на модерацию!\n\n"
    else:
        text = "✅ Ваше фото отправлено на модерацию!\n\n"
    
    text += "При успешной проверке контент будет опубликован.\n"
    text += "❌ Если не появится - значит не прошел модерацию."
    
    bot.send_message(user_id, text)
    pending_confirmation[user_id] = False
    send_to_moderator(user_id)

def send_to_moderator(user_id):
    if user_id not in user_data or not user_data[user_id]:
        return
    
    # Получаем информацию о пользователе
    user = bot.get_chat(user_id)
    username = f"@{user.username}" if user.username else f"ID:{user_id}"
    
    # Создаем медиагруппу
    media = []
    for i, (photo, caption) in enumerate(user_data[user_id]):
        if i == 0:
            # Первое фото с подписью
            media.append(telebot.types.InputMediaPhoto(
                media=photo,
                caption=f"Новый контент на модерацию от {username}\n\nТекст: {caption}"
            ))
        else:
            # Остальные фото без подписи
            media.append(telebot.types.InputMediaPhoto(media=photo))
    
    # Отправляем альбом модератору
    bot.send_media_group(MODERATOR_ID, media)
    
    # Очищаем данные пользователя
    del user_data[user_id]
    del last_message_time[user_id]

# Запускаем проверку "зависших" альбомов
def check_pending_albums():
    while True:
        now = datetime.now()
        for user_id in list(last_message_time.keys()):
            if now - last_message_time[user_id] > timedelta(seconds=10):
                if user_id in pending_confirmation and pending_confirmation[user_id]:
                    send_user_confirmation(user_id)
        threading.Event().wait(5)

thread = threading.Thread(target=check_pending_albums)
thread.daemon = True
thread.start()

if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(non_stop=True)