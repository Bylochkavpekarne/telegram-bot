def _log_clearing(self, moderator_id, chat_id):
    """Логирование действия"""
    if not self.log_channel_id:
        return
        
    try:
        moderator = self.bot.get_chat(moderator_id)
        chat = self.bot.get_chat(chat_id)
        log_text = (
            f"🚨 Очистка чата\n"
            f"• Модератор: {moderator.first_name} (@{moderator.username if moderator.username else 'нет'})\n"
            f"• Чат: {chat.title if hasattr(chat, 'title') else 'ЛС'} (ID: {chat.id})"
        )
        self.bot.send_message(self.log_channel_id, log_text)
    except Exception as e:
        print(f"Ошибка логирования: {str(e)}")