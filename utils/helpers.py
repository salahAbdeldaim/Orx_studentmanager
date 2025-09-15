# utils/helpers.py
import flet as ft
import logging
import sqlite3
import asyncio
from utils.database import students_db_path
from utils.telegram_bot import send_telegram_message,send_telegram_photo,send_telegram_video


def format_phone_number(phone):
    print("format_phone_number")
    try:
        phone = str(phone).strip()
        if phone.startswith('+20'):
            return phone
        phone = phone.lstrip('0')
        return '+20' + phone
    except Exception as e:
        logging.error(f"خطأ في format_phone_number: {e}")
        return phone

def search_bar(msg, on_submit=None):
    print("search_bar")
    return ft.Container(
        height=50,
        expand=True,
        content=ft.TextField(
            hint_text=msg,
            prefix_icon=ft.Icons.SEARCH,
            bgcolor="#0059DF",
            color="white",
            border_radius=8,
            expand=True,
            on_submit=on_submit,
        )
    )

def show_error_dialog(page, message):
    snack = ft.SnackBar(
        content=ft.Text(message, text_align=ft.TextAlign.CENTER, color=ft.Colors.WHITE),
        bgcolor=ft.Colors.RED_700,
        duration=3000,
    )
    page.snack_bar = snack
    snack.open = True
    if snack not in page.overlay:
        page.overlay.append(snack)
    page.update()

def show_success_dialog(page, message):
    snack = ft.SnackBar(
        content=ft.Text(message, text_align=ft.TextAlign.CENTER, color=ft.Colors.WHITE),
        bgcolor=ft.Colors.GREEN_700,
        duration=3000,
    )
    page.snack_bar = snack
    snack.open = True
    if snack not in page.overlay:
        page.overlay.append(snack)
    page.update()

def show_under_development_dialog(page):
    under_dev_dialog = ft.AlertDialog(
        title=ft.Text("تحت التطوير", text_align=ft.TextAlign.CENTER),
        content=ft.Text("هذه الميزة قيد التطوير حالياً. شكراً لصبرك!", text_align=ft.TextAlign.CENTER),
        actions=[
            ft.TextButton("إغلاق", on_click=lambda e: e.page.close(under_dev_dialog))
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER
    )
    # إغلاق أي Dialog مفتوح مسبقاً
    if hasattr(page, 'dialog') and page.dialog:
        page.dialog.open = False
    # إضافة الـ Dialog إلى overlay
    if under_dev_dialog not in page.overlay:
        page.overlay.append(under_dev_dialog)
    under_dev_dialog.open = True
    page.update()

# دالة عامة لجلب المجموعات من قاعدة البيانات
def get_groups():
    print("get_groups")
    conn = sqlite3.connect(students_db_path)
    c = conn.cursor()
    c.execute('SELECT id, name, days FROM groups')
    groups = c.fetchall()
    conn.close()
    return [ft.dropdown.Option(key=str(g[0]), text=f"{g[1]} ({g[2]})") for g in groups]


def extract_unique_code(full_code: str) -> str:
    # نشيل الأصفار من البداية
    trimmed = full_code.lstrip("0")
    # ناخد أول 4 أرقام بس
    return trimmed[:4]


def show_skipped_students_dialog(page, skipped_students):
    if not skipped_students:
        return
    
    # طباعة في الكونسول
    print("⚠️ الطلاب اللي متبعتلهمش:")
    for s in skipped_students:
        print(f"   - {s}")

    # إنشاء Dialog
    dlg = ft.AlertDialog(
        title=ft.Text(
            "تنبيه: طلاب لم يتم إرسال رسائل لهم",
            size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER
        ),
        content=ft.Column(
            [ft.Text(student, size=16) for student in skipped_students],
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.START
        ),
        actions=[
            ft.TextButton(
                "حسناً", 
                on_click=lambda e: (setattr(dlg, "open", False), page.update())
            )
        ]
    )

    # إغلاق أي Dialog مفتوح مسبقاً
    if hasattr(page, 'dialog') and page.dialog:
        page.dialog.open = False

    # إضافة الـ Dialog للـ overlay
    if dlg not in page.overlay:
        page.overlay.append(dlg)

    dlg.open = True
    page.dialog = dlg   # تخزينه في page علشان نقدر نتحكم فيه بعدين
    page.update()


def send_telegrem_messege(student_data, message, to_value="ولي الأمر", page=None): 
    """إرسال رسالة تيليجرام للطالب أو ولي الأمر"""

    print("🚦 بدء عملية إرسال رسالة تيليجرام...")
    print(f"📌 المستلم: {to_value} | الرسالة: {message}")

    if page:
        show_success_dialog(page, "📱 جاري تجهيز الرسالة للإرسال عبر تيليجرام...")
    
    # تحديد معرف المحادثة بناءً على المستلم
    chat_id = student_data.get("guardian_chat_id" if to_value == "ولي الأمر" else "chat_id")
    recipient_type = "ولي أمر الطالب" if to_value == "ولي الأمر" else "الطالب"
    
    print(f"🔍 تم تحديد المستلم: {recipient_type} | chat_id={chat_id}")

    if not chat_id or not str(chat_id).strip():
        error_msg = f"⚠️ لم يتم العثور على حساب تيليجرام مرتبط بـ {recipient_type}. يرجى التأكد من تفعيل الحساب أولاً."
        print(f"❌ {error_msg}")
        if page:
            show_error_dialog(page, error_msg)
        return False, error_msg
    
    # إرسال الرسالة
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success, response_message = loop.run_until_complete(send_telegram_message(chat_id, message))
    finally:
        loop.close()

    if success:
        success_msg = f"✅ تم إرسال الرسالة بنجاح إلى {recipient_type}"
        print(success_msg)
        if page:
            show_success_dialog(page, success_msg)
    else:
        error_msg = f"❌ فشل إرسال الرسالة إلى {recipient_type}: {response_message}"
        print(error_msg)
        if page:
            show_error_dialog(page, error_msg)
    
    return success, response_message

def send_telegrem_photo(student_data, photo_path, caption="", to_value="ولي الأمر", page=None):
    """إرسال صورة تيليجرام للطالب أو ولي الأمر"""

    print("🚦 بدء عملية إرسال صورة عبر تيليجرام...")
    print(f"📌 المستلم: {to_value} | الصورة: {photo_path} | التوضيح: {caption}")

    # تحديد معرف المحادثة
    chat_id = student_data.get("guardian_chat_id" if to_value == "ولي الأمر" else "chat_id")
    recipient_type = "ولي أمر الطالب" if to_value == "ولي الأمر" else "الطالب"
    print(f"🔍 تم تحديد المستلم: {recipient_type} | chat_id={chat_id}")

    if not chat_id or not str(chat_id).strip():
        error_msg = f"⚠️ لم يتم العثور على حساب تيليجرام مرتبط بـ {recipient_type}."
        print(f"❌ {error_msg}")
        if page:
            show_error_dialog(page, error_msg)
        return False, error_msg

    # إرسال الصورة
    success, response_message = send_telegram_photo(chat_id, photo_path, caption)

    if success:
        success_msg = f"✅ تم إرسال الصورة بنجاح إلى {recipient_type}"
        print(success_msg)
        if page:
            show_success_dialog(page, success_msg)
    else:
        error_msg = f"❌ فشل إرسال الصورة إلى {recipient_type}: {response_message}"
        print(error_msg)
        if page:
            show_error_dialog(page, error_msg)

    return success, response_message


def send_telegrem_video(student_data, video_path, caption="", to_value="ولي الأمر", page=None):
    """إرسال فيديو تيليجرام للطالب أو ولي الأمر"""

    print("🚦 بدء عملية إرسال فيديو عبر تيليجرام...")
    print(f"📌 المستلم: {to_value} | الفيديو: {video_path} | التوضيح: {caption}")

    # تحديد معرف المحادثة
    chat_id = student_data.get("guardian_chat_id" if to_value == "ولي الأمر" else "chat_id")
    recipient_type = "ولي أمر الطالب" if to_value == "ولي الأمر" else "الطالب"
    print(f"🔍 تم تحديد المستلم: {recipient_type} | chat_id={chat_id}")

    if not chat_id or not str(chat_id).strip():
        error_msg = f"⚠️ لم يتم العثور على حساب تيليجرام مرتبط بـ {recipient_type}."
        print(f"❌ {error_msg}")
        if page:
            show_error_dialog(page, error_msg)
        return False, error_msg

    # إرسال الفيديو
    success, response_message = send_telegram_video(chat_id, video_path, caption)

    if success:
        success_msg = f"✅ تم إرسال الفيديو بنجاح إلى {recipient_type}"
        print(success_msg)
        if page:
            show_success_dialog(page, success_msg)
    else:
        error_msg = f"❌ فشل إرسال الفيديو إلى {recipient_type}: {response_message}"
        print(error_msg)
        if page:
            show_error_dialog(page, error_msg)

    return success, response_message
