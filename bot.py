
import json
import logging
import schedule
import requests
import asyncio
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка конфигурации
with open("wb_bot_config.json", "r") as f:
    CONFIG = json.load(f)

ALLOWED_USERS = CONFIG["allowed_users"]
WB_API_TOKEN = CONFIG["wildberries_api_token"]
SETTINGS_FILE = "user_settings.json"

# Чтение/запись пользовательских настроек
def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

user_settings = load_settings()

def is_allowed(user):
    return f"@{user.username}" in ALLOWED_USERS

# ====== API запросы ======
def get_sales():
    headers = {"Authorization": WB_API_TOKEN}
    date_today = datetime.now().strftime("%Y-%m-%d")
    date_week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    try:
        # Сегодня
        response_today = requests.get(
            f"https://statistics-api.wildberries.ru/api/v1/supplier/sales?dateFrom={date_today}",
            headers=headers
        )
        sales_today = response_today.json()
        qty_today = len(sales_today)
        amount_today = sum(item['forPay'] for item in sales_today)

        # Неделя
        response_week = requests.get(
            f"https://statistics-api.wildberries.ru/api/v1/supplier/sales?dateFrom={date_week}",
            headers=headers
        )
        sales_week = response_week.json()
        qty_week = len(sales_week)
        amount_week = sum(item['forPay'] for item in sales_week)

        return f"💰 Продажи:
Сегодня: {qty_today} шт. — {amount_today} ₽
Неделя: {qty_week} шт. — {amount_week} ₽"
    except Exception as e:
        return f"Ошибка при получении продаж: {e}"

def get_stocks():
    headers = {"Authorization": WB_API_TOKEN}
    try:
        response = requests.get(
            "https://statistics-api.wildberries.ru/api/v1/supplier/stocks",
            headers=headers
        )
        stocks = response.json()
        if not stocks:
            return "Остатков нет 😔"

        msg = "📦 Остатки на складе:
"
        for item in stocks[:15]:
            name = item.get("nmId", "товар")
            qty = item.get("quantity", 0)
            msg += f"- {name}: {qty} шт.
"
        return msg
    except Exception as e:
        return f"Ошибка при получении остатков: {e}"

# ====== Команды ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user):
        await update.message.reply_text("Брат, доступ запрещён ❌")
        return

    keyboard = [
        [KeyboardButton("💰 Продажи"), KeyboardButton("📦 Остатки на складе")],
        [KeyboardButton("🔔 Настройка уведомлений")]
    ]
    await update.message.reply_text("Ассаламу алейкум, брат! Бот работает ✅", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = f"@{user.username}"
    if not is_allowed(user):
        return

    msg = update.message.text
    settings = load_settings()

    if msg == "💰 Продажи":
        await update.message.reply_text(get_sales())
    elif msg == "📦 Остатки на складе":
        await update.message.reply_text(get_stocks())
    elif msg == "🔔 Настройка уведомлений":
        await update.message.reply_text("Выбери режим уведомлений:", reply_markup=ReplyKeyboardMarkup([
            ["✅ Включить все уведомления"],
            ["✉️ Только отзывы и чаты"],
            ["❌ Отключить уведомления"]
        ], resize_keyboard=True))
    elif msg == "✅ Включить все уведомления":
        settings[username] = "all"
        save_settings(settings)
        await update.message.reply_text("Все уведомления включены 🔔")
    elif msg == "✉️ Только отзывы и чаты":
        settings[username] = "reviews"
        save_settings(settings)
        await update.message.reply_text("Включены только отзывы и чаты ✉️")
    elif msg == "❌ Отключить уведомления":
        settings[username] = "off"
        save_settings(settings)
        await update.message.reply_text("Уведомления отключены ❌")


# Планировщик уведомлений раз в 10 минут
async def check_updates_and_notify(app):
    settings = load_settings()
    headers = {"Authorization": WB_API_TOKEN}
    try:
        # Получаем новые отзывы, заказы и т.д. (пока только продажи как пример)
        date_from = (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S")
        response = requests.get(
            f"https://statistics-api.wildberries.ru/api/v1/supplier/sales?dateFrom={date_from}",
            headers=headers
        )
        data = response.json()
        if data:
            for user in ALLOWED_USERS:
                mode = settings.get(user, "all")
                if mode == "off":
                    continue
                chat = await app.bot.get_chat(user)
                text = f"🛒 Новые продажи за 10 минут: {len(data)} шт."
                await app.bot.send_message(chat_id=chat.id, text=text)
    except Exception as e:
        logger.error(f"Ошибка при автообновлении: {e}")

async def scheduled_report(app):
    pass

async def scheduler(app):
    asyncio.create_task(check_updates_and_notify(app))
    while True:
        schedule.run_pending()
        await asyncio.sleep(600)  # каждые 10 минут

async def on_startup(app):
    asyncio.create_task(scheduler(app))

def main():
    app = ApplicationBuilder().token("7581299433:AAEYKFEHSB5PVYgMxlS-cThhw9y2PwCTMS4").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.post_init = on_startup
    app.run_polling()

if __name__ == "__main__":
    main()
