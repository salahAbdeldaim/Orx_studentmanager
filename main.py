# main.py
import flet as ft
import os

# استيراد الصفحات من مجلد pages
from pages.student_page import student_page
from pages.group_page import group_page
from pages.send_mails_page import send_mails_page
from pages.barcode_page import  barcode_page


# استيراد الدوال المساعدة
from utils.helpers import show_error_dialog, show_success_dialog, show_under_development_dialog
from utils.add_code import init_codes
from utils.telegram_bot import run_telegram_bot
import multiprocessing

# تعريف المسارات الرئيسية للملفات هنا
try:
    # المسار الذي يوجد به الملف التنفيذي أو main.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "assets")

    # تعريف متغيرات مسارات الصور
    app_icon = os.path.join(assets_dir, "icon.ico") 
    facebook = os.path.join(assets_dir, "facebook.png")
    whatsapp = os.path.join(assets_dir, "whatsapp.png")
    linkedin = os.path.join(assets_dir, "linkedin.png")
    gmail = os.path.join(assets_dir, "gmail.png")
    home_gif = os.path.join(assets_dir, "home1.gif")
except Exception as e:
    print(f"Error loading asset paths: {e}")
    # Provide fallback paths or handle the error
    app_icon = None # Or a default icon path

def main(page: ft.Page):
    # تحقق من أن كل الطلاب لديهم كود، وأضف كود لأي طالب لا يوجد له كود
    added_count = init_codes()
    if added_count:
        show_success_dialog(page, f"تم إضافة أكواد جديدة لعدد {added_count} من الطلاب.")
    page.title = "نظام إدارة الطلاب"
    if app_icon and os.path.exists(app_icon):
        page.window.icon = app_icon
    
    page.window.width = 1440
    page.window.height = 900
    page.bgcolor = "#FFFFFF"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.DARK



    # --- الصفحات ---
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

    # حاوية المحتوى الرئيسي
    main_content = ft.Container(content=home_page_content, expand=True)


    pages_map = {
        "home": home_page_content,
        "students": student_page,
        "groups": group_page,
        "mails": send_mails_page,
        "barcode": barcode_page,
    }


    def show_page(key):
        content_function = pages_map[key]
        main_content.content = content_function(page) if callable(content_function) else content_function
        page.update()


    # --- شريط التنقل السفلي ---
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
                ft.IconButton(icon=ft.Icons.BARCODE_READER, icon_color=ft.Colors.WHITE, on_click=lambda e: show_page( "barcode")),
                ft.IconButton(icon=ft.Icons.SETTINGS, icon_color=ft.Colors.WHITE, on_click=lambda e: show_under_development_dialog(e.page)),
                # ... (أضف قائمة منبثقة إذا أردت)
            ]
        ),
    )
    
    page.add(main_content)
    page.update()


if __name__ == "__main__":
    # تشغيل بوت التليجرام في عملية منفصلة
    bot_process = multiprocessing.Process(target=run_telegram_bot)
    bot_process.daemon = True  # سيتم إغلاق البوت عند إغلاق البرنامج الرئيسي
    bot_process.start()
    
    # تأكد من أن Flet يبحث عن مجلد assets في المسار الصحيح
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "assets")
    
    ft.app(target=main, assets_dir=assets_dir)