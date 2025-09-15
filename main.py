import flet as ft
import os
import logging
import asyncio
import multiprocessing

# إعداد الـ logging
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

# استيراد الصفحات من مجلد pages
from pages.student_page import student_page
from pages.group_page import group_page
from pages.send_mails_page import send_mails_page
from pages.barcode_page import barcode_page

# استيراد الدوال المساعدة
from utils.helpers import show_error_dialog, show_success_dialog, show_under_development_dialog
from utils.add_code import init_codes
from utils.telegram_bot import run_telegram_bot

# تعريف المسارات الرئيسية للملفات
try:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "assets")
    logging.info(f"Assets path configured: {assets_dir}")

    app_icon = os.path.join(assets_dir, "icon.ico")
    facebook = os.path.join(assets_dir, "facebook.png")
    whatsapp = os.path.join(assets_dir, "whatsapp.png")
    linkedin = os.path.join(assets_dir, "linkedin.png")
    gmail = os.path.join(assets_dir, "gmail.png")
    home_gif = os.path.join(assets_dir, "home1.gif")
    logging.info("Asset paths loaded successfully")
except Exception as e:
    logging.error(f"Error loading asset paths: {e}")
    print(f"Error loading asset paths: {e}")

def start_bot_later():
    """تشغيل بوت التليجرام في عملية منفصلة بعد تحميل الـ UI"""
    logging.info("Starting Telegram bot process")
    bot_process = multiprocessing.Process(target=run_telegram_bot)
    bot_process.daemon = True
    bot_process.start()
    logging.info("Telegram bot process started")

def main(page: ft.Page):
    logging.info("Starting main function")
    added_count = init_codes()
    if added_count:
        show_success_dialog(page, f"تم إضافة أكواد جديدة لعدد {added_count} من الطلاب.")
        logging.info(f"Added codes for {added_count} students")
    page.title = "نظام إدارة الطلاب"
    if app_icon and os.path.exists(app_icon):
        page.window.icon = app_icon
        logging.info(f"App icon set: {app_icon}")
    else:
        logging.warning(f"App icon not found: {app_icon}")

    page.window.width = 1440
    page.window.height = 900
    page.bgcolor = "#FFFFFF"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.DARK
    logging.info("Page settings configured")

    # --- الصفحات ---
    try:
        home_page_content = ft.Container(
            expand=True,
            alignment=ft.alignment.center,
            content=ft.Column(
                [
                    ft.Icon(name=ft.Icons.SCHOOL, size=80, color="#00409F"),
                    ft.Text(
                        "مرحباً بك في نظام إدارة الطلاب!",
                        size=30, weight=ft.FontWeight.BOLD, color="#00409F",
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "نظام متكامل لإدارة بيانات الطلاب والمجموعات بكفاءة وسهولة.",
                        size=20, color="#333333", text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Image(src=home_gif, width=400, height=400, fit=ft.ImageFit.CONTAIN)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20,
            ),
        )
        logging.info("Home page content created")
    except Exception as e:
        logging.error(f"Error creating home page content: {e}")

    main_content = ft.Container(content=home_page_content, expand=True)

    pages_map = {
        "home": home_page_content,
        "students": student_page,
        "groups": group_page,
        "mails": send_mails_page,
        "barcode": barcode_page,
    }

    def show_page(key):
        logging.info(f"Switching to page: {key}")
        try:
            content_function = pages_map[key]
            main_content.content = content_function(page) if callable(content_function) else content_function
            page.update()
        except Exception as e:
            logging.error(f"Error switching to page {key}: {e}")

    page.bottom_appbar = ft.BottomAppBar(
        height=60,
        bgcolor="#00409F",
        shape=ft.NotchShape.CIRCULAR,
        content=ft.Row(
            controls=[
                ft.IconButton(icon=ft.Icons.HOME, icon_color=ft.Colors.WHITE, on_click=lambda e: show_page("home")),
                ft.IconButton(icon=ft.Icons.PEOPLE_ALT_ROUNDED, icon_color=ft.Colors.WHITE, on_click=lambda e: show_page("students")),
                ft.IconButton(icon=ft.Icons.DIVERSITY_3, icon_color=ft.Colors.WHITE, on_click=lambda e: show_page("groups")),
                ft.Container(expand=True),
                ft.IconButton(icon=ft.Icons.MAIL, icon_color=ft.Colors.WHITE, on_click=lambda e: show_page("mails")),
                ft.IconButton(icon=ft.Icons.BARCODE_READER, icon_color=ft.Colors.WHITE, on_click=lambda e: show_page("barcode")),
                ft.IconButton(icon=ft.Icons.SETTINGS, icon_color=ft.Colors.WHITE, on_click=lambda e: show_under_development_dialog(e.page)),
            ]
        ),
    )
    logging.info("Bottom appbar configured")

    # تشغيل البوت بعد تحميل الـ page
    async def start_bot_async():
        await asyncio.sleep(2)  # تأخير 2 ثانية لضمان تحميل الـ UI
        start_bot_later()

    page.run_task(start_bot_async)
    logging.info("Scheduled Telegram bot to start after UI load")

    page.add(main_content)
    page.update()
    logging.info("Main content added to page")

if __name__ == "__main__":
    logging.info("Starting application")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "assets")
    ft.app(target=main, assets_dir=assets_dir)