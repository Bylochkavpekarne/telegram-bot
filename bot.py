import telebot
import os
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime, timedelta
import threading

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
MODERATOR_ID = 1955832136

bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

# Хранилище для группировки альбомов
user_albums = defaultdict(list)
album_timers = {}
pending_confirmations = set()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Отправь мне фото или альбом с текстом, и я передам их на модерацию.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        user_id = message.from_user.id
        photo = message.photo[-1].file_id
        caption = message.caption if message.caption else "Без описания"
        
        # Если это медиагруппа (альбом), обрабатываем все фото сразу
        if message.media_group_id:
            media_group_id = message.media_group_id
            user_albums[(user_id, media_group_id)].append((photo, caption))
            
            # Запускаем таймер только для первого фото в альбоме
            if (user_id, media_group_id) not in album_timers:
                album_timers[(user_id, media_group_id)] = threading.Timer(
                    2.0, process_album, 
                    args=[user_id, media_group_id]
                )
                album_timers[(user_id, media_group_id)].start()
        else:
            # Одиночное фото
            process_single_photo(user_id, photo, caption)
            
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка: {e}")

def process_album(user_id, media_group_id):
    """Обрабатывает собранный альбом"""
    if (user_id, media_group_id) not in user_albums:
        return
        
    album = user_albums[(user_id, media_group_id)]
    user = bot.get_chat(user_id)
    username = f"@{user.username}" if user.username else f"ID:{user_id}"
    
    # Отправляем подтверждение пользователю
    if len(album) > 1:
        bot.send_message(
            user_id,
            f"✅ Ваш альбом из {len(album)} фото отправлен на модерацию!\n\n"
            "При успешной проверке контент будет опубликован.\n"
            "❌ Если не появится - значит не прошел модерацию."
        )
    else:
        bot.send_message(
            user_id,
            "✅ Ваше фото отправлено на модерацию!\n\n"
            "При успешной проверке контент будет опубликован.\n"
            "❌ Если не появится - значит не прошел модерацию."
        )
    
    # Отправляем модератору
    media_group = []
    for i, (photo, caption) in enumerate(album):
        if i == 0:
            media_group.append(telebot.types.InputMediaPhoto(
                media=photo,
                caption=f"Новый контент от {username}\n\nТекст: {caption}"
            ))
        else:
            media_group.append(telebot.types.InputMediaPhoto(media=photo))
    
    bot.send_media_group(MODERATOR_ID, media_group)
    
    # Очищаем
    del user_albums[(user_id, media_group_id)]
    del album_timers[(user_id, media_group_id)]

def process_single_photo(user_id, photo, caption):
    """Обрабатывает одиночное фото"""
    user = bot.get_chat(user_id)
    username = f"@{user.username}" if user.username else f"ID:{user_id}"
    
    # Отправляем подтверждение
    bot.send_message(
        user_id,
        "✅ Ваше фото отправлено на модерацию!\n\n"
        "При успешной проверке контент будет опубликован.\n"
        "❌ Если не появится - значит не прошел модерацию."
    )
    
    # Отправляем модератору
    bot.send_photo(
        MODERATOR_ID,
        photo,
        caption=f"Новый контент от {username}\n\nТекст: {caption}"
    )

# Запускаем бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(non_stop=True)