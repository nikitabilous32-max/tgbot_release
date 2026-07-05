import os
import time
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import (
    Bot,
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
    CallbackContext
)
from telegram import InputFile

from database import get_db


BOT_TOKEN = "8987195198:AAHv7vh2mDPt81mDK_EDYxHv5AhHrOGJ7YY"


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


# ---------- КНОПКИ ----------

reply_kb = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📁 Чаты"), KeyboardButton("👤 Пользователи")],
        [KeyboardButton("🔍 Username")]
    ],
    resize_keyboard=True
)


# ---------- HANDLERS ----------

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Выберите действие:", reply_markup=reply_kb)


def menu(update: Update, context: CallbackContext):
    update.message.reply_text("Меню открыто:", reply_markup=reply_kb)


def clear(update: Update, context: CallbackContext):
    update.message.reply_text("🧹 Очищаю базу и файлы...")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

    media_root = os.path.join(os.path.dirname(__file__), "..", "media")

    removed_files = 0
    for root, dirs, files in os.walk(media_root):
        for f in files:
            try:
                os.remove(os.path.join(root, f))
                removed_files += 1
            except:
                pass

    update.message.reply_text(f"✔ База очищена\n✔ Удалено файлов: {removed_files}")


# ---------- ОТПРАВКА УДАЛЁННЫХ ----------

def send_deleted(update: Update, context: CallbackContext, rows):
    chat_id = update.effective_chat.id

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

        if local_path and os.path.exists(local_path):
            try:
                file = InputFile(local_path)

                if mt == "photo":
                    context.bot.send_photo(chat_id, file, caption=caption)
                elif mt == "video":
                    context.bot.send_video(chat_id, file, caption=caption)
                elif mt == "document":
                    context.bot.send_document(chat_id, file, caption=caption)
                elif mt == "audio":
                    context.bot.send_audio(chat_id, file, caption=caption)
                elif mt == "voice":
                    context.bot.send_voice(chat_id, file, caption=caption)
                elif mt == "animation":
                    context.bot.send_animation(chat_id, file, caption=caption)
                elif mt == "sticker":
                    context.bot.send_sticker(chat_id, file)
                    context.bot.send_message(chat_id, caption)
                else:
                    context.bot.send_document(chat_id, file, caption=caption)

                continue

            except Exception as e:
                update.message.reply_text(f"Ошибка отправки файла: {e}\n{caption}")
                continue

        update.message.reply_text(caption)


# ---------- КНОПКИ ----------

def open_chats(update: Update, context: CallbackContext):
    rows = get_deleted_chats()

    if not rows:
        update.message.reply_text("Нет чатов с удалёнными сообщениями.")
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Chat {r['chat_id']}", callback_data=f"chat_{r['chat_id']}")]
        for r in rows
    ])

    update.message.reply_text("Выберите чат:", reply_markup=kb)


def open_users(update: Update, context: CallbackContext):
    rows = get_deleted_users()

    if not rows:
        update.message.reply_text("Нет пользователей, которые удаляли сообщения.")
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(r["username"] or r["user_id"], callback_data=f"user_{r['user_id']}")]
        for r in rows
    ])

    update.message.reply_text("Выберите пользователя:", reply_markup=kb)


def open_usernames(update: Update, context: CallbackContext):
    rows = get_deleted_usernames()

    if not rows:
        update.message.reply_text("Нет username с удалёнными сообщениями.")
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"@{r['username']}", callback_data=f"uname_{r['username']}")]
        for r in rows
    ])

    update.message.reply_text("Выберите username:", reply_markup=kb)


# ---------- CALLBACKS ----------

def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data

    if data.startswith("chat_"):
        chat_id = data.split("_", 1)[1]
        rows = get_deleted_by_chat(chat_id)
        send_deleted(update, context, rows)

    elif data.startswith("user_"):
        user_id = data.split("_", 1)[1]
        rows = get_deleted_by_user(user_id)
        send_deleted(update, context, rows)

    elif data.startswith("uname_"):
        username = data.split("_", 1)[1]
        rows = get_deleted_by_username(username)
        send_deleted(update, context, rows)

    query.answer()


# ---------- ЗАПУСК ----------

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("menu", menu))
    dp.add_handler(CommandHandler("clear", clear))

    dp.add_handler(MessageHandler(Filters.text("📁 Чаты"), open_chats))
    dp.add_handler(MessageHandler(Filters.text("👤 Пользователи"), open_users))
    dp.add_handler(MessageHandler(Filters.text("🔍 Username"), open_usernames))

    dp.add_handler(CallbackQueryHandler(callback_handler))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
