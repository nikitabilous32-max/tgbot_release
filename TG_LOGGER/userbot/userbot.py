import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyrogram import Client, filters
from database import get_db
from datetime import datetime
import time

api_id = 32816018
api_hash = "73aa5abdd997d8dc991c261b010adfdf"

app = Client("userbot", api_id=api_id, api_hash=api_hash)

MEDIA_DIR = os.path.join(os.path.dirname(__file__), "..", "media", "photos")
os.makedirs(MEDIA_DIR, exist_ok=True)


def extract_media(msg):
    if msg.video_note:
        return "video_note", msg.video_note.file_id, msg.video_note.file_unique_id

    if msg.video and msg.video_note:
        return "video_note", msg.video.file_id, msg.video.file_unique_id

    if msg.video:
        return "video", msg.video.file_id, msg.video.file_unique_id

    if msg.photo:
        return "photo", msg.photo.file_id, msg.photo.file_unique_id

    if msg.document:
        return "document", msg.document.file_id, msg.document.file_unique_id

    if msg.animation:
        return "animation", msg.animation.file_id, msg.animation.file_unique_id

    if msg.sticker:
        return "sticker", msg.sticker.file_id, msg.sticker.file_unique_id

    if msg.voice:
        return "voice", msg.voice.file_id, msg.voice.file_unique_id

    if msg.audio:
        return "audio", msg.audio.file_id, msg.audio.file_unique_id

    return None, None, None


def get_extension(msg, media_type):
    if media_type == "photo":
        return ".jpg"

    if media_type == "document" and msg.document.file_name:
        return os.path.splitext(msg.document.file_name)[1]

    if media_type == "video_note":
        return ".mp4"

    if media_type == "video" and msg.video.file_name:
        return os.path.splitext(msg.video.file_name)[1]

    if media_type == "audio" and msg.audio.file_name:
        return os.path.splitext(msg.audio.file_name)[1]

    if media_type == "voice":
        return ".ogg"

    if media_type == "sticker":
        return ".tgs" if msg.sticker.is_animated else ".webp"

    if media_type == "animation":
        return ".gif"

    return ".bin"


async def download_media(msg, media_type, file_id):
    ext = get_extension(msg, media_type)
    filename = f"{msg.id}_{media_type}{ext}"
    path = os.path.join(MEDIA_DIR, filename)

    try:
        await msg.download(path)
        return path
    except Exception as e:
        print(f"Ошибка скачивания файла: {e}")
        return None


def save_message(msg, media_type, file_id, file_unique_id, local_path, deleted=False, edited=False):
    conn = get_db()
    cur = conn.cursor()

    chat_id = msg.chat.id if msg.chat else None
    user_id = msg.from_user.id if msg.from_user else None
    username = msg.from_user.username if msg.from_user else None
    text = msg.text if msg.text else None

    cur.execute("""
        INSERT INTO messages (chat_id, message_id, user_id, username, date, text,
                              media_type, file_id, file_unique_id, local_path, deleted, edited)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        chat_id,
        msg.id,
        user_id,
        username,
        int(time.time()),
        text,
        media_type,
        file_id,
        file_unique_id,
        local_path,
        1 if deleted else 0,
        1 if edited else 0
    ))

    conn.commit()
    conn.close()


@app.on_message(filters.all)
async def log_message(client, msg):

    # НЕ сохраняем сообщения от ботов
    if msg.from_user and msg.from_user.is_bot:
        return

    # НЕ сохраняем сообщения от каналов
    if msg.sender_chat:
        return

    media_type, file_id, file_unique_id = extract_media(msg)
    local_path = None

    # === Проверяем одноразовое фото ===
    is_view_once_photo = False

    if getattr(msg, "has_media_spoiler", False):
        is_view_once_photo = True

    if msg.photo and msg.photo.ttl_seconds:
        is_view_once_photo = True

    # === Проверяем одноразовое видео ===
    is_view_once_video = False

    if msg.video and msg.video.ttl_seconds:
        is_view_once_video = True

    # === Если одноразовое фото ===
    if is_view_once_photo:
        try:
            filename = f"{msg.chat.id}_{msg.id}_{datetime.now().timestamp()}_view_once_photo.jpg"
            path = os.path.join(MEDIA_DIR, filename)

            await msg.download(file_name=path)
            local_path = path

            print(f"🔥 Одноразовое фото сохранено: {path}")

            media_type = "photo_view_once"

        except Exception as e:
            print(f"[ERROR] Не удалось сохранить одноразовое фото: {e}")

        save_message(msg, media_type, file_id, file_unique_id, local_path)
        print("Получено сообщение:", msg.text or media_type)
        return

    # === Если одноразовое видео ===
    if is_view_once_video:
        try:
            filename = f"{msg.chat.id}_{msg.id}_{datetime.now().timestamp()}_view_once_video.mp4"
            path = os.path.join(MEDIA_DIR, filename)

            await msg.download(file_name=path)
            local_path = path

            print(f"🔥 Одноразовое видео сохранено: {path}")

            media_type = "video_view_once"

        except Exception as e:
            print(f"[ERROR] Не удалось сохранить одноразовое видео: {e}")

        save_message(msg, media_type, file_id, file_unique_id, local_path)
        print("Получено сообщение:", msg.text or media_type)
        return

    # === Обычные медиа ===
    if media_type:
        local_path = await download_media(msg, media_type, file_id)

    save_message(msg, media_type, file_id, file_unique_id, local_path)
    print("Получено сообщение:", msg.text or media_type)


@app.on_deleted_messages()
async def deleted_messages(client, messages):
    conn = get_db()
    cur = conn.cursor()

    for msg in messages:
        cur.execute("SELECT * FROM messages WHERE message_id = ?", (msg.id,))
        old = cur.fetchone()

        if old:
            chat_id = old["chat_id"]
            user_id = old["user_id"]
            username = old["username"]
            text = old["text"]
            media_type = old["media_type"]
            file_id = old["file_id"]
            file_unique_id = old["file_unique_id"]
            local_path = old["local_path"]

            date_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            print("🗑 Удалено сообщение:")
            print(f"  📅 Дата: {date_str}")
            print(f"  💬 Чат: {chat_id}")
            print(f"  👤 Пользователь: {username} ({user_id})")

            if text:
                print(f"  ✏️ Текст: {text}")
            elif media_type:
                print(f"  🖼 Медиа: {media_type} (local={local_path})")
            else:
                print(f"  ❓ Тип: неизвестно")

        else:
            chat_id = None
            user_id = None
            username = None
            text = None
            media_type = None
            file_id = None
            file_unique_id = None
            local_path = None

        cur.execute("""
            INSERT INTO messages (chat_id, message_id, user_id, username, date, text,
                                  media_type, file_id, file_unique_id, local_path, deleted, edited)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chat_id,
            msg.id,
            user_id,
            username,
            int(time.time()),
            text,
            media_type,
            file_id,
            file_unique_id,
            local_path,
            1,
            0
        ))

    conn.commit()
    conn.close()


@app.on_edited_message()
async def edited_message(client, msg):
    media_type, file_id, file_unique_id = extract_media(msg)
    local_path = None

    if media_type:
        local_path = await download_media(msg, media_type, file_id)

    save_message(msg, media_type, file_id, file_unique_id, local_path, edited=True)
    print("✏️ Отредактировано сообщение:", msg.text or media_type)


app.run()
