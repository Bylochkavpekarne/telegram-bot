import telebot
import os
from dotenv import load_dotenv
from collections import defaultdict
import threading
from datetime import datetime

# Настройка логирования
LOG_FILE = 'logs.txt'

def log_action(action: str, user_id: int = None, details: str = ""):
    """Записывает действие в лог-файл"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user_info = f"User {user_id}" if user_id else "System"
    log_entry = f"[{timestamp}] {user_info} - {action} - {details}\n"
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)

# Инициализация бота
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
MODERATOR_ID = 1955832136

bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()
log_action("SYSTEM", None, "Bot initialized")

# Хранилище для данных
user_albums = defaultdict(list)
active_timers = {}
text_messages = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        log_action("COMMAND", message.from_user.id, f"Used command: {message.text}")
        response = "Привет! Отправь мне:\n- Фото или альбом с текстом\n- Или если ты хочешь связаться с модерацией тогда просто опиши свою проблему\nЯ передам это на модерацию."
        bot.reply_to(message, response)
        log_action("RESPONSE", message.from_user.id, "Sent welcome message")
    except Exception as e:
        log_action("ERROR", message.from_user.id, f"Welcome error: {str(e)}")
        bot.reply_to(message, f"⚠️ Ошибка: {e}")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        user_id = message.from_user.id
        log_action("PHOTO_RECEIVED", user_id, "Started processing photo")
        
        photo = message.photo[-1].file_id
        caption = message.caption if message.caption else "Без описания"
        
        album_key = (user_id, message.media_group_id) if message.media_group_id else (user_id, None)
        user_albums[album_key].append((photo, caption))
        log_action("PHOTO_STORED", user_id, f"Media group: {message.media_group_id or 'single'}")
        
        if message.media_group_id and album_key not in active_timers:
            active_timers[album_key] = True
            threading.Timer(1.5, process_album, args=[album_key]).start()
            log_action("ALBUM_TIMER", user_id, "Started album processing timer")
        elif not message.media_group_id:
            process_single_photo(album_key)
            
    except Exception as e:
        log_action("ERROR", message.from_user.id, f"Photo handling error: {str(e)}")
        bot.reply_to(message, f"⚠️ Ошибка: {e}")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    try:
        user_id = message.from_user.id
        text = message.text
        log_action("TEXT_RECEIVED", user_id, f"Text length: {len(text)} chars")
        
        # Отправляем подтверждение пользователю
        bot.send_message(user_id, "✅ Ваше сообщение отправлено на модерацию!\n\n")
        log_action("USER_NOTIFIED", user_id, "Sent moderation confirmation")
        
        # Отправляем модератору
        user = bot.get_chat(user_id)
        username = f"@{user.username}" if user.username else f"ID:{user_id}"
        
        bot.send_message(
            MODERATOR_ID,
            f"Новый текст от {username}\n\nТекст: {text}"
        )
        log_action("MODERATOR_NOTIFIED", user_id, "Forwarded text to moderator")
            
    except Exception as e:
        log_action("ERROR", message.from_user.id, f"Text handling error: {str(e)}")
        bot.reply_to(message, f"⚠️ Ошибка: {e}")

def process_album(album_key):
    """Обрабатывает собранный альбом"""
    try:
        if album_key not in user_albums:
            log_action("WARNING", None, f"Album {album_key} not found")
            return
            
        user_id, _ = album_key
        log_action("ALBUM_PROCESSING", user_id, "Starting album processing")
        
        album = user_albums.pop(album_key)
        active_timers.pop(album_key, None)
        
        user = bot.get_chat(user_id)
        username = f"@{user.username}" if user.username else f"ID:{user_id}"
        
        # Отправка подтверждения пользователю
        response_msg = f"✅ Ваш {'альбом' if len(album) > 1 else 'фото'} из {len(album)} {'фото' if len(album) > 1 else ''} отправлен на модерацию!\n\nПри успешной проверке контент будет опубликован.\n❌ Если ваш контент не появится - значит он не прошел модерацию."
        bot.send_message(user_id, response_msg)
        log_action("USER_NOTIFIED", user_id, f"Sent album confirmation ({len(album)} photos)")
        
        # Отправка модератору
        media_group = []
        for i, (photo, caption) in enumerate(album):
            media_group.append(telebot.types.InputMediaPhoto(
                media=photo,
                caption=f"Новый контент от {username}\n\nТекст: {caption}" if i == 0 else None
            ))
        
        bot.send_media_group(MODERATOR_ID, media_group)
        log_action("MODERATOR_NOTIFIED", user_id, f"Sent album to moderator ({len(album)} photos)")
        
    except Exception as e:
        log_action("ERROR", user_id if 'user_id' in locals() else None, f"Album processing error: {str(e)}")

def process_single_photo(album_key):
    """Обрабатывает одиночное фото"""
    try:
        user_id, _ = album_key
        if album_key not in user_albums:
            log_action("WARNING", None, f"Photo {album_key} not found")
            return
            
        log_action("PHOTO_PROCESSING", user_id, "Starting single photo processing")
        
        photo, caption = user_albums.pop(album_key)[0]
        user = bot.get_chat(user_id)
        username = f"@{user.username}" if user.username else f"ID:{user_id}"
        
        # Отправка подтверждения пользователю
        bot.send_message(
            user_id,
            "✅ Ваше фото отправлено на модерацию!\n\n"
            "При успешной проверке контент будет опубликован.\n"
            "❌ Если ваш контент не появится - значит он не прошел модерацию."
        )
        log_action("USER_NOTIFIED", user_id, "Sent photo confirmation")
        
        # Отправка модератору
        bot.send_photo(
            MODERATOR_ID,
            photo,
            caption=f"Новый контент от {username}\n\nТекст: {caption}"
        )
        log_action("MODERATOR_NOTIFIED", user_id, "Sent photo to moderator")
        
    except Exception as e:
        log_action("ERROR", user_id if 'user_id' in locals() else None, f"Photo processing error: {str(e)}")

if __name__ == '__main__':
    try:
        print("Бот запущен...")
        log_action("SYSTEM", None, "Starting bot polling")
        bot.polling(non_stop=True)
    except Exception as e:
        log_action("CRITICAL", None, f"Bot crashed: {str(e)}")
        raise