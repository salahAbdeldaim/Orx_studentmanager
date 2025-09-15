import flet as ft
import sqlite3
from datetime import datetime
from functools import partial
import uuid

import logging

# استيراد من الوحدات الأخرى
from utils.database import students_db_path
from utils.helpers import show_error_dialog, show_success_dialog, search_bar, get_groups,show_skipped_students_dialog,send_telegrem_messege
from utils.whatsapp_manager import send_whatsapp_message, check_internet
from utils.connection_manager import ConnectionManager
from utils.telegram_bot import generate_activation_link,send_telegram_message
from utils.activation_messages import get_activation_message, get_student_welcome_message, get_guardian_welcome_message

# ====== وظائف إدارة قوالب الرسائل ======
def get_exams_message(exams, student_type, n=None):
    """إنشاء نص تقرير الاختبارات"""
    data = exams[-n:] if n else exams
    msg = ""
    for i, (date, full, std_d) in enumerate(data, start=1):
        msg += f"{i}- {date} - الدرجة النهائية: {full} - درجة {student_type}: {std_d}\n"
    return msg.strip()

def get_attendance_message(attendance, n=None):
    """إنشاء نص تقرير الحضور"""
    data = attendance[-n:] if n else attendance
    msg = ""
    for i, (date, day, status) in enumerate(data, start=1):
        msg += f"{i}. {date} - {day} - {status}\n"
    return msg.strip()

def get_payments_message(payments, n=None):
    """إنشاء نص تقرير المدفوعات"""
    data = payments[-n:] if n else payments
    msg = ""
    for i, (month, status) in enumerate(data, start=1):
        msg += f"{i}. {month} - {status}\n"
    return msg.strip()

def create_monthly_report(student_name, student_type, exams, attendance, payments, teacher_name, to_value="ولي الأمر", exams_num=None, attends_num=None, payments_num=None):
    """إنشاء التقرير الشهري الكامل"""
    greeting = f"مرحبًا {student_name}" if to_value == "الطالب" else f"مرحبًا ولي أمر الطالب {student_name}"
    message = f"""{greeting} برجاء الاطلاع على التقرير الشهري...

📝 الاختبارات:
{get_exams_message(exams, student_type, exams_num)}

📅 تقرير الحضور :
{get_attendance_message(attendance, attends_num)}

💵 تقرير حالة الدفع :
{get_payments_message(payments, payments_num)}

مع تحيات {teacher_name}
"""
    return message

def create_attendance_report(student_name, attendance, teacher_name, to_value="ولي الأمر", attends_num=None):
    """إنشاء تقرير الحضور فقط"""
    greeting = f"مرحبًا {student_name}" if to_value == "الطالب" else f"مرحبًا ولي أمر الطالب {student_name}"
    message = f"""{greeting} برجاء الاطلاع على تقرير الحضور...

📅 تقرير الحضور :
{get_attendance_message(attendance, attends_num)}

مع تحيات {teacher_name}
"""
    return message

def create_exams_report(student_name, student_type, exams, teacher_name, to_value="ولي الأمر", exams_num=None):
    """إنشاء تقرير الاختبارات فقط"""
    greeting = f"مرحبًا {student_name}" if to_value == "الطالب" else f"مرحبًا ولي أمر الطالب {student_name}"
    message = f"""{greeting} برجاء الاطلاع على تقرير الاختبارات...

📝 الاختبارات:
{get_exams_message(exams, student_type, exams_num)}

مع تحيات {teacher_name}
"""
    return message

def create_custom_report(template, student_name, student_type, teacher_name, exams, attendance, payments,
                        to_value="ولي الأمر", exams_num=None, attends_num=None, payments_num=None):
    """إنشاء تقرير مخصص باستخدام قالب"""
    greeting = f"مرحبًا {student_name}" if to_value == "الطالب" else f"مرحبًا ولي أمر الطالب {student_name}"
    replacements = {
        "اسم_الطالب": student_name,
        "اسم_المعلم": teacher_name,
        "الطالب/ة": student_type,
        "تقرير_الاختبارات": get_exams_message(exams, student_type, exams_num),
        "تقرير_الحضور": get_attendance_message(attendance, attends_num),
        "تقرير_الدفع": get_payments_message(payments, payments_num),
    }
    message = template
    for key, value in replacements.items():
        message = message.replace(key, value)
    return f"{greeting}\n\n{message}"

# ====== وظائف استرجاع بيانات الطلاب ======
def fetch_students(filter_group=None, filter_search=""):
    """استرجاع قائمة الطلاب حسب المعايير المحددة"""
    if not filter_group and not filter_search:
        return []
    
    from utils.helpers import extract_unique_code
    with sqlite3.connect(students_db_path) as conn:
        c = conn.cursor()
        query = '''SELECT s.id, s.first_name, s.father_name, s.family_name, s.phone, s.guardian_phone, s.gender, g.name as group_name, s.group_id, s.code
                    FROM students s LEFT JOIN groups g ON s.group_id = g.id'''
        params = []
        where = []
        
        if filter_group:
            where.append("s.group_id = ?")
            params.append(filter_group)
        
        search_val = filter_search
        code_val = extract_unique_code(search_val) if search_val else ""
        if search_val:
            where.append("(s.first_name LIKE ? OR s.father_name LIKE ? OR s.family_name LIKE ? OR s.code LIKE ?)")
            val = f"%{search_val}%"
            code_like = f"%{code_val}%"
            params += [val, val, val, code_like]
            
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY s.first_name, s.father_name, s.family_name"
        
        c.execute(query, params)
        students = c.fetchall()
        result = []
        
        from datetime import datetime
        now = datetime.now()
        month_str = now.strftime("%Y-%m")
        
        for s in students:
            student_id, first_name, father_name, family_name, phone, guardian_phone, gender, group_name, group_id, code = s
            full_name = f"{first_name} {father_name} {family_name}"
            
            c.execute('SELECT status FROM payments WHERE student_id=? AND strftime("%Y-%m", month)=? ORDER BY month DESC LIMIT 1', 
                     (student_id, month_str))
            payment_status = c.fetchone()
            payment_status = payment_status[0] if payment_status else "-"
            
            result.append({
                "id": student_id,
                "name": full_name,
                "student_phone": phone,
                "parent_phone": guardian_phone,
                "gender": gender or "-",
                "group": group_name or "-",
                "payment_status": payment_status,
                "code": code,
            })
            
        return result

def get_student_data(student_name):
    """استرجاع كافة بيانات الطالب المطلوبة للتقارير"""
    # استخراج الاسم الثلاثي
    name_parts = student_name.strip().split()
    first, father, family = name_parts[0], name_parts[1] if len(name_parts) > 1 else '', name_parts[2] if len(name_parts) > 2 else ''
    
    student_data = {
        "name": student_name,
        "phone": "",
        "parent_phone": "",
        "gender": "---",
        "type": "الطالب/ة",
        "exams": [],
        "attendance": [],
        "payments": [],
        "code": None,  # الكود الفريد
        "chat_id": None,  # معرف محادثة الطالب في تيليجرام
        "guardian_chat_id": None  # معرف محادثة ولي الأمر في تيليجرام
    }
    
    try:
        with sqlite3.connect(students_db_path) as conn:
            c = conn.cursor()
            # استرجاع البيانات الأساسية
            c.execute("""
                SELECT s.id, s.phone, s.guardian_phone, s.gender, s.code,
                       s.chat_id as student_chat_id,
                       s.guardian_chat_id as guardian_chat_id
                FROM students s
                WHERE s.first_name=? AND s.father_name=? AND s.family_name=?
            """, (first, father, family))
            
            row = c.fetchone()
            if row:
                student_id, phone, parent_phone, gender, code, student_chat_id, guardian_chat_id = row
                student_data.update({
                    "phone": phone,
                    "parent_phone": parent_phone,
                    "gender": gender,
                    "type": "الطالب" if gender == "ذكر" else "الطالبة" if gender == "انثى" else "الطالب/ة",
                    "code": str(code) if code else None,
                    "chat_id": str(student_chat_id) if student_chat_id else None,
                    "guardian_chat_id": str(guardian_chat_id) if guardian_chat_id else None
                })
                
                # استرجاع بيانات الاختبارات
                c.execute("SELECT exam_date, total_score, student_score FROM exams WHERE student_id=? ORDER BY exam_date", (student_id,))
                student_data["exams"] = [list(map(str, r)) for r in c.fetchall()]
                
                # استرجاع بيانات الحضور
                c.execute("SELECT attendance_date, status FROM attendance WHERE student_id=? ORDER BY attendance_date", (student_id,))
                att_rows = c.fetchall()
                attendance = []
                for att in att_rows:
                    date_str, status = att
                    try:
                        day_name = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
                        days_ar = {
                            "Monday": "الاثنين", "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء",
                            "Thursday": "الخميس", "Friday": "الجمعة", "Saturday": "السبت", "Sunday": "الأحد"
                        }
                        day_ar = days_ar.get(day_name, day_name)
                        attendance.append([date_str, day_ar, status])
                    except ValueError:
                        attendance.append([date_str, "تاريخ غير صالح", status])
                
                student_data["attendance"] = attendance
                
                # استرجاع بيانات المدفوعات
                c.execute("SELECT month, status FROM payments WHERE student_id=? ORDER BY month", (student_id,))
                student_data["payments"] = [list(r) for r in c.fetchall()]
                
    except sqlite3.Error as e:
        print(f"خطأ في الاتصال بقاعدة البيانات: {e}")
        
    return student_data

# ====== وظائف إرسال الرسائل ======
def send_whatsapp_messege(student_data, message, to_value="ولي الأمر", page=None):
    """إرسال رسالة واتساب للطالب أو ولي الأمر"""
    if page:
        show_success_dialog(page, "يتم محاولة ارسال الرسالة...")
    
    # تحديد رقم الهاتف بناءً على المستلم
    phone = student_data["parent_phone"] if to_value == "ولي الأمر" else student_data["phone"]
    
    if not phone or not str(phone).strip():
        if page:
            show_error_dialog(page, "❌ لا يوجد رقم هاتف لهذا الطالب أو ولي الأمر. تم تخطي الإرسال.")
        return False, "لا يوجد رقم هاتف"
    
    success, message = send_whatsapp_message(phone, message)
    if page:
        if success:
            show_success_dialog(page, "✅ " + message)
        else:
            show_error_dialog(page, "⚠️ " + message)
    
    return success, message

# ====== مكونات واجهة المستخدم ======
def create_shortcuts_box(on_shortcut_click):
    """إنشاء مربع الاختصارات"""
    return ft.Container(
        bgcolor="#0059DF",
        border=ft.border.all(1, "#CBD5E1"),
        border_radius=8,
        padding=10,
        expand=True,
        content=ft.Column([
            ft.Text(
                "📌 الاختصارات المتاحة:",
                weight=ft.FontWeight.BOLD,
                size=16,
                color="#FFFFFF",
                text_align=ft.TextAlign.RIGHT,
            ),
            ft.Container(
                expand=True,
                content=ft.Row(
                    [
                        ft.ElevatedButton("اسم_الطالب", on_click=lambda e: on_shortcut_click(e, "اسم_الطالب")),
                        ft.ElevatedButton("اسم_المعلم", on_click=lambda e: on_shortcut_click(e, "اسم_المعلم")),
                        ft.ElevatedButton("الطالب/ة", on_click=lambda e: on_shortcut_click(e, "الطالب/ة")),
                        ft.ElevatedButton("تقرير الاختبارات", on_click=lambda e: on_shortcut_click(e, "تقرير_الاختبارات")),
                        ft.ElevatedButton("تقرير الحضور", on_click=lambda e: on_shortcut_click(e, "تقرير_الحضور")),
                        ft.ElevatedButton("تقرير الدفع", on_click=lambda e: on_shortcut_click(e, "تقرير_الدفع")),
                    ],
                    spacing=10,
                    wrap=True,
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                    expand=True,
                ),
                bgcolor="#0059DF",
                border_radius=8,
                padding=5,
            ),
        ],
        spacing=10,
        expand=True,
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        scroll=ft.ScrollMode.AUTO,
        ),
    )

def create_preview_container(content=""):
    """إنشاء مربع معاينة الرسالة"""
    return ft.Container(
        bgcolor="#0059DF",
        padding=15,
        border=ft.border.all(1, "#E2E8F0"),
        border_radius=10,
        expand=True,
        alignment=ft.alignment.top_right,
        content=ft.Text(
            content,
            selectable=True,
            size=16,
            color="white",
        ),
    )

def create_message_form(student_data, on_preview_change, on_send_click):
    """إنشاء نموذج إرسال الرسائل"""
    send_to_ddawn = ft.Dropdown(
        label="اختر المستلم",
        hint_text="ولي الأمر",
        options=[
            ft.dropdown.Option("ولي الأمر"),
            ft.dropdown.Option("الطالب"),
        ],
        value="ولي الأمر",
        expand=True,
        on_change=on_preview_change
    )

    send_what_ddawn = ft.Dropdown(
        label="اختر القالب",
        hint_text="تقرير كامل",
        options=[
            ft.dropdown.Option("تقرير كامل"),
            ft.dropdown.Option("تقرير الحضور"),
            ft.dropdown.Option("تقرير الاختبارات"),
            ft.dropdown.Option("رسالة مخصصة"),
        ],
        value="تقرير كامل",
        expand=True,
        on_change=on_preview_change
    )

    get_exams_num = ft.TextField(
        label="عدد الامتحانات",
        hint_text="مثال: 3",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
        on_change=on_preview_change
    )

    get_attends_num = ft.TextField(
        label="عدد الحضور",
        hint_text="مثال: 5",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
        on_change=on_preview_change
    )

    get_payments_num = ft.TextField(
        label="عدد الدفعات",
        hint_text="مثال: 2",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
        on_change=on_preview_change
    )
    
    cstm_msg = ft.TextField(
        label="اكتب رسالة مخصصة",
        multiline=True,
        min_lines=4,
        expand=True,
        hint_text="اكتب رسالتك هنا (مثال: مرحبًا اسم_الطالب، مع تحيات اسم_المعلم)",
        height=120,
        on_change=on_preview_change
    )

    # إرجاع العناصر والنموذج
    return {
        "form": ft.Column([
            ft.Row([send_to_ddawn, send_what_ddawn]),
            ft.Row([get_exams_num, get_attends_num, get_payments_num]),
            cstm_msg,
            
        ]),
        "controls": {
            "send_to": send_to_ddawn,
            "send_what": send_what_ddawn,
            "exams_num": get_exams_num,
            "attends_num": get_attends_num,
            "payments_num": get_payments_num,
            "custom_msg": cstm_msg
        }
    }

def send_mails_page(page: ft.Page):

    """الصفحة الرئيسية لإرسال الرسائل"""
    # تهيئة مدير الاتصال
    conn_manager = ConnectionManager()
    conn_manager.start_monitoring()

    # مؤشر حالة الاتصال
    connection_status = ft.Container(
        width=15,
        height=15,
        border_radius=50,
        bgcolor=ft.Colors.GREEN if conn_manager.is_online else ft.Colors.RED,
        tooltip="متصل بالإنترنت" if conn_manager.is_online else "غير متصل بالإنترنت"
    )

    def update_connection_status(is_online):
        """تحديث حالة الاتصال"""
        connection_status.bgcolor = ft.Colors.GREEN if is_online else ft.Colors.RED
        connection_status.tooltip = "متصل بالإنترنت" if is_online else "غير متصل بالإنترنت"
        page.update()

    # تسجيل المستمع لتغييرات حالة الاتصال
    conn_manager.add_status_listener(update_connection_status)

    side_rec_container = ft.Container(
        margin=ft.margin.only(left=10, right=0, top=10, bottom=10),
        padding=10,
        alignment=ft.alignment.center,
        bgcolor="#3B7EFF",
        border_radius=10,
        expand=4,
        content=ft.Column([
            ft.Row([
                ft.Text("اختر عملية من القائمة", size=20, weight="bold"),
                connection_status
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ])
    )

    def update_side_content(new_content):
        """تحديث محتوى القائمة الجانبية"""
        side_rec_container.content = new_content
        page.update()

    def send_student_container():
        """حاوية إرسال رسالة فردية"""
        filter_group = {"value": None}
        filter_search = {"value": ""}

        def on_name_click(e, student):
            """معالجة النقر على اسم الطالب"""
            update_side_content(send_to_student_container(student["name"]))

        def refresh_table():
            """تحديث جدول الطلاب"""
            nonlocal student_table
            students_data = fetch_students(filter_group["value"], filter_search["value"])
            if not students_data:
                student_table.rows = [
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text('لا يوجد طلاب لعرضهم', text_align='center', color='red', weight='bold'))
                        ] + [ft.DataCell(ft.Text(''))]*6)
                ]
            else:
                student_table.rows = [
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(idx+1), text_align="center", color="#1E3A8A", weight="bold")),
                            ft.DataCell(
                                ft.TextButton(
                                    text=s["name"],
                                    on_click=lambda e, student=s: on_name_click(e, student),
                                    style=ft.ButtonStyle(color="#0077CC"),
                                    tooltip="تمرير"
                                )
                            ),
                            ft.DataCell(
                                ft.TextButton(
                                    text=s["student_phone"] or "-",
                                    url=f"https://wa.me/{s['student_phone'].replace('+', '')}" if s["student_phone"] else None,
                                    style=ft.ButtonStyle(color="#25D366"),
                                    tooltip="تواصل واتساب مع الطالب",
                                    disabled=not s["student_phone"]
                                )
                            ),
                            ft.DataCell(
                                ft.TextButton(
                                    text=s["parent_phone"] or "-",
                                    url=f"https://wa.me/{s['parent_phone'].replace('+', '')}" if s["parent_phone"] else None,
                                    style=ft.ButtonStyle(color="#0D6EFD"),
                                    tooltip="تواصل واتساب مع ولي الأمر",
                                    disabled=not s["parent_phone"]
                                )
                            ),
                            ft.DataCell(ft.Text(s["gender"], text_align="center", color="#000000")),
                            ft.DataCell(ft.Text(s["group"], text_align="center", color="#000000")),
                            ft.DataCell(ft.Text(s["payment_status"], text_align="center", color="green" if s["payment_status"]=="دفع" else "red", weight="bold")),
                        ]
                    )
                    for idx, s in enumerate(students_data)
                ]
            page.update()

        def on_search_submit(e=None):
            """معالجة البحث عن طالب"""
            from utils.helpers import extract_unique_code
            val = e.control.value.strip() if e else ""
            if val:
                val = extract_unique_code(val)
            filter_search["value"] = val
            refresh_table()

        def on_group_change(e):
            """معالجة تغيير المجموعة"""
            filter_group["value"] = std_group.value
            refresh_table()

        std_group = ft.Dropdown(
            label="المجموعة",
            hint_text="اختر مجموعة",
            options=get_groups(),
            expand=True,
            on_change=on_group_change
        )

        student_table = ft.DataTable(
            expand=True,
            column_spacing=30,
            data_row_min_height=50,
            heading_row_color="#1E3A8A",
            border=ft.border.all(1, "#1E3A8A"),
            divider_thickness=1,
            columns=[
                ft.DataColumn(ft.Text("#", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("اسم الطالب", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("هاتف الطالب", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("هاتف الأب", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("النوع", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("المجموعة", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("حالة الدفع (الشهر الحالي)", weight="bold", color="white", text_align="center")),
            ],
            rows=[],
        )

        return ft.Container(
            border=ft.border.all(2, "#FFFFFF"),
            expand=True,
            padding=20,
            border_radius=12,
            alignment=ft.alignment.center,
            content=ft.Column(
                [
                    ft.Column(
                        [
                            ft.Text(
                                "ارسال رسالة فردية",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.CENTER,
                                color="white"
                            ),
                            ft.Divider(height=20, color="white"),
                            ft.Container(
                                expand=False,
                                content=ft.Column(
                                    spacing=10,
                                    controls=[
                                        search_bar("ابحث عن طالب...", on_submit=on_search_submit),
                                        std_group
                                    ]
                                )
                            ),
                        ],
                        spacing=5,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(
                        expand=True,
                        bgcolor="#F4F4F4",
                        border_radius=10,
                        padding=10,
                        border=ft.border.all(1, "#CBD5E1"),
                        content=ft.Column(
                            expand=True,
                            scroll=ft.ScrollMode.AUTO,
                            controls=[
                                ft.Row(
                                    controls=[student_table],
                                    scroll=ft.ScrollMode.AUTO,
                                    expand=True,
                                )
                            ]
                        )
                    ),
                ],
                expand=True,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                rtl=True,
            ),
        )

    def send_to_student_container(student_name):
        """حاوية نموذج إرسال للطالب المحدد"""
        if not conn_manager.check_connection(show_message=True, page=page):
            return ft.Text("⚠️ لا يوجد اتصال بالإنترنت", color="red")

        student_data = get_student_data(student_name)
        teacher_name = "مستر / احمد العبادي"

        def update_preview(e=None):
            """تحديث معاينة الرسالة"""
            to_value = form_controls["send_to"].value or "ولي الأمر"
            what_value = form_controls["send_what"].value or "تقرير كامل"
            exams_num = int(form_controls["exams_num"].value) if form_controls["exams_num"].value and form_controls["exams_num"].value.isdigit() else None
            attends_num = int(form_controls["attends_num"].value) if form_controls["attends_num"].value and form_controls["attends_num"].value.isdigit() else None
            payments_num = int(form_controls["payments_num"].value) if form_controls["payments_num"].value and form_controls["payments_num"].value.isdigit() else None

            greeting = f"مرحبًا {student_name}" if to_value == "الطالب" else f"مرحبًا ولي أمر الطالب {student_name}"
            if what_value == "رسالة مخصصة" and not form_controls["custom_msg"].value.strip():
                msg = "❌ يرجى كتابة رسالة مخصصة."
            elif what_value == "رسالة مخصصة":
                msg = create_custom_report(
                    form_controls["custom_msg"].value, student_name, student_data["type"], teacher_name,
                    student_data["exams"], student_data["attendance"], student_data["payments"],
                    to_value, exams_num, attends_num, payments_num
                )
            elif what_value == "تقرير كامل":
                msg = create_monthly_report(
                    student_name, student_data["type"], student_data["exams"], student_data["attendance"],
                    student_data["payments"], teacher_name, to_value, exams_num, attends_num, payments_num
                )
            elif what_value == "تقرير الحضور":
                msg = create_attendance_report(student_name, student_data["attendance"], teacher_name, to_value, attends_num)
            elif what_value == "تقرير الاختبارات":
                msg = create_exams_report(student_name, student_data["type"], student_data["exams"], teacher_name, to_value, exams_num)
            else:
                msg = "❌ لم يتم اختيار تقرير."

            preview_container.content.value = f"""
            {greeting}

            📌 المستلم: {to_value}
            📌 نوع التقرير: {what_value}

            ✉️ الرسالة:
            {msg}
            """
            page.update()

        def on_send_click(e):
            """معالجة إرسال الرسالة"""
            # التحقق من اختيار منصة الإرسال
            send_platform = send_how.value
            if not send_platform:
                show_error_dialog(page, "⚠️ يرجى اختيار منصة الإرسال (واتساب أو تليجرام)")
                return

            what_value = form_controls["send_what"].value or "تقرير كامل"
            exams_num = int(form_controls["exams_num"].value) if form_controls["exams_num"].value and form_controls["exams_num"].value.isdigit() else None
            attends_num = int(form_controls["attends_num"].value) if form_controls["attends_num"].value and form_controls["attends_num"].value.isdigit() else None
            payments_num = int(form_controls["payments_num"].value) if form_controls["payments_num"].value and form_controls["payments_num"].value.isdigit() else None

            if what_value == "رسالة مخصصة" and not form_controls["custom_msg"].value.strip():
                show_error_dialog(page, "❌ يرجى كتابة رسالة مخصصة.")
                return
            elif what_value == "رسالة مخصصة":
                msg = create_custom_report(
                    form_controls["custom_msg"].value, student_name, student_data["type"], teacher_name,
                    student_data["exams"], student_data["attendance"], student_data["payments"],
                    form_controls["send_to"].value, exams_num, attends_num, payments_num
                )
            elif what_value == "تقرير كامل":
                msg = create_monthly_report(
                    student_name, student_data["type"], student_data["exams"], student_data["attendance"],
                    student_data["payments"], teacher_name, form_controls["send_to"].value, exams_num, attends_num, payments_num
                )
            elif what_value == "تقرير الحضور":
                msg = create_attendance_report(student_name, student_data["attendance"], teacher_name, form_controls["send_to"].value, attends_num)
            elif what_value == "تقرير الاختبارات":
                msg = create_exams_report(student_name, student_data["type"], student_data["exams"], teacher_name, form_controls["send_to"].value, exams_num)
            else:
                show_error_dialog(page, "❌ لم يتم اختيار تقرير.")
                return

            # الحصول على المستلم
            to_value = form_controls["send_to"].value or "ولي الأمر"
            
            # إرسال الرسالة حسب المنصة المختارة
            if send_platform == "واتساب":
                send_whatsapp_messege(student_data, msg, to_value, page)
            elif send_platform == "تليجرام":
                send_telegrem_messege(student_data, msg, to_value, page)

        def on_send_activation_click(e):
            """معالجة إرسال رسالة التفعيل للطالب أو ولي الأمر"""
            if not conn_manager.check_connection(show_message=True, page=page):
                return
        
            # التحقق من وجود الكود الفريد
            if not student_data.get("code"):
                show_error_dialog(page, "❌ عذراً، لم يتم العثور على كود فريد للطالب!")
                logging.error(f"محاولة إرسال رسالة تفعيل لطالب بدون كود فريد: {student_data['name']}")
                return
        
            # تحديد نوع المستلم (طالب / ولي الأمر)
            send_to = form_controls["send_to"].value or "ولي الأمر"
            is_guardian = send_to == "ولي الأمر"
        
            # تعديل الكود حسب المستلم (ولي الأمر → الكود + "1")
            activation_code = (
                f"{student_data['code']}1" if is_guardian else student_data["code"]
            )
        
            # إنشاء رسالة التفعيل
            msg = get_activation_message(
                student_data["name"],
                activation_code,
                is_guardian
            )
        
            # إرسال الرسالة عبر واتساب
            success, message = send_whatsapp_messege(student_data, msg, send_to, page)
        
            if success:
                show_success_dialog(page, "✅ تم إرسال رابط التفعيل بنجاح!")
                logging.info(f"تم إرسال رابط التفعيل للطالب {student_data['name']} ({send_to})")
        
                # تحديث المعاينة لعرض الرسالة المرسلة
                preview_container.content.value = f"""
                تم إرسال رسالة التفعيل التالية:
        
                {msg}
                """
                page.update()
            else:
                show_error_dialog(page, f"❌ فشل إرسال رابط التفعيل: {message}")
                logging.error(f"فشل إرسال رابط التفعيل للطالب {student_data['name']} ({send_to}): {message}")
        
        
        preview_container = create_preview_container("هنا يظهر التقرير أو الرسالة...")
        form_data = create_message_form(student_data, update_preview, on_send_click)
        form = form_data["form"]
        form_controls = form_data["controls"]

        def insert_shortcut(e, text_to_insert):
            """إدراج اختصار في حقل الرسالة المخصصة"""
            current_text = form_controls["custom_msg"].value or ""
            form_controls["custom_msg"].value = current_text + text_to_insert
            form_controls["custom_msg"].update()
            update_preview(e)

        shortcuts_box = create_shortcuts_box(insert_shortcut)
        update_preview()

        send_how = ft.Dropdown(
            label="اختر منصة الارسال",
            hint_text="تليجرام",
            options=[ft.dropdown.Option(d) for d in ["تليجرام", "واتساب"]],
            text_align=ft.TextAlign.RIGHT,
            expand=True
        )

        return ft.Container(
            border=ft.border.all(2, "#FFFFFF"),
            expand=True,
            padding=20,
            border_radius=12,
            alignment=ft.alignment.center,
            content=ft.Column(
                [
                    ft.Column(
                        [
                            ft.Text(
                                f"ارسال رسالة للطالب: {student_name}",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.CENTER,
                                color="white"
                            ),
                            ft.Divider(height=20, color="white"),
                        ],
                        spacing=5,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(
                        expand=True,
                        border_radius=10,
                        padding=10,
                        border=ft.border.all(1, "#CBD5E1"),
                        content=ft.ResponsiveRow(
                            [
                                ft.Column(
                                    scroll=ft.ScrollMode.AUTO,
                                    col={"sm": 12, "md": 4},
                                    controls=[
                                        form,
                                        send_how,
                                        shortcuts_box,
                                    ],
                                    expand=True,
                                    spacing=10,
                                ),
                                ft.Column(
                                    col={"sm": 12, "md": 8},
                                    controls=[preview_container],
                                    expand=True,
                                    alignment=ft.MainAxisAlignment.START,
                                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                                ),
                            ],
                            expand=True,
                            spacing=10,
                        ),
                    ),
                    ft.Row(
                            [
                                ft.ElevatedButton(
                                    content=ft.Row(
                                        [
                                            ft.Text("ارسال", size=18, weight=ft.FontWeight.BOLD, color="#F5F5F5"),
                                            ft.Icon(ft.Icons.SEND, size=28, color="#07C06A"),
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        spacing=10
                                    ),
                                    height=50,
                                    expand=True,
                                    bgcolor="#0059DF",
                                    on_click=on_send_click,
                                ),
                                ft.ElevatedButton(
                                content=ft.Row(
                                    [
                                        ft.Text("ارسال رسالة التفعيل", size=18, weight=ft.FontWeight.BOLD, color="#F5F5F5"),
                                        ft.Icon(ft.Icons.SEND, size=28, color="#FFD000"),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=10
                                ),
                                height=50,
                                expand=True,
                                bgcolor="#0059DF",
                                on_click=on_send_activation_click,
                            ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_AROUND,
                            spacing=20,
                        ),
                ],
                expand=True,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                rtl=True,
            ),
        )
 
    def send_group_student_container():
        """حاوية إرسال رسائل جماعية"""
        teacher_name = "مستر / احمد العبادي"

        def get_students_count_by_level(grade):
            """عدد الطلاب في الصف"""
            try:
                with sqlite3.connect(students_db_path) as conn:
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*) FROM students WHERE grade=?", (grade,))
                    return c.fetchone()[0]
            except sqlite3.Error:
                return 0

        def get_students_count_by_group(group_id):
            """عدد الطلاب في المجموعة"""
            try:
                with sqlite3.connect(students_db_path) as conn:
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*) FROM students WHERE group_id=?", (group_id,))
                    return c.fetchone()[0]
            except sqlite3.Error:
                return 0

        def get_students_by_level(grade):
            """استرجاع طلاب الصف"""
            try:
                with sqlite3.connect(students_db_path) as conn:
                    c = conn.cursor()
                    c.execute("SELECT id, first_name, father_name, family_name FROM students WHERE grade=?", (grade,))
                    return c.fetchall()
            except sqlite3.Error as e:
                print(f"خطأ في قاعدة البيانات: {e}")
                return []

        def get_students_by_group(group_id):
            """استرجاع طلاب المجموعة"""
            try:
                with sqlite3.connect(students_db_path) as conn:
                    c = conn.cursor()
                    c.execute("SELECT id, first_name, father_name, family_name FROM students WHERE group_id=?", (group_id,))
                    return c.fetchall()
            except sqlite3.Error as e:
                print(f"خطأ في قاعدة البيانات: {e}")
                return []

        def update_preview_and_counts(e=None):
            """تحديث المعاينة وعدد الطلاب"""
            selected_level = level_ddawn.value
            selected_group = groups_ddawn.value
            title_text.value = "ارسال رسائل جماعية"
            number_of_group_students = 0
            sample_student_data = None

            if selected_level:
                title_text.value += f" - الصف: {selected_level}"
                number_of_group_students = get_students_count_by_level(selected_level)
                students = get_students_by_level(selected_level)
                if students:
                    sample_student_data = get_student_data(f"{students[0][1]} {students[0][2]} {students[0][3]}")
            elif selected_group:
                title_text.value += f" - المجموعة: {selected_group}"
                number_of_group_students = get_students_count_by_group(selected_group)
                students = get_students_by_group(selected_group)
                if students:
                    sample_student_data = get_student_data(f"{students[0][1]} {students[0][2]} {students[0][3]}")

            num_of_std.content.value = f"الطالب: 0 من {number_of_group_students}"

            to_value = form_controls["send_to"].value or "ولي الأمر"
            what_value = form_controls["send_what"].value or "تقرير كامل"
            exams_num = int(form_controls["exams_num"].value) if form_controls["exams_num"].value and form_controls["exams_num"].value.isdigit() else None
            attends_num = int(form_controls["attends_num"].value) if form_controls["attends_num"].value and form_controls["attends_num"].value.isdigit() else None
            payments_num = int(form_controls["payments_num"].value) if form_controls["payments_num"].value and form_controls["payments_num"].value.isdigit() else None

            if sample_student_data:
                student_name = sample_student_data["name"]
                greeting = f"مرحبًا {student_name}" if to_value == "الطالب" else f"مرحبًا ولي أمر الطالب {student_name}"
                if what_value == "رسالة مخصصة" and not form_controls["custom_msg"].value.strip():
                    msg = "❌ يرجى كتابة رسالة مخصصة."
                elif what_value == "رسالة مخصصة":
                    msg = create_custom_report(
                        form_controls["custom_msg"].value, student_name, sample_student_data["type"], teacher_name,
                        sample_student_data["exams"], sample_student_data["attendance"], sample_student_data["payments"],
                        to_value, exams_num, attends_num, payments_num
                    )
                elif what_value == "تقرير كامل":
                    msg = create_monthly_report(
                        student_name, sample_student_data["type"], sample_student_data["exams"], sample_student_data["attendance"],
                        sample_student_data["payments"], teacher_name, to_value, exams_num, attends_num, payments_num
                    )
                elif what_value == "تقرير الحضور":
                    msg = create_attendance_report(student_name, sample_student_data["attendance"], teacher_name, to_value, attends_num)
                elif what_value == "تقرير الاختبارات":
                    msg = create_exams_report(student_name, sample_student_data["type"], sample_student_data["exams"], teacher_name, to_value, exams_num)
                else:
                    msg = "❌ لم يتم اختيار تقرير."
            else:
                msg = "يرجى اختيار صف أو مجموعة لعرض المعاينة."
                greeting = "مرحبًا"

            preview_container.content.value = f"""
            {greeting}

            📌 المستلم: {to_value}
            📌 نوع التقرير: {what_value}

            ✉️ الرسالة:
            {msg}
            """
            page.update()

        def on_send_click(e):
            """معالجة إرسال الرسائل الجماعية"""
            if not conn_manager.check_connection(show_message=True, page=page):
                return

            selected_level = level_ddawn.value
            selected_group = groups_ddawn.value
            if not selected_level and not selected_group:
                show_error_dialog(page, "⚠️ يرجى اختيار صف أو مجموعة.")
                return

            students = get_students_by_level(selected_level) if selected_level else get_students_by_group(selected_group)
            if not students:
                show_error_dialog(page, "⚠️ لا يوجد طلاب في هذا الصف أو المجموعة.")
                return

            what_value = form_controls["send_what"].value or "تقرير كامل"
            exams_num = int(form_controls["exams_num"].value) if form_controls["exams_num"].value and form_controls["exams_num"].value.isdigit() else None
            attends_num = int(form_controls["attends_num"].value) if form_controls["attends_num"].value and form_controls["attends_num"].value.isdigit() else None
            payments_num = int(form_controls["payments_num"].value) if form_controls["payments_num"].value and form_controls["payments_num"].value.isdigit() else None

            # التحقق من اختيار منصة الإرسال
            send_platform = send_how.value
            if not send_platform:
                show_error_dialog(page, "⚠️ يرجى اختيار منصة الإرسال (واتساب أو تليجرام)")
                return

            show_success_dialog(page, "يتم محاولة ارسال الرسائل...")
            current_student_count = 0
            skipped_students = []

            for student in students:
                student_name = f"{student[1]} {student[2]} {student[3]}"
                student_data = get_student_data(student_name)

                # الحصول على المستلم
                to_value = form_controls["send_to"].value or "ولي الأمر"
                is_guardian = to_value == "ولي الأمر"

                # التحقق من وجود بيانات الاتصال المطلوبة
                if send_platform == "واتساب":
                    required_phone = student_data["parent_phone"] if is_guardian else student_data["phone"]
                    if not required_phone:
                        skipped_students.append(f"{student_name} (لا يوجد رقم هاتف {to_value})")
                        continue
                elif send_platform == "تليجرام":
                    required_chat_id = student_data["guardian_chat_id"] if is_guardian else student_data["chat_id"]
                    if not required_chat_id:
                        skipped_students.append(f"{student_name} (لا يوجد معرف تليجرام {to_value})")
                        continue

                if what_value == "رسالة مخصصة" and not form_controls["custom_msg"].value.strip():
                    show_error_dialog(page, "❌ يرجى كتابة رسالة مخصصة.")
                    continue
                elif what_value == "رسالة مخصصة":
                    msg = create_custom_report(
                        form_controls["custom_msg"].value, student_name, student_data["type"], teacher_name,
                        student_data["exams"], student_data["attendance"], student_data["payments"],
                        form_controls["send_to"].value, exams_num, attends_num, payments_num
                    )
                elif what_value == "تقرير كامل":
                    msg = create_monthly_report(
                        student_name, student_data["type"], student_data["exams"], student_data["attendance"],
                        student_data["payments"], teacher_name, form_controls["send_to"].value, exams_num, attends_num, payments_num
                    )
                elif what_value == "تقرير الحضور":
                    msg = create_attendance_report(student_name, student_data["attendance"], teacher_name, form_controls["send_to"].value, attends_num)
                elif what_value == "تقرير الاختبارات":
                    msg = create_exams_report(student_name, student_data["type"], student_data["exams"], teacher_name, form_controls["send_to"].value, exams_num)
                else:
                    show_error_dialog(page, "❌ لم يتم اختيار تقرير.")
                    continue

                # الحصول على المستلم
                to_value = form_controls["send_to"].value or "ولي الأمر"

                preview_container.content.value = f"""
                {f"مرحبًا {student_name}" if to_value == "الطالب" else f"مرحبًا ولي أمر الطالب {student_name}"}

                📌 المستلم: {to_value}
                📌 نوع التقرير: {what_value}
                📱 منصة الإرسال: {send_platform}

                ✉️ الرسالة:
                {msg}
                """
                page.update()

                # إرسال الرسالة حسب المنصة المختارة
                if send_platform == "واتساب":
                    success, message = send_whatsapp_messege(student_data, msg, to_value, page)
                elif send_platform == "تليجرام":
                    success, message = send_telegrem_messege(student_data, msg, to_value, page)

                if success:
                    current_student_count += 1
                    num_of_std.content.value = f"الطالب: {current_student_count} من {len(students)}"
                    page.update()
                else:
                    if "اتصال" in message or "إنترنت" in message:
                        break

            # بعد حلقة الإرسال
            show_skipped_students_dialog(page, skipped_students)

            # النتيجة النهائية
            print(f" تم إرسال {current_student_count} من أصل {len(students)} عبر {send_platform}")
            show_success_dialog(page, f"✅ تم إرسال {current_student_count} رسالة من أصل {len(students)}")


        def on_send_activation_click(e):
            if not conn_manager.check_connection(show_message=True, page=page):
                return      

            selected_level = level_ddawn.value
            selected_group = groups_ddawn.value
            if not selected_level and not selected_group:
                show_error_dialog(page, "⚠️ يرجى اختيار صف أو مجموعة.")
                return      

            students = get_students_by_level(selected_level) if selected_level else get_students_by_group(selected_group)
            if not students:
                show_error_dialog(page, "⚠️ لا يوجد طلاب في هذا الصف أو المجموعة.")
                return      

            # التحقق من اختيار منصة الإرسال
            send_platform = send_how.value
            if not send_platform:
                show_error_dialog(page, "⚠️ يرجى اختيار منصة الإرسال (واتساب أو تليجرام)")
                return

            show_success_dialog(page, "جاري إرسال روابط التفعيل...")
            current_student_count = 0
            total_students = len(students)
            skipped_students = []

            for student in students:
                student_name = f"{student[1]} {student[2]} {student[3]}"
                student_data = get_student_data(student_name)
                
                # إرسال رسالة التفعيل للمستلم المحدد (طالب/ولي أمر)
                to_value = form_controls["send_to"].value or "ولي الأمر"
                is_guardian = to_value == "ولي الأمر"

                # التحقق من وجود بيانات الاتصال المطلوبة
                if send_platform == "واتساب":
                    required_phone = student_data["parent_phone"] if is_guardian else student_data["phone"]
                    if not required_phone:
                        skipped_students.append(f"{student_name} (لا يوجد رقم هاتف {to_value})")
                        continue
                elif send_platform == "تليجرام":
                    required_chat_id = student_data["guardian_chat_id"] if is_guardian else student_data["chat_id"]
                    if not required_chat_id:
                        skipped_students.append(f"{student_name} (لا يوجد معرف تليجرام {to_value})")
                        continue

                # التحقق من وجود الكود الفريد
                if not student_data.get("code"):
                    skipped_students.append(f"{student_name} (لا يوجد كود فريد)")
                    logging.warning(f"لم يتم العثور على كود فريد للطالب {student_name}")
                    continue

                # إنشاء رابط التفعيل
                activation_link = generate_activation_link(student_data["code"], "guardian" if is_guardian else "student")

                # إنشاء رسالة التفعيل
                from utils.activation_messages import get_activation_message
                msg = get_activation_message(student_data["name"], student_data["code"], is_guardian)

                if msg:
                    # إرسال الرسالة حسب المنصة المختارة
                    if send_platform == "واتساب":
                        success, _ = send_whatsapp_messege(student_data, msg, to_value, page)
                    else:  # تليجرام
                        success, _ = send_telegrem_messege(student_data, msg, to_value, page)

                    if success:
                        current_student_count += 1
                        num_of_std.content.value = f"تم الإرسال إلى {current_student_count} من {total_students}"
                        page.update()

            # عرض قائمة الطلاب الذين تم تخطيهم
            show_skipped_students_dialog(page, skipped_students)

            show_success_dialog(page, f"✅ تم إرسال {current_student_count} رسالة تفعيل من أصل {total_students}")       
 
        title_text = ft.Text(
            "ارسال رسائل جماعية",
            size=24,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
            color="white"
        )

        level_ddawn = ft.Dropdown(
            label="اختر الصف",
            hint_text="الثاني الاعدادي",
            options=[
                ft.dropdown.Option("الاول الابتدائي"),
                ft.dropdown.Option("الثاني الابتدائي"),
                ft.dropdown.Option("الثالث الابتدائي"),
                ft.dropdown.Option("الرابع الابتدائي"),
                ft.dropdown.Option("الخامس الابتدائي"),
                ft.dropdown.Option("السادس الابتدائي"),
                ft.dropdown.Option("الأول الإعدادي"),
                ft.dropdown.Option("الثاني الإعدادي"),
                ft.dropdown.Option("الثالث الإعدادي"),
                ft.dropdown.Option("الأول الثانوي"),
                ft.dropdown.Option("الثاني الثانوي"),
                ft.dropdown.Option("الثالث الثانوي"),
            ],
            expand=True,
            on_change=update_preview_and_counts
        )

        groups_ddawn = ft.Dropdown(
            label="اختر المجموعة",
            hint_text="مجموعة ج (السبت والثلاثاء)",
            options=get_groups(),
            expand=True,
            on_change=update_preview_and_counts
        )

        send_how = ft.Dropdown(
            label="اختر منصة الارسال",
            hint_text="تليجرام",
            options=[ft.dropdown.Option(d) for d in ["تليجرام", "واتساب"]],
            text_align=ft.TextAlign.RIGHT,
            expand=True
        )

        preview_container = create_preview_container("هنا يظهر التقرير أو الرسالة...")
        form_data = create_message_form({}, update_preview_and_counts, on_send_click)
        form = form_data["form"]
        form_controls = form_data["controls"]

        def insert_shortcut(e, text_to_insert):
            """إدراج اختصار في حقل الرسالة المخصصة"""
            current_text = form_controls["custom_msg"].value or ""
            form_controls["custom_msg"].value = current_text + text_to_insert
            form_controls["custom_msg"].update()
            update_preview_and_counts(e)

        shortcuts_box = create_shortcuts_box(insert_shortcut)
        num_of_std = ft.Container(
            bgcolor="#0059DF",
            border=ft.border.all(1, "#CBD5E1"),
            border_radius=8,
            padding=10,
            expand=True,
            content=ft.Text(
                "الطالب: 0 من 0",
                weight=ft.FontWeight.BOLD,
                size=16,
                color="#FFFFFF",
                text_align=ft.TextAlign.RIGHT,
            ),
        )

        update_preview_and_counts()

        return ft.Container(
            border=ft.border.all(2, "#FFFFFF"),
            expand=True,
            padding=20,
            border_radius=12,
            alignment=ft.alignment.center,
            content=ft.Column(
                [
                    ft.Column(
                        [
                            title_text,
                            ft.Divider(height=20, color="white"),
                        ],
                        spacing=5,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(
                        expand=True,
                        border_radius=10,
                        padding=10,
                        border=ft.border.all(1, "#CBD5E1"),
                        content=ft.ResponsiveRow(
                            [
                                ft.Column(
                                    scroll=ft.ScrollMode.AUTO,
                                    col={"sm": 12, "md": 4},
                                    controls=[
                                        ft.Row([level_ddawn,groups_ddawn,]),
                                        send_how,
                                        form,
                                        shortcuts_box,
                                        num_of_std,
                                    ],
                                    expand=True,
                                    spacing=10,
                                ),
                                ft.Column(
                                    col={"sm": 12, "md": 8},
                                    controls=[preview_container],
                                    expand=True,
                                    alignment=ft.MainAxisAlignment.START,
                                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                                ),
                                
                            ],
                            expand=True,
                            spacing=10,
                        ),
                    ),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                content=ft.Row(
                                    [
                                        ft.Text("ارسال", size=18, weight=ft.FontWeight.BOLD, color="#F5F5F5"),
                                        ft.Icon(ft.Icons.SEND, size=28, color="#07C06A"),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=10
                                ),
                                height=50,
                                expand=True,
                                bgcolor="#0059DF",
                                on_click=on_send_click,
                            ),
                            ft.ElevatedButton(
                                content=ft.Row(
                                    [
                                        ft.Text("ارسال رسالة التفعيل", size=18, weight=ft.FontWeight.BOLD, color="#F5F5F5"),
                                        ft.Icon(ft.Icons.SEND, size=28, color="#FFD000"),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=10
                                ),
                                height=50,
                                expand=True,
                                bgcolor="#0059DF",
                                on_click=on_send_activation_click,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                        spacing=20,
                    ),
                ],
                expand=True,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                rtl=True,
            ),
        )
  
    return ft.Row(
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Column(
                            [
                                ft.Text(
                                    "ارسال الرسائل",
                                    size=26,
                                    weight=ft.FontWeight.BOLD,
                                    color="#FFFFFF",
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Divider(height=10, color="white"),
                            ],
                            spacing=10,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Container(
                            expand=True,
                            content=ft.Column(
                                controls=[
                                    ft.Container(
                                        content=ft.Row(
                                            [
                                                ft.Text("ارسال رسالة فردية", size=22, weight="bold", color="#ffffff"),
                                                ft.Icon(ft.Icons.SEND_OUTLINED, size=32, color="#ffffff"),
                                            ],
                                            alignment="center",
                                            spacing=12,
                                        ),
                                        bgcolor="#0D6EFD",
                                        border_radius=12,
                                        height=80,
                                        expand=True,
                                        margin=5,
                                        padding=5,
                                        border=ft.border.all(2, "#0044A9"),
                                        ink=True,
                                        on_click=lambda e: update_side_content(send_student_container()),
                                        alignment=ft.alignment.center,
                                    ),
                                    ft.Container(
                                        content=ft.Row(
                                            [
                                                ft.Text("ارسال رسائل جماعية", size=22, weight="bold", color="#ffffff"),
                                                ft.Icon(ft.Icons.GROUP_ROUNDED, size=32, color="#ffffff"),
                                            ],
                                            alignment="center",
                                            spacing=12,
                                        ),
                                        bgcolor="#3B7EFF",
                                        border_radius=12,
                                        height=80,
                                        expand=True,
                                        margin=5,
                                        padding=5,
                                        border=ft.border.all(2, "#0044A9"),
                                        ink=True,
                                        on_click=lambda e: update_side_content(send_group_student_container()),
                                        alignment=ft.alignment.center,
                                    ),
                                ],
                                spacing=15,
                                expand=True,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                        ),
                    ],
                    expand=True,
                    alignment=ft.MainAxisAlignment.START,
                    spacing=20,
                ),
                margin=ft.margin.only(left=10, right=10, top=10, bottom=10),
                padding=10,
                alignment=ft.alignment.center,
                bgcolor="#94BFFF",
                border_radius=10,
                expand=1,
            ),
            side_rec_container,
        ],
        expand=True,
    )