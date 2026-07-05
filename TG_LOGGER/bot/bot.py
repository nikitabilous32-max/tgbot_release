
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from database import get_db
import time

BOT_TOKEN = "8987195198:AAHv7vh2mDPt81mDK_EDYxHv5AhHrOGJ7YY"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ---------- БАЗА ----------

def get_deleted_chats():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT chat_id FROM messages WHERE deleted = 1")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_deleted_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT user_id, username FROM messages WHERE deleted = 1")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_deleted_usernames():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT username FROM messages WHERE deleted = 1 AND username IS NOT NULL")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_deleted_by_chat(chat_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM messages
        WHERE deleted = 1 AND chat_id = ?
        ORDER BY date DESC
        LIMIT 50
    """, (chat_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_deleted_by_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM messages
        WHERE deleted = 1 AND user_id = ?
        ORDER BY date DESC
        LIMIT 50
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_deleted_by_username(username):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM messages
        WHERE deleted = 1 AND username = ?
        ORDER BY date DESC
        LIMIT 50
    """, (username,))
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------- REPLY-КНОПКИ СНИЗУ ----------

reply_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📁 Чаты"), KeyboardButton(text="👤 Пользователи")],
        [KeyboardButton(text="🔍 Username")]
    ],
    resize_keyboard=True
)


@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    await msg.answer("Выберите действие:", reply_markup=reply_kb)


@dp.message(Command("menu"))
async def menu_cmd(msg: types.Message):
    await msg.answer("Меню открыто:", reply_markup=reply_kb)

@dp.message(Command("clear"))
async def clear_cmd(msg: types.Message):
    await msg.answer("🧹 Очищаю базу и файлы...")

    # --- Удаляем записи из базы ---
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

    # --- Удаляем локальные файлы ---
    media_root = os.path.join(os.path.dirname(__file__), "..", "media")

    removed_files = 0
    for root, dirs, files in os.walk(media_root):
        for f in files:
            try:
                os.remove(os.path.join(root, f))
                removed_files += 1
            except:
                pass

    await msg.answer(f"✔ База очищена\n✔ Удалено файлов: {removed_files}")


# ---------- ОТПРАВКА УДАЛЁННЫХ СООБЩЕНИЙ ----------

async def send_deleted(callback: types.CallbackQuery, rows):
    for r in rows:
        date_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["date"]))

        caption = (
            f"🗑 Удалённое сообщение\n"
            f"📅 Дата: {date_str}\n"
            f"💬 Чат: {r['chat_id']}\n"
            f"👤 Пользователь: {r['username']} ({r['user_id']})\n"
            f"✏️ Текст: {r['text']}\n"
        )

        mt = r["media_type"]
        local_path = r["local_path"]
        chat_id = callback.message.chat.id

        # --- если есть локальный файл ---
        if local_path and os.path.exists(local_path):

            try:
                # КРУЖОЧКИ — caption нельзя, отправляем отдельно
                if mt == "video_note":
                    await bot.send_video_note(chat_id, FSInputFile(local_path))
                    await bot.send_message(chat_id, caption)
                    continue

                # ФОТО
                if mt == "photo":
                    await bot.send_photo(chat_id, FSInputFile(local_path), caption=caption)
                    continue

                # ВИДЕО
                if mt == "video":
                    await bot.send_video(chat_id, FSInputFile(local_path), caption=caption)
                    continue

                # ДОКУМЕНТЫ
                if mt == "document":
                    await bot.send_document(chat_id, FSInputFile(local_path), caption=caption)
                    continue

                # АУДИО
                if mt == "audio":
                    await bot.send_audio(chat_id, FSInputFile(local_path), caption=caption)
                    continue

                # ГОЛОСОВЫЕ
                if mt == "voice":
                    await bot.send_voice(chat_id, FSInputFile(local_path), caption=caption)
                    continue

                # GIF / анимации
                if mt == "animation":
                    await bot.send_animation(chat_id, FSInputFile(local_path), caption=caption)
                    continue

                # СТИКЕРЫ — caption нельзя
                if mt == "sticker":
                    await bot.send_sticker(chat_id, FSInputFile(local_path))
                    await bot.send_message(chat_id, caption)
                    continue

                # fallback — отправляем как документ
                await bot.send_document(chat_id, FSInputFile(local_path), caption=caption)
                continue

            except Exception as e:
                await callback.message.answer(f"Ошибка отправки файла: {e}\n{caption}")
                continue

        # --- если файла нет ---
        await callback.message.answer(caption)



# ---------- ОБРАБОТКА КНОПОК СНИЗУ ----------

@dp.message(lambda m: m.text == "📁 Чаты")
async def open_chats(msg: types.Message):
    rows = get_deleted_chats()

    if not rows:
        await msg.answer("Нет чатов с удалёнными сообщениями.")
        return

    kb = InlineKeyboardBuilder()
    for r in rows:
        kb.button(text=f"Chat {r['chat_id']}", callback_data=f"chat_{r['chat_id']}")
    kb.adjust(1)

    await msg.answer("Выберите чат:", reply_markup=kb.as_markup())


@dp.message(lambda m: m.text == "👤 Пользователи")
async def open_users(msg: types.Message):
    rows = get_deleted_users()

    if not rows:
        await msg.answer("Нет пользователей, которые удаляли сообщения.")
        return

    kb = InlineKeyboardBuilder()
    for r in rows:
        name = r["username"] if r["username"] else r["user_id"]
        kb.button(text=f"{name}", callback_data=f"user_{r['user_id']}")
    kb.adjust(1)

    await msg.answer("Выберите пользователя:", reply_markup=kb.as_markup())


@dp.message(lambda m: m.text == "🔍 Username")
async def open_usernames(msg: types.Message):
    rows = get_deleted_usernames()

    if not rows:
        await msg.answer("Нет username с удалёнными сообщениями.")
        return

    kb = InlineKeyboardBuilder()
    for r in rows:
        kb.button(text=f"@{r['username']}", callback_data=f"uname_{r['username']}")
    kb.adjust(1)

    await msg.answer("Выберите username:", reply_markup=kb.as_markup())


# ---------- CALLBACK-ХЕНДЛЕРЫ ----------

@dp.callback_query(lambda c: c.data.startswith("chat_"))
async def show_chat(callback: types.CallbackQuery):
    chat_id = callback.data.split("_", 1)[1]
    rows = get_deleted_by_chat(chat_id)
    await send_deleted(callback, rows)


@dp.callback_query(lambda c: c.data.startswith("user_"))
async def show_user(callback: types.CallbackQuery):
    user_id = callback.data.split("_", 1)[1]
    rows = get_deleted_by_user(user_id)
    await send_deleted(callback, rows)


@dp.callback_query(lambda c: c.data.startswith("uname_"))
async def show_username(callback: types.CallbackQuery):
    username = callback.data.split("_", 1)[1]
    rows = get_deleted_by_username(username)
    await send_deleted(callback, rows)


# ---------- ЗАПУСК ----------

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
