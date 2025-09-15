import sqlite3
import requests
import socket
import asyncio
import time
from functools import wraps
from threading import Thread, Lock
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
                    elif any(err in message for err in ["اتصال بالإنترنت", "getaddrinfo failed"]):
                        retries += 1
                        print(f"⏳ محاولة {retries} من {max_retries}, انتظار {current_delay}s...")
                        await asyncio.sleep(current_delay)
                        current_delay *= 2
                        continue
                    return result
                except Exception as e:
                    retries += 1
                    print(f"⚠️ استثناء: {e}, محاولة {retries} من {max_retries}")
                    await asyncio.sleep(current_delay)
                    current_delay *= 2
            return False, "⚠️ فشلت جميع المحاولات"
        return wrapper
    return decorator

def save_chat_id(code: str, role: str, chat_id: int):
    print(f"⌛ جاري محاولة حفظ chat_id للكود {code} كـ {role}...")
    
    if not code or not role or not chat_id:
        print("❌ خطأ: البيانات غير مكتملة")
        print(f"code: {code}, role: {role}, chat_id: {chat_id}")
        return False

    if len(code) != 4 or not code.isdigit():
        print(f"❌ خطأ: كود الطالب يجب أن يكون 4 أرقام رقمية: {code}")
        return False

    try:
        with sqlite3.connect(students_db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT code FROM students WHERE code = ?", (code,))
            if not c.fetchone():
                print(f"❌ خطأ: الكود {code} غير موجود في قاعدة البيانات")
                return False

            if role == "student":
                c.execute("UPDATE students SET chat_id = ? WHERE code = ?", (chat_id, code))
            elif role == "guardian":
                c.execute("UPDATE students SET guardian_chat_id = ? WHERE code = ?", (chat_id, code))
            else:
                print(f"❌ خطأ: نوع المستخدم غير صحيح: {role}")
                return False
            
            if c.rowcount == 0:
                print(f"❌ لم يتم تحديث أي صفوف للكود {code}")
                return False
            
            if role == "student":
                c.execute("SELECT chat_id FROM students WHERE code = ?", (code,))
            else:
                c.execute("SELECT guardian_chat_id FROM students WHERE code = ?", (code,))
            
            result = c.fetchone()
            if result and str(result[0]) == str(chat_id):
                conn.commit()
                print(f"✅ تم حفظ chat_id بنجاح للكود {code}")
                return True
            else:
                print(f"❌ فشل التحقق من الحفظ للكود {code}")
                return False

    except sqlite3.Error as e:
        print(f"❌ خطأ في قاعدة البيانات: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {str(e)}")
        return False

@retry_on_network_error()
async def send_telegram_message(chat_id: int, text: str):
    conn_manager = ConnectionManager()
    if not conn_manager.is_online:
        return False, "❌ لا يوجد اتصال بالإنترنت"
    try:
        url = BASE_URL + "/sendMessage"
        params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            return True, "✅ تم إرسال الرسالة بنجاح"
        else:
            return False, f"❌ خطأ: {resp.text}"
    except Exception as e:
        return False, f"⚠️ استثناء أثناء الإرسال: {e}"

@retry_on_network_error()
async def send_telegram_photo(chat_id: int, photo_path: str, caption: str = ""):
    conn_manager = ConnectionManager()
    if not conn_manager.is_online:
        return False, "❌ لا يوجد اتصال بالإنترنت"
    try:
        with open(photo_path, "rb") as photo_file:
            files = {"photo": photo_file}
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
            resp = requests.post(BASE_URL + "/sendPhoto", data=data, files=files, timeout=20)
        if resp.status_code == 200:
            return True, "✅ تم إرسال الصورة بنجاح"
        else:
            return False, f"❌ خطأ: {resp.text}"
    except Exception as e:
        return False, f"⚠️ استثناء أثناء إرسال الصورة: {e}"

@retry_on_network_error()
async def send_telegram_video(chat_id: int, video_path: str, caption: str = ""):
    conn_manager = ConnectionManager()
    if not conn_manager.is_online:
        return False, "❌ لا يوجد اتصال بالإنترنت"
    try:
        with open(video_path, "rb") as video_file:
            files = {"video": video_file}
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
            resp = requests.post(BASE_URL + "/sendVideo", data=data, files=files, timeout=60)
        if resp.status_code == 200:
            return True, "✅ تم إرسال الفيديو بنجاح"
        else:
            return False, f"❌ خطأ: {resp.text}"
    except Exception as e:
        return False, f"⚠️ استثناء أثناء إرسال الفيديو: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        print(f"👤 مستخدم جديد - chat_id: {chat_id}")

        if not update.message:
            print("❌ خطأ: لا توجد رسالة في التحديث")
            return

        text = update.message.text
        if not text:
            print("❌ خطأ: الرسالة لا تحتوي على نص")
            await update.message.reply_text("⚠️ حدث خطأ. برجاء المحاولة مرة أخرى.")
            return

        activation_code = None
        if text.startswith("/start "):
            activation_code = text.split(" ", 1)[1].strip()

        if not activation_code or not activation_code.isdigit():
            await update.message.reply_text(
                "⚠️ برجاء الدخول من خلال الرابط المرسل لك."
            )
            print("❌ محاولة بدء بدون كود تفعيل صالح")
            return

        print(f"🔍 معالجة كود التفعيل: {activation_code}")
        
        code = activation_code
        if len(activation_code) == 4:
            role = "student"
        elif len(activation_code) > 4:
            role = "guardian"
            code = activation_code[:4]
        else:
            await update.message.reply_text("❌ كود التفعيل غير صالح. برجاء المحاولة مرة أخرى.")
            print(f"❌ كود تفعيل غير صالح: {activation_code}")
            return

        print(f"📝 محاولة حفظ - نوع: {role}, كود: {code}, chat_id: {chat_id}")

        if save_chat_id(code, role, chat_id):
            success_message = (
                f"✅ تم ربط حسابك بنجاح!\n"
                f"نوع الحساب: {'ولي أمر' if role=='guardian' else 'طالب'}\n"
                f"الكود: {code}"
            )
            await update.message.reply_text(success_message)
            print(f"✅ تم الربط بنجاح - نوع: {role}, كود: {code}, chat_id: {chat_id}")
        else:
            error_message = (
                "❌ عذراً، حدث خطأ أثناء ربط حسابك.\n"
                "برجاء التأكد من صحة الكود والمحاولة مرة أخرى."
            )
            await update.message.reply_text(error_message)
            print(f"❌ فشل الربط - نوع: {role}, كود: {code}, chat_id: {chat_id}")

    except Exception as e:
        error_message = (
            "❌ عذراً، حدث خطأ غير متوقع.\n"
            "برجاء المحاولة مرة أخرى لاحقاً."
        )
        await update.message.reply_text(error_message)
        print(f"❌ خطأ غير متوقع: {str(e)}")

async def role_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    role = query.data.replace("role_", "")
    code = context.user_data.get("code")
    chat_id = query.from_user.id
    
    print(f"👤 اختيار نوع المستخدم - نوع: {role}, كود: {code}, chat_id: {chat_id}")
    
    if not code:
        await query.edit_message_text("⚠️ خطأ: لم يتم تحديد الكود. برجاء المحاولة مرة أخرى.")
        print(f"❌ محاولة اختيار نوع بدون كود - chat_id: {chat_id}")
        return
        
    if save_chat_id(code, role, chat_id):
        success_message = (
            f"✅ تم ربط حسابك بنجاح!\n"
            f"نوع الحساب: {role}\n"
            f"الكود: {code}"
        )
        await query.edit_message_text(success_message)
        print(f"✅ تم الربط بنجاح عبر القائمة - نوع: {role}, كود: {code}, chat_id: {chat_id}")
    else:
        error_message = (
            "❌ عذراً، حدث خطأ أثناء ربط حسابك.\n"
            "برجاء التأكد من صحة الكود والمحاولة مرة أخرى."
        )
        await query.edit_message_text(error_message)
        print(f"❌ فشل الربط عبر القائمة - نوع: {role}, كود: {code}, chat_id: {chat_id}")

@retry_on_network_error(max_retries=3, delay=1)
async def initialize_bot(app: Application):
    try:
        await app.initialize()
        print("✨ تم تهيئة البوت بنجاح")
        return True, "✅ تم تهيئة البوت بنجاح"
    except NetworkError as e:
        print(f"❌ خطأ شبكة أثناء تهيئة البوت: {str(e)}")
        return False, f"❌ خطأ شبكة: {str(e)}"
    except Exception as e:
        print(f"❌ خطأ غير متوقع أثناء تهيئة البوت: {str(e)}")
        return False, f"❌ خطأ: {str(e)}"

@retry_on_network_error(max_retries=3, delay=1)
async def send_pending_notifications():
    conn_manager = ConnectionManager()
    if not conn_manager.is_online:
        print("❌ لا يوجد اتصال بالإنترنت لإرسال الإشعارات المؤجلة")
        return False, "❌ لا يوجد اتصال بالإنترنت"

    try:
        with sqlite3.connect(students_db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT id, chat_id, message FROM pending_notifications')
            notifications = c.fetchall()
            sent_count = 0
            for notif_id, chat_id, message in notifications:
                success, error_msg = await send_telegram_message(chat_id, message)
                if success:
                    print(f"📨 تم إرسال إشعار مؤجل (ID: {notif_id}) إلى {chat_id}")
                    c.execute('DELETE FROM pending_notifications WHERE id = ?', (notif_id,))
                    sent_count += 1
                else:
                    print(f"❌ فشل إرسال إشعار مؤجل (ID: {notif_id}): {error_msg}")
            conn.commit()
            if sent_count > 0:
                return True, f"✅ تم إرسال {sent_count} إشعار مؤجل"
            else:
                return True, "✅ لا يوجد إشعارات مؤجلة"
    except sqlite3.Error as e:
        print(f"❌ خطأ في قاعدة البيانات أثناء معالجة الإشعارات المؤجلة: {str(e)}")
        return False, f"❌ خطأ: {str(e)}"

def run_telegram_bot():
    print("🚀 بدء تشغيل بوت التيليجرام...")
    
    conn_manager = ConnectionManager()
    conn_manager.start_monitoring()
    print("🔄 بدء مراقبة الاتصال بالإنترنت...")

    def run_bot_thread():
        """تشغيل البوت في خيط منفصل لتجنب تضارب event loop مع Flet"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_polling())
        except Exception as e:
            print(f"❌ حدث خطأ في خيط البوت: {str(e)}")
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
            
            print("⏳ جاري بدء عملية استقبال الرسائل...")
            # إعادة إرسال الإشعارات المؤجلة عند التشغيل
            success, message = await send_pending_notifications()
            print(message)
            
            await app.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES,
                close_loop=False
            )
        except Exception as e:
            print(f"❌ حدث خطأ أثناء تشغيل البوت: {str(e)}")

    # تشغيل البوت في خيط منفصل
    bot_thread = Thread(target=run_bot_thread, daemon=True)
    bot_thread.start()
    print("🔄 تم تشغيل بوت التليجرام في خيط منفصل")

if __name__ == "__main__":
    run_telegram_bot()

    