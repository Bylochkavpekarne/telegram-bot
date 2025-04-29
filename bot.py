import telebot
import os
from dotenv import load_dotenv
from collections import defaultdict
import threading

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
MODERATOR_ID = 1955832136

bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

# Хранилище для альбомов
user_albums = defaultdict(list)
active_timers = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Отправь мне фото или альбом с текстом, и я передам их на модерацию.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        user_id = message.from_user.id
        photo = message.photo[-1].file_id
        caption = message.caption if message.caption else "Без описания"
        
        # Ключ для группировки: user_id + media_group_id (если есть)
        album_key = (user_id, message.media_group_id) if message.media_group_id else (user_id, None)
        
        # Добавляем фото в альбом
        user_albums[album_key].append((photo, caption))
        
        # Для альбомов: запускаем таймер только один раз
        if message.media_group_id and album_key not in active_timers:
            active_timers[album_key] = True
            threading.Timer(1.5, process_album, args=[album_key]).start()
        # Для одиночных фото: обрабатываем сразу
        elif not message.media_group_id:
            process_single_photo(album_key)
            
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка: {e}")

def process_album(album_key):
    """Обрабатывает собранный альбом"""
    if album_key not in user_albums:
        return
        
    user_id, _ = album_key
    album = user_albums.pop(album_key)
    active_timers.pop(album_key, None)
    
    user = bot.get_chat(user_id)
    username = f"@{user.username}" if user.username else f"ID:{user_id}"
    
    # Отправляем ОДНО подтверждение пользователю
    bot.send_message(
        user_id,
        f"✅ Ваш {'альбом' if len(album) > 1 else 'фото'} из {len(album)} {'фото' if len(album) > 1 else ''} отправлен на модерацию!\n\n"
        "При успешной проверке контент будет опубликован.\n"
        "❌ Если не появится - значит не прошел модерацию."
    )
    
    # Отправляем модератору
    media_group = []
    for i, (photo, caption) in enumerate(album):
        media_group.append(telebot.types.InputMediaPhoto(
            media=photo,
            caption=f"Новый контент от {username}\n\nТекст: {caption}" if i == 0 else None
        ))
    
    bot.send_media_group(MODERATOR_ID, media_group)

def process_single_photo(album_key):
    """Обрабатывает одиночное фото"""
    user_id, _ = album_key
    if album_key not in user_albums:
        return
        
    photo, caption = user_albums.pop(album_key)[0]
    user = bot.get_chat(user_id)
    username = f"@{user.username}" if user.username else f"ID:{user_id}"
    
    # Отправляем ОДНО подтверждение
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

if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(non_stop=True)