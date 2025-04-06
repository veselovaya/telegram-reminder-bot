import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime
import dateparser
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()

async def on_startup(dp):
    scheduler.start()


# Клавиатура
kb = ReplyKeyboardMarkup(resize_keyboard=True)
kb.add(KeyboardButton("➕ Добавить напоминание"))

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(
        "Привет! Я бот-напоминалка 🧠\n\n"
        "Напиши напоминание в формате:\n"
        "- `Напомни завтра в 19:00: Позвонить маме`\n"
        "- `Каждый понедельник в 08:30: Зарядка`\n"
        "- `Каждое 15-е число в 12:00: Оплатить телефон`\n",
        parse_mode="Markdown",
        reply_markup=kb
    )

@dp.message_handler(lambda msg: msg.text == "➕ Добавить напоминание")
async def ask_text(message: types.Message):
    await message.answer(
        "Напиши:\n"
        "- `Напомни в [дата/время]: [текст]`\n"
        "- или `Каждый [день/дата] в [время]: [текст]`\n\n"
        "Примеры:\n"
        "- `Напомни 7 апреля в 18:00: Позвонить бабушке`\n"
        "- `Каждый понедельник в 08:00: Утренняя пробежка`\n"
        "- `Каждое 1-е число в 09:00: Подать отчёт`"
    )

@dp.message_handler()
async def handle_input(message: types.Message):
    text = message.text.strip().lower()
    user_id = message.from_user.id

    try:
        if text.startswith("кажд"):
            # Повторяющееся напоминание
            await handle_recurring_reminder(message)
        elif text.startswith("напомни"):
            # Разовое напоминание
            await handle_one_time_reminder(message)
        else:
            await message.answer("Не понял формат. Попробуй снова 🙈")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")

async def handle_one_time_reminder(message):
    content = message.text[7:].strip()
    if ":" not in content:
        await message.answer("Формат: `Напомни [дата и время]: [текст]`")
        return

    when_part, text = content.split(":", 1)
    dt = dateparser.parse(when_part.strip(), languages=["ru"])

    if not dt:
        await message.answer("Не смог понять дату 😢 Попробуй в формате `7 апреля в 18:00`.")
        return

    scheduler.add_job(
        send_reminder,
        DateTrigger(run_date=dt),
        args=[message.chat.id, text.strip()],
    )

    await message.answer(f"✅ Напоминание запланировано на {dt.strftime('%d.%m.%Y %H:%M')}:\n{text.strip()}")

async def handle_recurring_reminder(message):
    text = message.text
    if ":" not in text:
        await message.answer("Формат: `Каждый [день/дата] в [время]: [текст]`")
        return

    before_colon, reminder_text = text.split(":", 1)
    reminder_text = reminder_text.strip()

    if "в" not in before_colon:
        await message.answer("Не понял время напоминания 😕")
        return

    pattern_part, time_part = before_colon.split("в")
    time_part = time_part.strip()
    hour, minute = map(int, time_part.split(":"))

    cron_args = {}

    if "понедельник" in pattern_part:
        cron_args["day_of_week"] = "mon"
    elif "вторник" in pattern_part:
        cron_args["day_of_week"] = "tue"
    elif "среда" in pattern_part:
        cron_args["day_of_week"] = "wed"
    elif "четверг" in pattern_part:
        cron_args["day_of_week"] = "thu"
    elif "пятница" in pattern_part:
        cron_args["day_of_week"] = "fri"
    elif "суббота" in pattern_part:
        cron_args["day_of_week"] = "sat"
    elif "воскресенье" in pattern_part:
        cron_args["day_of_week"] = "sun"
    elif "1-е" in pattern_part or "1е" in pattern_part:
        cron_args["day"] = 1
    elif "15-е" in pattern_part or "15е" in pattern_part:
        cron_args["day"] = 15
    else:
        await message.answer("Не понял шаблон повторения 😅 Попробуй: 'Каждый понедельник', 'Каждое 1-е число'.")
        return

    job_id = f"{message.chat.id}_{reminder_text}_{hour}{minute}"
    scheduler.add_job(
        send_reminder,
        CronTrigger(hour=hour, minute=minute, **cron_args),
        args=[message.chat.id, reminder_text],
        id=job_id,
        replace_existing=True
    )

    await message.answer(f"🔁 Повторяющееся напоминание создано: {reminder_text} в {hour:02}:{minute:02}")

async def send_reminder(chat_id, text):
    await bot.send_message(chat_id, f"⏰ Напоминание: {text}")

if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup)
