import sqlite3
import requests
import asyncio
from functools import wraps
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import NetworkError

from utils.database import students_db_path
from utils.connection_manager import ConnectionManager

TOKEN = "8256652647:AAHqakKvqgWiKqsm0qI61pXPKa_ETKwfyfE"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

def generate_activation_link(code: str, role: str) -> str:
    if role == "guardian":
        activation_code = f"{code}1"
    else:
        activation_code = code
    return f"https://t.me/studentMang_bot?start={activation_code}"

def retry_on_network_error(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            while retries < max_retries:
                try:
                    result = await func(*args, **kwargs)
                    success, message = result if isinstance(result, tuple) else (True, result)
                    if success:
                        return result
                    elif any(err in message for err in ["internet connection", "getaddrinfo failed"]):
                        retries += 1
                        print(f"Retry {retries} of {max_retries}, waiting {current_delay}s...")
                        await asyncio.sleep(current_delay)
                        current_delay *= 2
                        continue
                    return result
                except Exception as e:
                    retries += 1
                    print(f"Exception: {e}, retry {retries} of {max_retries}")
                    await asyncio.sleep(current_delay)
                    current_delay *= 2
            return False, "All retries failed"
        return wrapper
    return decorator

def save_chat_id(code: str, role: str, chat_id: int):
    print(f"Trying to save chat_id for code {code} as {role}...")

    if not code or not role or not chat_id:
        print("Error: Missing data")
        print(f"code: {code}, role: {role}, chat_id: {chat_id}")
        return False

    if len(code) != 4 or not code.isdigit():
        print(f"Error: Student code must be 4 digits: {code}")
        return False

    try:
        with sqlite3.connect(students_db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT code FROM students WHERE code = ?", (code,))
            if not c.fetchone():
                print(f"Error: Code {code} not found in database")
                return False

            if role == "student":
                c.execute("UPDATE students SET chat_id = ? WHERE code = ?", (chat_id, code))
            elif role == "guardian":
                c.execute("UPDATE students SET guardian_chat_id = ? WHERE code = ?", (chat_id, code))
            else:
                print(f"Error: Invalid role {role}")
                return False

            if c.rowcount == 0:
                print(f"No rows updated for code {code}")
                return False

            if role == "student":
                c.execute("SELECT chat_id FROM students WHERE code = ?", (code,))
            else:
                c.execute("SELECT guardian_chat_id FROM students WHERE code = ?", (code,))

            result = c.fetchone()
            if result and str(result[0]) == str(chat_id):
                conn.commit()
                print(f"chat_id saved successfully for code {code}")
                return True
            else:
                print(f"Verification failed for code {code}")
                return False

    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return False

@retry_on_network_error()
async def send_telegram_message(chat_id: int, text: str):
    conn_manager = ConnectionManager()
    if not conn_manager.is_online:
        return False, "No internet connection"
    try:
        url = BASE_URL + "/sendMessage"
        params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            return True, "Message sent successfully"
        else:
            return False, f"Error: {resp.text}"
    except Exception as e:
        return False, f"Exception while sending: {e}"

@retry_on_network_error()
async def send_telegram_photo(chat_id: int, photo_path: str, caption: str = ""):
    conn_manager = ConnectionManager()
    if not conn_manager.is_online:
        return False, "No internet connection"
    try:
        with open(photo_path, "rb") as photo_file:
            files = {"photo": photo_file}
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
            resp = requests.post(BASE_URL + "/sendPhoto", data=data, files=files, timeout=20)
        if resp.status_code == 200:
            return True, "Photo sent successfully"
        else:
            return False, f"Error: {resp.text}"
    except Exception as e:
        return False, f"Exception while sending photo: {e}"

@retry_on_network_error()
async def send_telegram_video(chat_id: int, video_path: str, caption: str = ""):
    conn_manager = ConnectionManager()
    if not conn_manager.is_online:
        return False, "No internet connection"
    try:
        with open(video_path, "rb") as video_file:
            files = {"video": video_file}
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
            resp = requests.post(BASE_URL + "/sendVideo", data=data, files=files, timeout=60)
        if resp.status_code == 200:
            return True, "Video sent successfully"
        else:
            return False, f"Error: {resp.text}"
    except Exception as e:
        return False, f"Exception while sending video: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        print(f"New user - chat_id: {chat_id}")

        if not update.message:
            print("Error: No message in update")
            return

        text = update.message.text
        if not text:
            print("Error: Message has no text")
            await update.message.reply_text("An error occurred. Please try again.")
            return

        activation_code = None
        if text.startswith("/start "):
            activation_code = text.split(" ", 1)[1].strip()

        if not activation_code or not activation_code.isdigit():
            await update.message.reply_text("Please use the link sent to you.")
            print("Invalid start attempt without activation code")
            return

        print(f"Processing activation code: {activation_code}")

        code = activation_code
        if len(activation_code) == 4:
            role = "student"
        elif len(activation_code) > 4:
            role = "guardian"
            code = activation_code[:4]
        else:
            await update.message.reply_text("Invalid activation code. Please try again.")
            print(f"Invalid activation code: {activation_code}")
            return

        print(f"Saving chat_id - role: {role}, code: {code}, chat_id: {chat_id}")

        if save_chat_id(code, role, chat_id):
            success_message = (
                f"Account linked successfully!\n"
                f"Role: {'Guardian' if role=='guardian' else 'Student'}\n"
                f"Code: {code}"
            )
            await update.message.reply_text(success_message)
            print(f"Linked successfully - role: {role}, code: {code}, chat_id: {chat_id}")
        else:
            error_message = (
                "An error occurred while linking your account.\n"
                "Please check your code and try again."
            )
            await update.message.reply_text(error_message)
            print(f"Linking failed - role: {role}, code: {code}, chat_id: {chat_id}")

    except Exception as e:
        error_message = "An unexpected error occurred. Please try again later."
        await update.message.reply_text(error_message)
        print(f"Unexpected error: {str(e)}")

async def role_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    role = query.data.replace("role_", "")
    code = context.user_data.get("code")
    chat_id = query.from_user.id

    print(f"Role selected - role: {role}, code: {code}, chat_id: {chat_id}")

    if not code:
        await query.edit_message_text("Error: No code provided. Please try again.")
        print(f"Attempted role selection without code - chat_id: {chat_id}")
        return

    if save_chat_id(code, role, chat_id):
        success_message = f"Account linked successfully!\nRole: {role}\nCode: {code}"
        await query.edit_message_text(success_message)
        print(f"Linked successfully via menu - role: {role}, code: {code}, chat_id: {chat_id}")
    else:
        error_message = "An error occurred while linking your account. Please check your code and try again."
        await query.edit_message_text(error_message)
        print(f"Linking failed via menu - role: {role}, code: {code}, chat_id: {chat_id}")

@retry_on_network_error(max_retries=3, delay=1)
async def initialize_bot(app: Application):
    try:
        await app.initialize()
        print("Bot initialized successfully")
        return True, "Bot initialized successfully"
    except NetworkError as e:
        print(f"Network error during initialization: {str(e)}")
        return False, f"Network error: {str(e)}"
    except Exception as e:
        print(f"Unexpected error during initialization: {str(e)}")
        return False, f"Error: {str(e)}"

@retry_on_network_error(max_retries=3, delay=1)
async def send_pending_notifications():
    conn_manager = ConnectionManager()
    if not conn_manager.is_online:
        print("No internet connection for sending pending notifications")
        return False, "No internet connection"

    try:
        with sqlite3.connect(students_db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT id, chat_id, message FROM pending_notifications')
            notifications = c.fetchall()
            sent_count = 0
            for notif_id, chat_id, message in notifications:
                success, error_msg = await send_telegram_message(chat_id, message)
                if success:
                    print(f"Pending notification (ID: {notif_id}) sent to {chat_id}")
                    c.execute('DELETE FROM pending_notifications WHERE id = ?', (notif_id,))
                    sent_count += 1
                else:
                    print(f"Failed to send pending notification (ID: {notif_id}): {error_msg}")
            conn.commit()
            if sent_count > 0:
                return True, f"Sent {sent_count} pending notifications"
            else:
                return True, "No pending notifications"
    except sqlite3.Error as e:
        print(f"Database error while processing pending notifications: {str(e)}")
        return False, f"Error: {str(e)}"

def run_telegram_bot():
    print("Starting Telegram bot...")

    conn_manager = ConnectionManager()
    conn_manager.start_monitoring()
    print("Started monitoring internet connection...")

    def run_bot_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_polling())
        except Exception as e:
            print(f"Error in bot thread: {str(e)}")
        finally:
            loop.close()
            conn_manager.stop_monitoring()

    async def run_polling():
        try:
            app = Application.builder().token(TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CallbackQueryHandler(role_selected))

            success, message = await initialize_bot(app)
            if not success:
                print(message)
                return

            print("Starting to receive messages...")
            success, message = await send_pending_notifications()
            print(message)

            await app.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES,
                close_loop=False
            )
        except Exception as e:
            print(f"Error while running bot: {str(e)}")

    bot_thread = Thread(target=run_bot_thread, daemon=True)
    bot_thread.start()
    print("Telegram bot is running in a separate thread")

if __name__ == "__main__":
    run_telegram_bot()
