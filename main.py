import os
import time
import requests
import logging
from telegram import Bot
from telegram.ext import Updater, CommandHandler, CallbackContext

# --- Конфигурация ---
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
WB_API_KEY = os.getenv("WB_API_KEY")

ALLOWED_USERS = [
    7581299433,   # @zariipov57
    1192402262,   # @dk_smile
    633668083,    # @stas_pw
    1142902789    # @khabibulliin
]

last_review_id = None
last_question_id = None

bot = Bot(token=TG_BOT_TOKEN)
updater = Updater(token=TG_BOT_TOKEN)
dispatcher = updater.dispatcher

def is_authorized(user_id: int) -> bool:
    return user_id in ALLOWED_USERS

def start(update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Доступ запрещён.")
        return
    context.bot.send_message(chat_id=update.effective_chat.id, text="🤖 Бот активен. Ожидайте уведомлений!")

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

def check_wb():
    global last_review_id, last_question_id
    headers = {"Authorization": WB_API_KEY}

    # --- Отзывы ---
    reviews_url = "https://feedbacks-api.wildberries.ru/api/v1/feedbacks"
    params = {"isAnswered": False, "take": 10, "skip": 0}
    try:
        res = requests.get(reviews_url, headers=headers, params=params)
        reviews = res.json().get("data", [])
        for r in reviews:
            r_id = r.get("id")
            if r_id != last_review_id:
                last_review_id = r_id
                msg = (
                    f"📝 Новый отзыв:

"
                    f"{r.get('text')}

"
                    f"Товар: {r.get('productDetails', {}).get('supplierArticle', '')}"
                )
                for uid in ALLOWED_USERS:
                    bot.send_message(chat_id=uid, text=msg)
    except Exception as e:
        logging.warning(f"Ошибка при получении отзывов: {e}")

    # --- Вопросы ---
    questions_url = "https://feedbacks-api.wildberries.ru/api/v1/questions"
    try:
        res = requests.get(questions_url, headers=headers, params={"isAnswered": False, "take": 10})
        questions = res.json().get("data", [])
        for q in questions:
            q_id = q.get("id")
            if q_id != last_question_id:
                last_question_id = q_id
                msg = (
                    f"❓ Новый вопрос:

"
                    f"{q.get('text')}

"
                    f"Товар: {q.get('productDetails', {}).get('supplierArticle', '')}"
                )
                for uid in ALLOWED_USERS:
                    bot.send_message(chat_id=uid, text=msg)
    except Exception as e:
        logging.warning(f"Ошибка при получении вопросов: {e}")

def polling_loop():
    while True:
        check_wb()
        time.sleep(180)  # каждые 3 минуты

if __name__ == "__main__":
    import threading
    threading.Thread(target=polling_loop).start()
    updater.start_polling()
    updater.idle()