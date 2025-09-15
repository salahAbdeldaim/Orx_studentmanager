# pages/student_page.py
import flet as ft
import sqlite3
import asyncio
from datetime import datetime, date

# استيراد من الوحدات الأخرى في المشروع
from utils.database import students_db_path
from utils.helpers import show_error_dialog, show_success_dialog, search_bar, format_phone_number, get_groups , extract_unique_code
from utils.add_code import init_codes
from components.tables import PaymentTable, AttendanceTable, ExamTable
from utils.date_utils import normalize_date_format


current_month = datetime.now().strftime("%Y-%m")

def student_page(page) :

    side_rec_container = ft.Container(
        margin=ft.margin.only(left=10, right=0, top=10, bottom=10),
        padding=10,
        alignment=ft.alignment.center,
        bgcolor="#3B7EFF",
        border_radius=10,
        expand=4,
        content=ft.Text("اختر عملية من القائمة", size=20, weight="bold")
    )

    def update_side_content(new_content):
        side_rec_container.content = new_content
        side_rec_container.update()

    def section_header(title, count):
        return ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    title,
                    size=22,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                    color="white"
                ),
                ft.Container(
                    content=ft.Text(str(count), size=18, weight=ft.FontWeight.BOLD, color="#1E3A8A"),
                    bgcolor="white",
                    padding=ft.padding.all(8),
                    border_radius=8,
                    border=ft.border.all(1, "#1E3A8A"),
                    margin=ft.margin.only(left=10)
                )
            ]
        )

    def add_student_container():
        std_name = ft.TextField(label="اسم الطالب", text_align=ft.TextAlign.RIGHT)
        father_name = ft.TextField(label="اسم الأب", text_align=ft.TextAlign.RIGHT)
        family_name = ft.TextField(label="اسم العائلة", text_align=ft.TextAlign.RIGHT)
        std_phone = ft.TextField(label="رقم هاتف الطالب", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.RIGHT)
        father_phone = ft.TextField(label="رقم هاتف ولي الأمر", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.RIGHT)    

        std_level = ft.Dropdown(
            label="المرحلة الدراسية",
            hint_text="الصف الأول الإعدادي",
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
        )   

        std_type = ft.Dropdown(
            label="الجنس",
            hint_text="اختر الجنس",
            options=[
                ft.dropdown.Option("ذكر"),
                ft.dropdown.Option("انثى"),
            ],
            expand=True,
        )   

        std_group = ft.Dropdown(
            label="المجموعة",
            hint_text="اختر مجموعة",
            options=get_groups(),
            expand=True,
        )   

        def is_valid_name(name):
            return name and not any(char.isdigit() for char in name)    

        def is_valid_phone(phone):
            if not phone:
                return True
            phone = phone.strip()
            # أضف رمز الدولة إذا لم يكن موجوداً
            if phone.startswith("0"):
                phone = "+20" + phone[1:]
            elif not phone.startswith("+20"):
                phone = "+20" + phone
            return phone.startswith("+20") and len(phone) == 13 and phone[3:].isdigit() 

        def normalize_phone(phone):
            phone = phone.strip()
            if not phone:
                return ""
            if phone.startswith("0"):
                phone = "+20" + phone[1:]
            elif not phone.startswith("+20"):
                phone = "+20" + phone
            return phone    

        def on_save_click(e):
            # تحقق من صحة الأسماء والأرقام
            if not is_valid_name(std_name.value):
                show_error_dialog(e.page, "يرجى إدخال اسم الطالب بشكل صحيح بدون أرقام.")
                return
            if not is_valid_name(father_name.value):
                show_error_dialog(e.page, "يرجى إدخال اسم الأب بشكل صحيح بدون أرقام.")
                return
            if not is_valid_name(family_name.value):
                show_error_dialog(e.page, "يرجى إدخال اسم العائلة بشكل صحيح بدون أرقام.")
                return
            if not is_valid_phone(std_phone.value):
                show_error_dialog(e.page, "يرجى إدخال رقم هاتف الطالب بشكل صحيح (13 رقم ويبدأ بـ +20).")
                return
            if not is_valid_phone(father_phone.value):
                show_error_dialog(e.page, "يرجى إدخال رقم هاتف ولي الأمر بشكل صحيح (13 رقم ويبدأ بـ +20).")
                return
            if not std_level.value:
                show_error_dialog(e.page, "يرجى اختيار المرحلة الدراسية.")
                return
            if not std_group.value:
                show_error_dialog(e.page, "يرجى اختيار المجموعة.")
                return
            if std_type.value not in ["ذكر", "انثى"]:
                show_error_dialog(e.page, "يرجى اختيار الجنس (ذكر أو انثى).")
                return
            # تطبيع أرقام الهواتف
            normalized_std_phone = normalize_phone(std_phone.value)
            normalized_father_phone = normalize_phone(father_phone.value)
            if normalized_std_phone == normalized_father_phone and normalized_std_phone != "":
                show_error_dialog(e.page, "رقم الطالب يجب أن يكون مختلفًا عن رقم ولي الأمر إذا كانا غير فارغين.")
                return
            try:
                conn = sqlite3.connect(students_db_path)
                c = conn.cursor()
                c.execute(
                    """SELECT id FROM students WHERE first_name=? AND father_name=? AND family_name=?""",
                    (std_name.value.strip(), father_name.value.strip(), family_name.value.strip()),
                )
                exists = c.fetchone()
                if exists:
                    show_error_dialog(
                        e.page,
                        "يوجد طالب بهذا الاسم الثلاثي بالفعل! إذا كنت تريد تعديل بياناته، استخدم خيار تعديل طالب.",
                    )
                    conn.close()
                    return
                # إضافة الطالب مع الجنس
                c.execute(
                    """INSERT INTO students (first_name, father_name, family_name, phone, guardian_phone, grade, group_id, gender) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        std_name.value.strip(),
                        father_name.value.strip(),
                        family_name.value.strip(),
                        normalized_std_phone,
                        normalized_father_phone,
                        std_level.value,
                        int(std_group.value),
                        std_type.value
                    )
                )
                conn.commit()
                added_count = init_codes()
                if added_count:
                    show_success_dialog(page, f"تم إضافة أكواد جديدة لعدد {added_count} من الطلاب.")
                show_success_dialog(e.page, "تم حفظ الطالب بنجاح")
                for field in [std_name, father_name, family_name, std_phone, father_phone]:
                    field.value = ""
                    field.update()

            except Exception as ex:
                show_error_dialog(e.page, f"حدث خطأ أثناء حفظ الطالب: {ex}")
            finally:
                conn.close()    
 
        def on_clear_click(e):
            update_side_content(add_student_container())

        return ft.Container(
            border=ft.border.all(2, "#FFFFFF"),
            expand=True,
            padding=20,
            # bgcolor="#3B7EFF",
            border_radius=12,
            alignment=ft.alignment.center,
            content=ft.Column(
                expand=True,
                controls=[
                    ft.Text(
                        "إضافة طالب",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                        color="white",
                    ),
                    ft.Divider(height=20, color="white"),
                    ft.Container(
                        expand=True,
                        content=ft.Column(
                            expand=True,
                            scroll=ft.ScrollMode.AUTO,
                            spacing=15,
                            controls=[
                                std_name,
                                father_name,
                                family_name,
                                std_phone,
                                father_phone,
                                std_level,
                                std_type,
                                std_group,
                            ],
                        ),
                    ),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                content=ft.Row(
                                    [
                                        ft.Text("حفظ", size=18, weight=ft.FontWeight.BOLD, color="#F5F5F5"),
                                        ft.Icon(ft.Icons.SAVE, size=28, color="#07C06A"),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=10
                                ),
                                height=50,
                                expand=True,
                                bgcolor="#0059DF",
                                on_click=on_save_click,
                            ),  

                            ft.ElevatedButton(
                                content=ft.Row(
                                    [
                                        ft.Text("مسح", size=18, weight=ft.FontWeight.BOLD, color="#F5F5F5"),
                                        ft.Icon(ft.Icons.CLEAR, size=28, color="#FB4E5F"),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=10
                                ),
                                height=50,
                                expand=True,
                                bgcolor="#0059DF",
                                on_click=on_clear_click,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                        spacing=20,
                    )   

                ],
                spacing=20,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                rtl=True,
            ),
        )
    
    def edit_student_container(e=None, name=None, std_id=None, student_phone=None, parent_phone=None, grade=None, group=None):
        std_name = ft.TextField(label="اسم الطالب", text_align=ft.TextAlign.RIGHT)
        father_name = ft.TextField(label="اسم الأب", text_align=ft.TextAlign.RIGHT)
        family_name = ft.TextField(label="اسم العائلة", text_align=ft.TextAlign.RIGHT)
        std_phone = ft.TextField(label="رقم هاتف الطالب", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.RIGHT)
        father_phone = ft.TextField(label="رقم هاتف ولي الأمر", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.RIGHT)
        std_level = ft.Dropdown(
            label="المرحلة الدراسية",
            hint_text="الصف الأول الإعدادي",
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
            expand=True
        )
        std_type = ft.Dropdown(
            label="الجنس",
            hint_text="اختر الجنس",
            options=[
                ft.dropdown.Option("ذكر"),
                ft.dropdown.Option("انثى"),
            ],
            expand=True,
            value=None
        )
        std_group = ft.Dropdown(
            label="المجموعة",
            hint_text="اختر مجموعة",
            options=get_groups(),
            expand=True
        )   

        # ----------------------------
        # البحث عن الطالب
        def search_student(search_term):
            conn = sqlite3.connect(students_db_path)
            c = conn.cursor()
            
            # تنظيف الكود من الزوائد إذا كان البحث بالكود
            if search_term.strip().isdigit():
                search_term = extract_unique_code(search_term)
                c.execute('''SELECT id, first_name, father_name, family_name, phone, guardian_phone, grade, group_id, gender 
                         FROM students 
                         WHERE code = ?''', (search_term,))
            else:
                c.execute('''SELECT id, first_name, father_name, family_name, phone, guardian_phone, grade, group_id, gender 
                         FROM students 
                         WHERE first_name || ' ' || father_name || ' ' || family_name = ?''', (search_term.strip(),))
            
            result = c.fetchone()
            conn.close()
            return result   

        # ----------------------------
        # تحميل بيانات الطالب لو اتبعت name
        # استخدم dict لتخزين std_id بشكل قابل للتغيير
        std_id_holder = {"id": std_id}
        if name:
            conn = sqlite3.connect(students_db_path)
            c = conn.cursor()
            c.execute('''SELECT id, first_name, father_name, family_name, phone, guardian_phone, grade, group_id, gender FROM students WHERE first_name || ' ' || father_name || ' ' || family_name = ?''', (name.strip(),))
            result = c.fetchone()
            conn.close()
            if result:
                std_id_holder["id"] = result[0]
                std_name.value = result[1]
                father_name.value = result[2]
                family_name.value = result[3]
                std_phone.value = result[4]
                father_phone.value = result[5]
                std_level.value = result[6]
                std_group.value = str(result[7])
                std_type.value = result[8] if result[8] in ["ذكر", "انثى"] else None
            else:
                show_error_dialog(e.page if e else None, "الطالب غير موجود")
        # ----------------------------
        # البحث من search bar
        def on_search_submit(e):
            entered_name = e.control.value.strip()
            # إذا كان البحث عبارة عن كود رقمي، فلتره أولاً
            if entered_name.isdigit():
                from utils.helpers import extract_unique_code
                entered_name = extract_unique_code(entered_name)
            result = search_student(entered_name)
            if result:
                std_id_holder["id"] = result[0]
                std_name.value = result[1]
                father_name.value = result[2]
                family_name.value = result[3]
                std_phone.value = result[4]
                father_phone.value = result[5]
                std_level.value = result[6]
                std_group.value = str(result[7])
                std_type.value = result[8] if result[8] in ["ذكر", "انثى"] else None
                std_name.update(); father_name.update(); family_name.update()
                std_phone.update(); father_phone.update()
                std_level.update(); std_group.update(); std_type.update()
            else:
                show_error_dialog(e.page, "الطالب غير موجود")   

        def is_valid_name(name):
            return name and not any(char.isdigit() for char in name)    

        def is_valid_phone(phone):
            phone = format_phone_number(phone)
            return phone.startswith('+20') and len(phone) == 13 

        def on_update_click(e):
            phone_raw = std_phone.value.strip()
            guardian_phone_raw = father_phone.value.strip()
            phone = format_phone_number(phone_raw) if phone_raw else ''
            guardian_phone = format_phone_number(guardian_phone_raw) if guardian_phone_raw else ''  

            if not (is_valid_name(std_name.value) and is_valid_name(father_name.value) and is_valid_name(family_name.value)
                    and std_level.value and std_group.value and std_type.value in ["ذكر", "انثى"]):
                show_error_dialog(e.page, "يرجى ملء جميع الحقول بشكل صحيح وعدم استخدام أرقام في الاسم واختيار الجنس")
                return  

            # تحقق من صحة الأرقام فقط إذا كانت موجودة
            if phone:
                if not is_valid_phone(phone):
                    show_error_dialog(e.page, "رقم الطالب يجب أن يكون بصيغة دولية صحيحة")
                    return
            if guardian_phone:
                if not is_valid_phone(guardian_phone):
                    show_error_dialog(e.page, "رقم ولي الأمر يجب أن يكون بصيغة دولية صحيحة")
                    return
            # تحقق من عدم تساوي الرقمين إذا كانا موجودين معًا
            if phone and guardian_phone and phone == guardian_phone:
                show_error_dialog(e.page, "رقم الطالب يجب أن يكون مختلفًا عن رقم ولي الأمر")
                return  

            if not std_id_holder["id"]:
                show_error_dialog(e.page, "لا يمكن تحديث الطالب: المعرف غير متوفر")
                return  

            try:
                conn = sqlite3.connect(students_db_path)
                c = conn.cursor()
                c.execute('''UPDATE students 
                             SET first_name=?, father_name=?, family_name=?, phone=?, guardian_phone=?, grade=?, group_id=?, gender=? 
                             WHERE id = ?''',
                    (std_name.value.strip(), father_name.value.strip(), family_name.value.strip(),
                     phone, guardian_phone, std_level.value, int(std_group.value),
                     std_type.value,
                     std_id_holder["id"]))
                conn.commit()
                show_success_dialog(e.page, "تم تحديث بيانات الطالب بنجاح")
            except Exception as ex:
                show_error_dialog(e.page, f"خطأ: {ex}")
            finally:
                conn.close()    

        def on_delete_click(e):
            try:
                conn = sqlite3.connect(students_db_path)
                c = conn.cursor()
                c.execute('''DELETE FROM students 
                             WHERE first_name || ' ' || father_name || ' ' || family_name = ?''',
                          (std_name.value.strip() + ' ' + father_name.value.strip() + ' ' + family_name.value.strip(),))
                conn.commit()
                show_success_dialog(e.page, "تم حذف الطالب")
                std_name.value = ""; father_name.value = ""; family_name.value = ""
                std_phone.value = ""; father_phone.value = ""
                std_level.value = None; std_group.value = None
                std_name.update(); father_name.update(); family_name.update()
                std_phone.update(); father_phone.update()
                std_level.update(); std_group.update()
            except Exception as ex:
                show_error_dialog(e.page, f"خطأ: {ex}")
            finally:
                conn.close()    

        return ft.Container(
            border=ft.border.all(2, "#FFFFFF"),
            expand=True,
            padding=20,
            # bgcolor="#0D6EFD",
            border_radius=12,
            alignment=ft.alignment.center,
            content=ft.Column(
                [
                    # 1) الهيدر
                    ft.Column(
                        [
                            ft.Text(
                                "تعديل بيانات طالب",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.CENTER,
                                color="white"
                            ),
                            ft.Divider(height=20, color="white"),
                            search_bar("ابحث بالاسم أو الكود...",on_submit=on_search_submit,),
                        ],
                        spacing=5,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),  

                    # 2) الكونتنت (هو اللي يعمل scroll)
                    ft.Container(
                        expand=True,
                        content=ft.Column(
                            [
                                std_name,
                                father_name,
                                family_name,
                                std_phone,
                                father_phone,
                                std_level,
                                std_type,
                                std_group,
                            ],
                            spacing=10,
                            scroll=ft.ScrollMode.AUTO,
                            rtl=True,
                        ),
                    ),  

                    # 3) الفوتر (الأزرار)   

                    ft.Row(
                        [
                            ft.ElevatedButton(
                                content=ft.Row(
                                    [
                                        ft.Text("تحديث", size=18, weight=ft.FontWeight.BOLD, color="#F5F5F5"),
                                        ft.Icon(ft.Icons.UPDATE, size=28, color="#07C06A"),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=10
                                ),
                                height=50,
                                expand=True,
                                bgcolor="#0059DF",
                                on_click=on_update_click,
                            ),  

                            ft.ElevatedButton(
                                content=ft.Row(
                                    [
                                        ft.Text("حذف", size=18, weight=ft.FontWeight.BOLD, color="#F5F5F5"),
                                        ft.Icon(ft.Icons.DELETE, size=28, color="#FB4E5F"),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=10
                                ),
                                height=50,
                                expand=True,
                                bgcolor="#0059DF",
                                on_click=on_delete_click,
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
 
    def show_student_container(page):
        # تحديث الجدول عند فتح الصفحة مباشرة
        filter_level = {"value": None}
        filter_search = {"value": ""}

        def fetch_students():
            with sqlite3.connect(students_db_path) as conn:
                c = conn.cursor()
                query = '''SELECT s.id, s.code, s.first_name, s.father_name, s.family_name, 
                                  s.phone, s.guardian_phone, s.grade, g.name as group_name
                           FROM students s 
                           LEFT JOIN groups g ON s.group_id = g.id'''
                params = []
                where = []      

                if filter_level["value"]:
                    where.append("s.grade = ?")
                    params.append(filter_level["value"])        

                if filter_search["value"]:
                    search_val = filter_search["value"].strip()

                    # ✅ لو المدخل كله أرقام (باركود)
                    if search_val.isdigit():
                        # استخدم دالة extract_unique_code
                        filtered_code = extract_unique_code(search_val)
                        if filtered_code:
                            where.append("CAST(s.code AS TEXT) LIKE ?")
                            params.append(f"%{filtered_code}%")
                        else:
                            # إذا لم يرجع شيء من الدالة، استخدم آخر 4 أرقام كاحتياط
                            search_val = search_val[-4:]
                            where.append("CAST(s.code AS TEXT) LIKE ?")
                            params.append(f"%{search_val}%")
                    else:
                        # 🔍 بحث بالاسم أو رقم الهاتف إلخ
                        val = f"%{search_val}%"
                        where.append(
                            "(s.first_name LIKE ? OR s.father_name LIKE ? OR s.family_name LIKE ? OR CAST(s.code AS TEXT) LIKE ?)"
                        )
                        params += [val, val, val, val]

                if where:
                    query += " WHERE " + " AND ".join(where)        

                query += " ORDER BY s.first_name, s.father_name, s.family_name"
                c.execute(query, params)
                students = c.fetchall()
                result = []     

                # الشهر الحالي بالتنسيق الرقمي YYYY-MM
                current_month_numeric = datetime.now().strftime('%Y-%m')

                for s in students:
                    student_id, code, first_name, father_name, family_name, phone, guardian_phone, grade, group_name = s
                    full_name = f"{first_name} {father_name} {family_name}"     

                    # حالة الدفع
                    c.execute(
                        'SELECT status FROM payments WHERE student_id=? AND month=? LIMIT 1',
                        (student_id, current_month_numeric)
                    )
                    payment_status_row = c.fetchone()
                    payment_status = payment_status_row[0] if payment_status_row else "لم يدفع"     

                    # عدد الاختبارات
                    c.execute('SELECT COUNT(*) FROM exams WHERE student_id=?', (student_id,))
                    tests_count = c.fetchone()[0]       

                    # الحضور
                    c.execute('SELECT group_id FROM students WHERE id=?', (student_id,))
                    group_id_row = c.fetchone()
                    group_id = group_id_row[0] if group_id_row else None        

                    if group_id:
                        c.execute(
                            'SELECT DISTINCT attendance_date FROM attendance a JOIN students s ON a.student_id = s.id WHERE s.group_id=?',
                            (group_id,)
                        )
                        group_dates = [row[0] for row in c.fetchall()]
                        total_att = len(group_dates)        

                        if group_dates:
                            c.execute(
                                f'SELECT COUNT(*) FROM attendance WHERE student_id=? AND status="حاضر" AND attendance_date IN ({",".join(["?"]*len(group_dates))})',
                                [student_id] + group_dates
                            )
                            attended = c.fetchone()[0]
                        else:
                            attended = 0
                    else:
                        total_att = 0
                        attended = 0        

                    attendance = f"{attended}/{total_att}" if total_att > 0 else "-"        

                    result.append({
                        "id": student_id,
                        "code": code,
                        "name": full_name,
                        "group": group_name or "-",
                        "student_phone": phone,
                        "parent_phone": guardian_phone,
                        "grade": grade,
                        "payment_status": payment_status,
                        "tests_count": tests_count,
                        "attendance": attendance,
                    })
                return result       

        def refresh_table():
            students_data = fetch_students()

            if not students_data:
                student_table.rows = [
                    ft.DataRow(
                        cells=[ft.DataCell(ft.Text('لا يوجد طلاب لعرضهم', text_align='center', color='red', weight='bold'))]
                        + [ft.DataCell(ft.Text(''))] * 9
                    )
                ]
            else:
                student_table.rows = [
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(idx + 1), text_align="center", color="#1E3A8A", weight="bold")),
                            ft.DataCell(ft.Text(str(s["code"]), text_align="center", color="#000000", weight="bold")),
                            ft.DataCell(
                                ft.TextButton(
                                    text=s["name"],
                                    style=ft.ButtonStyle(color="#000000"),
                                    on_click=lambda e, student=s: on_click(student)
                                )
                            ),
                            ft.DataCell(ft.Text(s["group"], text_align="center", color="#000000", weight="bold")),
                            ft.DataCell(
                                ft.TextButton(
                                    text=s["student_phone"] if s["student_phone"] else "-",
                                    url=f"https://wa.me/{s['student_phone'].replace('+', '')}" if s["student_phone"] else None,
                                    style=ft.ButtonStyle(color="#25D366"),
                                    tooltip="تواصل واتساب مع الطالب",
                                    disabled=not s["student_phone"]
                                )
                            ),
                            ft.DataCell(
                                ft.TextButton(
                                    text=s["parent_phone"] if s["parent_phone"] else "-",
                                    url=f"https://wa.me/{s['parent_phone'].replace('+', '')}" if s["parent_phone"] else None,
                                    style=ft.ButtonStyle(color="#0D6EFD"),
                                    tooltip="تواصل واتساب مع ولي الأمر",
                                    disabled=not s["parent_phone"]
                                )
                            ),
                            ft.DataCell(ft.Text(s["grade"] if s["grade"] else "-", text_align="center", color="#000000", weight="bold")),
                            ft.DataCell(
                                ft.Text(
                                    s["payment_status"],
                                    color="green" if s["payment_status"] == "دفع" else "red",
                                    text_align="center",
                                    weight="bold"
                                )
                            ),
                            ft.DataCell(ft.Text(str(s["tests_count"]), text_align="center", color="#000000", weight="bold")),
                            ft.DataCell(ft.Text(s["attendance"], text_align="center", color="#000000", weight="bold")),
                        ]
                    )
                    for idx, s in enumerate(students_data)
                ]
            page.update()

        def on_click(student):
            update_side_content(show_student_details(student["name"]))

        def on_search_submit(e=None):
            filter_search["value"] = e.control.value.strip() if e and e.control else ""
            refresh_table()

        def on_level_change(e):
            filter_level["value"] = std_level.value
            refresh_table()

        student_table = ft.DataTable(
            expand=True,
            column_spacing=30,
            data_row_min_height=50,
            heading_row_color="#1E3A8A",
            border=ft.border.all(1, "#1E3A8A"),
            divider_thickness=1,
            columns=[
                ft.DataColumn(ft.Text("#", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("كود الطالب", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("الاسم الثلاثي", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("المجموعة", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("هاتف الطالب", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("هاتف ولي الأمر", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("الصف", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("حالة الدفع", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("عدد الاختبارات", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("الحضور", weight="bold", color="white", text_align="center")),
            ],
            rows=[],
        )

        std_level = ft.Dropdown(
            label="المرحلة الدراسية",
            hint_text="فلترة حسب المرحلة",
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
            on_change=on_level_change
        )

        refresh_table()

        return ft.Container(
            border=ft.border.all(2, "#FFFFFF"),
            expand=True,
            padding=20,
            border_radius=12,
            alignment=ft.alignment.center,
            content=ft.Column(
                expand=True,
                controls=[
                    ft.Text(
                        "عرض الطلاب",
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
                                search_bar("ابحث بالاسم أو الكود...", on_submit=on_search_submit),
                                std_level
                            ]
                        )
                    ),
                    ft.Container(
                        expand=True,
                        bgcolor="#F4F4F4",
                        border_radius=10,
                        padding=10,
                        border=ft.border.all(1, "#CBD5E1"),
                        content=ft.Column(
                            expand=True,
                            scroll=ft.ScrollMode.ADAPTIVE,
                            controls=[
                                ft.Row(
                                    controls=[student_table],
                                    scroll=ft.ScrollMode.ADAPTIVE,
                                    expand=True,
                                )
                            ]
                        )
                    )
                ],
                spacing=25,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                rtl=True
            )
        )
    
    def show_student_details(name):
        def on_edit_click(e):
            container = edit_student_container(name=name)
            update_side_content(container)  

        def on_delete_click(e):
            def confirm_delete(ev):
                try:
                    with sqlite3.connect(students_db_path) as conn:
                        c = conn.cursor()
                        c.execute("DELETE FROM attendance WHERE student_id=?", (student_data["id"],))
                        c.execute("DELETE FROM exams WHERE student_id=?", (student_data["id"],))
                        c.execute("DELETE FROM payments WHERE student_id=?", (student_data["id"],))
                        c.execute("DELETE FROM students WHERE id=?", (student_data["id"],))
                        conn.commit()
                    show_success_dialog(page, "تم حذف الطالب بنجاح!")
                    update_side_content(ft.Text("اختر عملية من القائمة", size=20, weight="bold"))
                    page.close(dialog)
                    page.update()
                except Exception as ex:
                    show_error_dialog(page, f"حدث خطأ أثناء الحذف: {ex}")
                    page.close(dialog)
                    page.update()   

            def cancel_delete(ev):
                page.close(dialog)
                page.update()   

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("تأكيد الحذف", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.RIGHT, color=ft.Colors.RED_700),
                content=ft.Text(f"هل أنت متأكد أنك تريد حذف الطالب '{student_data['name']}' نهائياً؟", text_align=ft.TextAlign.RIGHT),
                actions=[
                    ft.TextButton("إلغاء", on_click=cancel_delete, style=ft.ButtonStyle(color=ft.Colors.BLUE_700)),
                    ft.ElevatedButton("حذف", on_click=confirm_delete, style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE)),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
                content_padding=ft.padding.all(20),
                shape=ft.RoundedRectangleBorder(radius=10),
                bgcolor=ft.Colors.WHITE,
            )
            page.open(dialog)
            page.update()   

        def on_update_click(e):
            update_side_content(show_student_details(name))
            show_success_dialog(page, "تم تحديث البيانات بنجاح")    

        student_data = None
        with sqlite3.connect(students_db_path) as conn:
            c = conn.cursor()
            name_parts = name.strip().split()
            if len(name_parts) >= 3:
                c.execute('''SELECT s.id, s.code, s.first_name, s.father_name, s.family_name, s.phone, s.guardian_phone, s.grade, s.gender, g.name as group_name
                             FROM students s LEFT JOIN groups g ON s.group_id = g.id
                             WHERE s.first_name=? AND s.father_name=? AND s.family_name=?''',
                          (name_parts[0], name_parts[1], ' '.join(name_parts[2:])))
            else:
                like_val = f"%{name.strip()}%"
                c.execute('''SELECT s.id, s.code, s.first_name, s.father_name, s.family_name, s.phone, s.guardian_phone, s.grade, s.gender, g.name as group_name
                             FROM students s LEFT JOIN groups g ON s.group_id = g.id
                             WHERE s.first_name || ' ' || s.father_name || ' ' || s.family_name LIKE ?''', (like_val,))
            row = c.fetchone()
            if row:
                student_data = {
                    "id": row[0],
                    "code": row[1],
                    "name": f"{row[2]} {row[3]} {row[4]}",
                    "student_phone": row[5],
                    "parent_phone": row[6],
                    "grade": row[7],
                    "gender": row[8] if row[8] in ["ذكر", "انثى"] else "-",
                    "group": row[9] or "-",
                }   

        if not student_data:
            show_error_dialog(page, "لم يتم العثور على طالب بهذا الاسم!")
            page.update()
            return ft.Container(
                expand=True,
                alignment=ft.alignment.center,
                content=ft.Text("لا يوجد بيانات لهذا الطالب", size=20, color="red", text_align=ft.TextAlign.CENTER)
            )   

        def on_edit_click(e):
            container = edit_student_container(
                name=student_data["name"],
                std_id=student_data["id"],
                student_phone=student_data["student_phone"],
                parent_phone=student_data["parent_phone"],
                grade=student_data["grade"],
                group=student_data["group"]
            )
            update_side_content(container)  

        student_table = ft.DataTable(
            expand=True,
            column_spacing=30,
            data_row_min_height=50,
            heading_row_color="#1E3A8A",
            border=ft.border.all(1, "#1E3A8A"),
            divider_thickness=1,
            columns=[
                ft.DataColumn(ft.Text("الكود", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("الاسم الثلاثي", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("هاتف الطالب", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("هاتف ولي الأمر", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("المجموعة", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("الصف", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("النوع", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("تعديل", weight="bold", color="white", text_align="center")),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(student_data["code"]), text_align="center", color="#000000", weight="bold")),
                        ft.DataCell(ft.Text(student_data["name"], text_align="center", color="#000000", weight="bold")),
                        ft.DataCell(
                            ft.TextButton(
                                text=student_data["student_phone"] if student_data["student_phone"] else "-",
                                url=f"https://wa.me/{student_data['student_phone'].replace('+', '')}" if student_data["student_phone"] else None,
                                style=ft.ButtonStyle(color="#25D366"),
                                tooltip="تواصل واتساب مع الطالب",
                                disabled=not student_data["student_phone"]
                            )
                        ),
                        ft.DataCell(
                            ft.TextButton(
                                text=student_data["parent_phone"] if student_data["parent_phone"] else "-",
                                url=f"https://wa.me/{student_data['parent_phone'].replace('+', '')}" if student_data["parent_phone"] else None,
                                style=ft.ButtonStyle(color="#0D6EFD"),
                                tooltip="تواصل واتساب مع ولي الأمر",
                                disabled=not student_data["parent_phone"]
                            )
                        ),
                        ft.DataCell(ft.Text(student_data.get("group", "-"), text_align="center", color="#000000", weight="bold")),
                        ft.DataCell(ft.Text(student_data["grade"] if student_data["grade"] else "-", text_align="center", color="#000000", weight="bold")),
                        ft.DataCell(ft.Text(student_data["gender"], text_align="center", color="#000000", weight="bold")),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.Icons.EDIT,
                                icon_color="#FFC107",
                                tooltip="تعديل بيانات الطالب",
                                on_click=on_edit_click
                            )
                        ),
                    ]
                )
            ],
        )   

        def payment_table():
            arabic_months = [
                "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
            ]
            students_payment = []
            with sqlite3.connect(students_db_path) as conn:
                c = conn.cursor()
                c.execute('SELECT month, status, IFNULL(payment_date, "-") FROM payments WHERE student_id=? ORDER BY month DESC',
                          (student_data["id"],))
                for row in c.fetchall():
                    month_numeric = row[0]  # YYYY-MM
                    try:
                        month_idx = int(month_numeric.split('-')[1]) - 1
                        month_ar = arabic_months[month_idx]
                    except (ValueError, IndexError):
                        month_ar = month_numeric
                    students_payment.append({
                        "month": month_ar,
                        "status": row[1],
                        "date": row[2],
                        "numeric_month": row[0]
                    })  

            table = ft.DataTable(
                expand=True,
                column_spacing=30,
                data_row_min_height=50,
                heading_row_color=ft.Colors.BLUE_900,
                border=ft.border.all(1, ft.Colors.BLUE_900),
                divider_thickness=1,
                columns=[
                    ft.DataColumn(ft.Text("الشهر", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER)),
                    ft.DataColumn(ft.Text("الحالة", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER)),
                    ft.DataColumn(ft.Text("التاريخ", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER)),
                ],
                rows=[],
            )   

            def open_edit_dialog(payment=None):
                months = [
                    "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
                ]
                current_year = datetime.now().strftime('%Y')
                current_month_idx = datetime.now().month - 1
                default_month = months[current_month_idx] if payment is None else payment["month"]
                month_field = ft.Dropdown(
                    label="الشهر",
                    value=default_month,
                    expand=True,
                    text_align=ft.TextAlign.RIGHT,
                    options=[ft.dropdown.Option(m) for m in months],
                )
                status_field = ft.Dropdown(
                    label="حالة الدفع",
                    value="دفع" if payment is None else payment["status"],
                    expand=True,
                    text_align=ft.TextAlign.RIGHT,
                    options=[
                        ft.dropdown.Option("دفع"),
                        ft.dropdown.Option("لم يدفع"),
                    ],
                )
                date_format = "%d-%m-%Y"
                today_str = datetime.now().strftime(date_format)
                date_val = today_str if payment is None else (payment["date"] if payment["date"] and payment["date"] != "-" else today_str)
                date_field = ft.TextField(
                    label="تاريخ الدفع",
                    value=date_val,
                    read_only=True,
                    expand=True,
                    text_align=ft.TextAlign.RIGHT,
                )   

                def on_date_change(e):
                    date_field.value = e.control.value.strftime(date_format)
                    page.update()   

                date_picker = ft.DatePicker(
                    first_date=date(2020, 1, 1),
                    last_date=date(2035, 12, 31),
                    on_change=on_date_change,
                )
                if date_picker not in page.overlay:
                    page.overlay.append(date_picker)    

                def pick_date(e):
                    date_picker.pick_date() 

                date_field.suffix = ft.IconButton(
                    icon=ft.Icons.CALENDAR_MONTH,
                    on_click=pick_date,
                )   

                def save_changes(e):
                    if not month_field.value:
                        show_error_dialog(page, "يرجى اختيار شهر")
                        return
                    month_idx = months.index(month_field.value) + 1
                    new_month_numeric = f"{current_year}-{month_idx:02d}"
                    new_status = status_field.value
                    new_date = date_field.value if new_status == "دفع" else "-"
                    if new_status == "دفع" and (not new_date or new_date == "-"):
                        new_date = today_str    

                    with sqlite3.connect(students_db_path) as conn:
                        c = conn.cursor()
                        if payment is None or new_month_numeric != payment["numeric_month"]:
                            c.execute('SELECT COUNT(*) FROM payments WHERE student_id=? AND month=?',
                                      (student_data["id"], new_month_numeric))
                            if c.fetchone()[0] > 0:
                                show_error_dialog(page, f"الشهر {month_field.value} مسجل بالفعل لهذا الطالب.")
                                return
                        if payment is None:
                            c.execute('INSERT INTO payments (student_id, month, status, payment_date) VALUES (?, ?, ?, ?)',
                                      (student_data["id"], new_month_numeric, new_status, new_date))
                        else:
                            c.execute('UPDATE payments SET month=?, status=?, payment_date=? WHERE student_id=? AND month=?',
                                      (new_month_numeric, new_status, new_date, student_data["id"], payment["numeric_month"]))
                        conn.commit()   

                    on_update_click(e)
                    page.close(dialog)
                    page.update()   

                def cancel_dialog(e):
                    page.close(dialog)
                    page.update()   

                dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("إضافة/تعديل بيانات الدفع", 
                                size=20, 
                                weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.CENTER,
                                color="#1E3A8A"),
                    content=ft.Container(
                        content=ft.Column(
                            [month_field, status_field, date_field],
                            tight=True,
                            spacing=20,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                        padding=20
                    ),
                    actions=[
                        ft.TextButton(
                            "إلغاء",
                            on_click=cancel_dialog,
                            style=ft.ButtonStyle(
                                color="#D32F2F",
                                bgcolor={"hovered": "#FFEBEE"},
                            )
                        ),
                        ft.ElevatedButton(
                            "حفظ",
                            on_click=save_changes,
                            style=ft.ButtonStyle(
                                bgcolor={"": "#0059DF", "hovered": "#1565C0"},
                                color="white",
                            )
                        ),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                    shape=ft.RoundedRectangleBorder(radius=10),
                    bgcolor="white"
                )
                page.open(dialog)
                page.update()   

            def add_new_payment(e):
                open_edit_dialog()  

            def rebuild_table():
                table.rows = [
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(p["month"], text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)),
                            ft.DataCell(
                                ft.Text(
                                    p["status"],
                                    text_align=ft.TextAlign.CENTER,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.GREEN_700 if p["status"] == "دفع" else ft.Colors.RED_700,
                                )
                            ),
                            ft.DataCell(ft.Text(p["date"], text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)),
                        ],
                        on_select_changed=lambda e, p=p: open_edit_dialog(p),
                    )
                    for p in students_payment
                ]
                page.update()   

            rebuild_table()
            return ft.Column(
                [
                    ft.Container(
                        content=ft.ElevatedButton(
                            content=ft.Row([
                                ft.Text("إضافة دفع جديد", size=16, weight=ft.FontWeight.BOLD, color="white"),
                                ft.Icon(ft.Icons.ADD, size=20, color="white"),
                            ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                            bgcolor="#0059DF",
                            on_click=add_new_payment,
                            height=40,
                            expand=True,
                        ),
                        alignment=ft.alignment.center,
                        margin=ft.margin.only(bottom=10),
                        width=table.width,  # Match the table's width
                    ),
                    table
                ],
                spacing=0,  # No spacing between button and table
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
    
        def attendance_table():
            arabic_days = {"Saturday": "السبت", "Sunday": "الأحد", "Monday": "الإثنين", "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء", "Thursday": "الخميس", "Friday": "الجمعة"}
            students_attendance = []
            date_format = "%d-%m-%Y"
            with sqlite3.connect(students_db_path) as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT attendance_date, status, COALESCE(day, '-') as day 
                    FROM attendance 
                    WHERE student_id=? 
                    ORDER BY attendance_date DESC
                ''', (student_data["id"],))
                for row in c.fetchall():
                    att_date_str = row[0]
                    day_ar = row[2]
                    try:
                        dt = datetime.strptime(att_date_str, date_format)
                        correct_day_ar = arabic_days.get(dt.strftime("%A"), "-")
                        if day_ar != correct_day_ar:
                            day_ar = correct_day_ar
                    except ValueError:
                        day_ar = "-"
                    students_attendance.append({"date": att_date_str, "day": day_ar, "status": row[1]}) 

            table = ft.DataTable(
                expand=True, column_spacing=30, data_row_min_height=50,
                heading_row_color=ft.Colors.BLUE_900, border=ft.border.all(1, ft.Colors.BLUE_900),
                columns=[
                    ft.DataColumn(ft.Text("اليوم", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER)),
                    ft.DataColumn(ft.Text("الحالة", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER)),
                    ft.DataColumn(ft.Text("التاريخ", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER)),
                ],
                rows=[],
            )   

            def open_edit_dialog(att):
                today_str = datetime.now().strftime(date_format)
                date_val = att["date"] if att["date"] and att["date"] != "-" else today_str
                def get_day_ar(date_str):
                    try:
                        dt = datetime.strptime(date_str, date_format)
                        return arabic_days.get(dt.strftime("%A"), "-")
                    except Exception:
                        return "-"
                date_field = ft.TextField(label="تاريخ الحصة", value=date_val, read_only=True, expand=True, text_align=ft.TextAlign.RIGHT)
                day_field = ft.Text(value=get_day_ar(date_val), size=16, weight=ft.FontWeight.BOLD)
                status_field = ft.Dropdown(
                    label="الحالة", value=att["status"], expand=True, text_align=ft.TextAlign.RIGHT,
                    options=[ft.dropdown.Option("حاضر"), ft.dropdown.Option("غائب"), ft.dropdown.Option("معتذر")]
                )
                def on_date_change(e):
                    new_date_str = e.control.value.strftime(date_format)
                    date_field.value = new_date_str
                    day_field.value = get_day_ar(new_date_str)
                    page.update()
                date_picker = ft.DatePicker(first_date=date(2020, 1, 1), last_date=date(2035, 12, 31), on_change=on_date_change)
                page.overlay.append(date_picker)
                page.update()
                def pick_date(e):
                    date_picker.open = True
                    page.update()
                date_field.suffix = ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, on_click=pick_date)
                def save_changes(e):
                    try:
                        datetime.strptime(date_field.value, date_format)
                        old_date = att["date"]
                        new_date = date_field.value
                        new_status = status_field.value
                        new_day = get_day_ar(new_date)
                    except ValueError:
                        show_error_dialog(page, "صيغة التاريخ غير صحيحة. يجب أن تكون dd-mm-yyyy")
                        return
                    with sqlite3.connect(students_db_path) as conn:
                        c = conn.cursor()
                        if new_date != old_date:
                            c.execute('SELECT COUNT(*) FROM attendance WHERE student_id=? AND attendance_date=?', (student_data["id"], new_date))
                            if c.fetchone()[0] > 0:
                                show_error_dialog(page, f"التاريخ {new_date} مسجل بالفعل لهذا الطالب.")
                                return
                        c.execute('''UPDATE attendance SET attendance_date=?, status=?, day=? WHERE student_id=? AND attendance_date=?''',
                                  (new_date, new_status, new_day, student_data["id"], old_date))
                        conn.commit()
                    on_update_click(e)
                    page.close(dialog)
                    page.update()
                def cancel_dialog(e): page.close(dialog); page.update()
                dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text(
                        "تعديل بيانات الحضور",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                        color="#1E3A8A",
                    ),
                    content=ft.Container(
                        content=ft.Column(
                            [
                                date_field,
                                ft.Row(
                                    [ft.Text("اليوم:", weight=ft.FontWeight.BOLD), day_field],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                status_field,
                            ],
                            tight=True,
                            spacing=20,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=20,
                        height=300,   # 👈 ارتفاع ثابت
                        width=400,    # 👈 عرض ثابت (اختياري)
                        alignment=ft.alignment.center,  # يخلي المحتوى في النص عموديًا
                    ),
                    actions=[
                        ft.TextButton(
                            "إلغاء",
                            on_click=cancel_dialog,
                            style=ft.ButtonStyle(
                                color="#D32F2F",
                                bgcolor={"hovered": "#FFEBEE"},
                            ),
                        ),
                        ft.ElevatedButton(
                            "حفظ",
                            on_click=save_changes,
                            style=ft.ButtonStyle(
                                bgcolor={"": "#0059DF", "hovered": "#1565C0"},
                                color="white",
                            ),
                        ),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                    shape=ft.RoundedRectangleBorder(radius=10),
                    bgcolor="white",
                )               

                page.open(dialog)
                page.update()


            def get_current_day_ar(date_str):
                try:
                    dt = datetime.strptime(date_str, date_format)
                    return arabic_days.get(dt.strftime("%A"), "-")
                except ValueError:
                    return "-"  

            def rebuild_table():
                table.rows = [
                    ft.DataRow(
                        cells=[
                            ft.DataCell(
                                ft.Container(
                                    content=ft.Text(
                                        att["day"],
                                        text_align=ft.TextAlign.CENTER,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLUE_900
                                    ),
                                    padding=5,
                                    border_radius=5,
                                    bgcolor="#E3F2FD" if att["day"] == get_current_day_ar(att["date"]) else "#FFEBEE"
                                )
                            ),
                            ft.DataCell(ft.Text(att["status"], text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD,
                                                color=(ft.Colors.GREEN_700 if att["status"] == "حاضر" else ft.Colors.RED_700 if att["status"] == "غائب" else ft.Colors.AMBER_700))),
                            ft.DataCell(
                                ft.Container(
                                    content=ft.Text(att["date"], text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD),
                                    padding=5,
                                    border_radius=5,
                                    bgcolor="#E8F5E9" if att["date"] == datetime.now().strftime(date_format) else None
                                )
                            ),
                        ],
                        on_select_changed=lambda e, att=att: open_edit_dialog(att),
                    )
                    for att in students_attendance
                ]
                page.update()
            rebuild_table()
            return table    

        def exams_table():
            students_exams = []
            with sqlite3.connect(students_db_path) as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT e.id, s.code, e.total_score, e.student_score, e.exam_date
                    FROM exams e
                    JOIN students s ON e.student_id = s.id
                    WHERE e.student_id=?
                    ORDER BY e.exam_date DESC
                ''', (student_data["id"],))
                for row in c.fetchall():
                    students_exams.append({"id": row[0], "code": row[1], "total": row[2], "score": row[3], "date": row[4]})


            exams_table_widget = ft.DataTable(
                expand=True,
                column_spacing=30,
                data_row_min_height=50,
                heading_row_color=ft.Colors.BLUE_900,
                border=ft.border.all(1, ft.Colors.BLUE_900),
                columns=[
                    ft.DataColumn(ft.Text("#", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER)),
                    ft.DataColumn(ft.Text("الكود", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER)),
                    ft.DataColumn(ft.Text("النهائية", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER)),
                    ft.DataColumn(ft.Text("الدرجة", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER)),
                    ft.DataColumn(ft.Text("التاريخ", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER)),
                ],
                rows=[],
            )


            def open_edit_dialog(exam):
                date_format = "%d-%m-%Y"
                today_str = datetime.now().strftime(date_format)
                date_val = exam["date"] if exam["date"] and exam["date"] != "-" else today_str
                date_field = ft.TextField(
                    label="تاريخ الاختبار",
                    value=date_val,
                    read_only=True,
                    expand=True,
                    text_align=ft.TextAlign.RIGHT,
                    height=45,
                )
                total_field = ft.TextField(
                    label="الدرجة النهائية",
                    value=str(exam["total"]),
                    keyboard_type=ft.KeyboardType.NUMBER,
                    expand=True,
                    text_align=ft.TextAlign.RIGHT,
                    height=45,
                )
                score_field = ft.TextField(
                    label="درجة الطالب",
                    value=str(exam["score"]),
                    keyboard_type=ft.KeyboardType.NUMBER,
                    expand=True,
                    text_align=ft.TextAlign.RIGHT,
                    height=45,
                )
                def on_date_change(e):
                    date_field.value = e.control.value.strftime(date_format)
                    page.update()
                date_picker = ft.DatePicker(first_date=date(2020, 1, 1), last_date=date(2035, 12, 31), on_change=on_date_change)
                page.overlay.append(date_picker)
                page.update()
                def pick_date(e):
                    date_picker.open = True
                    page.update()
                date_field.suffix = ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, on_click=pick_date)
                def save_changes(e):
                    try:
                        new_total = int(total_field.value)
                        new_score = int(score_field.value)
                        new_date = date_field.value
                        exam_id = exam["id"]
                        with sqlite3.connect(students_db_path) as conn:
                            c = conn.cursor()
                            c.execute('''UPDATE exams SET exam_date=?, total_score=?, student_score=? WHERE id=?''',
                                      (new_date, new_total, new_score, exam_id))
                            conn.commit()
                        on_update_click(e)
                        page.close(dialog)
                        page.update()
                    except ValueError:
                        show_error_dialog(page, "يرجى إدخال أرقام صحيحة للدرجات")
                        page.update()
                def cancel_dialog(e):
                    page.close(dialog)
                    page.update()
                dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text(
                        "تعديل بيانات الاختبار",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                        color="#1E3A8A",
                    ),
                    content=ft.Container(
                        content=ft.Column(
                            [date_field, total_field, score_field],
                            tight=True,
                            spacing=10,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.padding.only(top=20, bottom=10, left=15, right=15),
                        height=250,   # 👈 هنا حددت ارتفاع ثابت
                        width=400,    # ممكن كمان تحدد عرض ثابت لو عايز
                    ),
                    actions=[
                        ft.TextButton(
                            "إلغاء",
                            on_click=cancel_dialog,
                            style=ft.ButtonStyle(
                                color="#D32F2F",
                                bgcolor={"hovered": "#FFEBEE"},
                            ),
                        ),
                        ft.ElevatedButton(
                            "حفظ",
                            on_click=save_changes,
                            style=ft.ButtonStyle(
                                bgcolor={"": "#0059DF", "hovered": "#1565C0"},
                                color="white",
                            ),
                        ),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                    shape=ft.RoundedRectangleBorder(radius=10),
                    bgcolor="white",
                )

                page.open(dialog)
                page.update()


            def rebuild_table():
                exams_table_widget.rows = [
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(idx+1), text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900)),
                            ft.DataCell(ft.Text(exam["code"], text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD, color="#000000")),
                            ft.DataCell(ft.Text(str(exam["total"]), text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)),
                            ft.DataCell(
                                ft.Text(str(exam["score"]), text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD,
                                        color=(ft.Colors.GREEN_700 if exam["score"] >= (exam["total"] / 2) else ft.Colors.RED_700))
                            ),
                            ft.DataCell(ft.Text(exam["date"], text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)),
                        ],
                        on_select_changed=lambda e, exam=exam: open_edit_dialog(exam),
                    )
                    for idx, exam in enumerate(students_exams)
                ]

                page.update()
            
            rebuild_table()
            return exams_table_widget   
  
        def responsive_tables_section():
            table_height = 300
            attendance_container = ft.Container(
                height=table_height, expand=True, bgcolor="#F4F4F4", border_radius=10, padding=10,
                content=ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=[
                    ft.Row(controls=[attendance_table()], scroll=ft.ScrollMode.AUTO, expand=True)
                ])
            )
            exams_container = ft.Container(
                height=table_height, expand=True, bgcolor="#F4F4F4", border_radius=10, padding=10,
                content=ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=[
                    ft.Row(controls=[exams_table()], scroll=ft.ScrollMode.AUTO, expand=True)
                ])
            )
            payment_container = ft.Container(
                height=table_height, expand=True, bgcolor="#F4F4F4", border_radius=10, padding=10,
                content=ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=[
                    ft.Row(controls=[payment_table()], scroll=ft.ScrollMode.AUTO, expand=True)
                ])
            )
            return ft.ResponsiveRow(
                controls=[
                    ft.Column([
                        section_header("الحضور والغياب", len(attendance_table().rows)),
                        attendance_container,
                    ], col={'xs': 12, 'sm': 12, 'md': 6, 'lg': 4, 'xl': 4}),
                    ft.Column([
                        section_header("الاختبارات", len(exams_table().rows)),
                        exams_container,
                    ], col={'xs': 12, 'sm': 12, 'md': 6, 'lg': 4, 'xl': 4}),
                    ft.Column([
                        section_header("الدفع", len(payment_table().controls[1].rows)),
                        payment_container,
                    ], col={'xs': 12, 'sm': 12, 'md': 12, 'lg': 4, 'xl': 4}),
                ],
                spacing=20, run_spacing=20, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, expand=True
            )   

        return ft.Container(
            border=ft.border.all(2, "#FFFFFF"), expand=True,
            padding=ft.padding.symmetric(horizontal=max(10, page.width * 0.05), vertical=20),
            border_radius=12, alignment=ft.alignment.center,
            content=ft.Column(
                [
                    ft.Column([
                        ft.Text(f"الطالب : {name}", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color="white"),
                        ft.Divider(height=20, color="white"),
                    ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(expand=True, content=ft.Column([
                        ft.Container(
                            bgcolor="#F4F4F4", border_radius=10, padding=10,
                            content=ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=[
                                ft.Row(controls=[student_table], scroll=ft.ScrollMode.AUTO, expand=True)
                            ])
                        ),
                        ft.Divider(height=20, color="white"),
                        responsive_tables_section()
                    ], spacing=0, scroll=ft.ScrollMode.AUTO, rtl=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                content=ft.Row(
                                    [
                                        ft.Text("تحديث", size=18, weight=ft.FontWeight.BOLD),
                                        ft.Icon(ft.Icons.UPDATE, size=28, color="green"),   # 👈 أيقونة خضراء
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                height=50,
                                expand=True,
                                bgcolor="#0059DF",
                                color="white",  # ينطبق على النص بس
                                on_click=on_update_click,
                            ),
                            ft.ElevatedButton(
                                content=ft.Row(
                                    [
                                        ft.Text("حذف", size=18, weight=ft.FontWeight.BOLD),
                                        ft.Icon(ft.Icons.DELETE, size=28, color="red"),   # 👈 أيقونة حمراء
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                height=50,
                                expand=True,
                                bgcolor="#0059DF",
                                color="white",
                                on_click=on_delete_click,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                        spacing=20,
                    )

                ],
                expand=True, alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, rtl=True,
            ),
        )
    
    def payment_container(page: ft.Page):
        # استيراد الدالة المساعدة
        from utils.date_utils import normalize_date_format  

        # ------------------------
        # قائمة المجموعات
        # ------------------------
        std_group = ft.Dropdown(
            label="المجموعة",
            hint_text="اختر مجموعة",
            options=get_groups(),
            autofocus=True,
            expand=True
        )   

        # ------------------------
        # جلب بيانات الطلاب
        # ------------------------
        def get_students(group_id=None, search_name=None):
            conn = sqlite3.connect(students_db_path)
            c = conn.cursor()
            month = PaymentTable.get_current_month()  # YYYY-MM 

            if group_id:
                c.execute('''SELECT s.id, s.code, s.first_name || ' ' || s.father_name || ' ' || s.family_name, 
                            (SELECT status FROM payments WHERE student_id = s.id AND month = ? LIMIT 1) as pay_status,
                            (SELECT month FROM payments WHERE student_id = s.id AND month = ? LIMIT 1) as pay_month
                            FROM students s 
                            WHERE s.group_id=? ORDER BY s.first_name, s.father_name, s.family_name''', (month, month, group_id))
            else:
                c.execute('''SELECT s.id, s.code, s.first_name || ' ' || s.father_name || ' ' || s.family_name, 
                            (SELECT status FROM payments WHERE student_id = s.id AND month = ? LIMIT 1) as pay_status,
                            (SELECT month FROM payments WHERE student_id = s.id AND month = ? LIMIT 1) as pay_month
                            FROM students s 
                            ORDER BY s.first_name, s.father_name, s.family_name''', (month, month)) 

            students = c.fetchall()
            conn.close()    

            if search_name:
                search_name = search_name.strip()
                students = [s for s in students if search_name in s[2] or search_name in str(s[1])]  # البحث بالاسم والكود  

            students.sort(key=lambda s: s[2])
            # إرجاع الاسم، الكود، حالة الدفع، الشهر (عربي للعرض)
            return [[s[2], s[1], s[3] if s[3] else "لم يدفع", PaymentTable.numeric_month_to_arabic(s[4] if s[4] else month)] for s in students] 

        students_data = []  # بداية بقائمة فارغة    

        def show_empty_message():
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.GROUP, size=64, color="#0059DF"),
                    ft.Text("برجاء اختيار مجموعة لعرض الطلاب",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color="#0059DF",
                            text_align=ft.TextAlign.CENTER)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.alignment.center,
                expand=True,
            )   

        # ------------------------
        # البحث
        # ------------------------
        def on_search_submit(e):
            name = e.control.value.strip()
            from utils.helpers import extract_unique_code
            group_id = std_group.value
            if name:
                name = extract_unique_code(name)
            students_data.clear()
            students_data.extend(get_students(group_id, name))
            payment_table.refresh(students_data)    

        # ------------------------
        # تغيير المجموعة
        # ------------------------
        def on_group_change(e):
            group_id = std_group.value
            students_data.clear()
            students_data.extend(get_students(group_id))
            payment_table.refresh(students_data)    

        # ------------------------
        # إنشاء الجدول
        # ------------------------
        payment_table = PaymentTable(students_data, page)  # نقل تعريف payment_table قبل الدوال 

        # ------------------------
        # حفظ حالة الدفع
        # ------------------------
        std_group.on_change = on_group_change   

        # ------------------------
        # الحاوية الكاملة
        # ------------------------
        return ft.Container(
            border=ft.border.all(2, "#FFFFFF"),
            expand=True,
            padding=20,
            border_radius=12,
            alignment=ft.alignment.center,
            content=ft.Column(
                expand=True,
                controls=[
                    ft.Text(
                        "تسجيل الدفع",
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
                                search_bar("ابحث بالاسم أو الكود...", on_submit=on_search_submit),
                                std_group
                            ]
                        )
                    ),
                    ft.Container(
                        expand=True,
                        padding=10,
                        bgcolor="#F4F4F4",
                        border_radius=15,
                        content=ft.Column(
                            [payment_table],
                            expand=True,
                            scroll=ft.ScrollMode.AUTO,
                        ),
                    ),
                ],
                spacing=20,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                rtl=True,
            ),
        )
    
    def attendance_container(page: ft.Page):
        # جلب المجموعات من قاعدة البيانات


        std_group = ft.Dropdown(
            label="المجموعة",
            hint_text="اختر مجموعة",
            options=get_groups(),
            autofocus=True,
            expand=True
        )

        # جلب بيانات الطلاب من القاعدة
        def get_students(group_id=None, search_name=None):
            from utils.date_utils import normalize_date_format
            conn = sqlite3.connect(students_db_path)
            c = conn.cursor()
            today = normalize_date_format(datetime.now().strftime('%Y-%m-%d'))
            if group_id:
                c.execute('''
                    WITH LastAttendance AS (
                        SELECT 
                            student_id,
                            status,
                            attendance_date,
                            ROW_NUMBER() OVER (PARTITION BY student_id ORDER BY attendance_date DESC) as rn
                        FROM attendance
                        WHERE attendance_date < ?
                    ),
                    TodayAttendance AS (
                        SELECT student_id, status
                        FROM attendance
                        WHERE attendance_date = ?
                    )
                    SELECT 
                        s.id, 
                        s.code, 
                        s.first_name || ' ' || s.father_name || ' ' || s.family_name,
                        COALESCE(t.status, 'غير محدد') as today_status,
                        COALESCE(l.status, '-') as last_status
                    FROM students s
                    LEFT JOIN TodayAttendance t ON s.id = t.student_id
                    LEFT JOIN LastAttendance l ON s.id = l.student_id AND l.rn = 1
                    WHERE s.group_id = ?
                    ORDER BY s.first_name, s.father_name, s.family_name
                ''', (today, today, group_id))
            else:
                c.execute('''
                    WITH LastAttendance AS (
                        SELECT 
                            student_id,
                            status,
                            attendance_date,
                            ROW_NUMBER() OVER (PARTITION BY student_id ORDER BY attendance_date DESC) as rn
                        FROM attendance
                        WHERE attendance_date < ?
                    ),
                    TodayAttendance AS (
                        SELECT student_id, status
                        FROM attendance
                        WHERE attendance_date = ?
                    )
                    SELECT 
                        s.id, 
                        s.code, 
                        s.first_name || ' ' || s.father_name || ' ' || s.family_name,
                        COALESCE(t.status, 'غير محدد') as today_status,
                        COALESCE(l.status, '-') as last_status
                    FROM students s
                    LEFT JOIN TodayAttendance t ON s.id = t.student_id
                    LEFT JOIN LastAttendance l ON s.id = l.student_id AND l.rn = 1
                    ORDER BY s.first_name, s.father_name, s.family_name
                ''', (today, today))
            students = c.fetchall()
            conn.close()
            if search_name:
                search_name = search_name.strip()
                students = [s for s in students if search_name in s[2] or search_name in str(s[1])]  # بحث بالاسم أو الكود
            # ترتيب أبجدي بعد البحث
            students.sort(key=lambda s: s[2])
            # إرجاع الاسم، الكود، اخر حالة، الحالة الحالية
            # ترتيب البيانات: [الاسم، الكود، آخر حالة حضور، الحالة الحالية]
            formatted_students = []
            for s in students:
                name = s[2]  # الاسم الكامل
                code = s[1]  # الكود
                last_status = s[4]  # حالة آخر حصة
                current_status = s[3]  # حالة اليوم
                formatted_students.append([name, code, last_status, current_status])
            return formatted_students

        students_data = []  # بداية بقائمة فارغة

        def on_search_submit(e):
                barcode = e.control.value.strip()
                from utils.helpers import extract_unique_code
                group_id = std_group.value
                if not group_id:
                    show_error_dialog(page, "يرجى اختيار المجموعة أولاً")
                    e.control.value = ""
                    e.control.focus()
                    page.update()
                    return

                if barcode:
                    barcode = extract_unique_code(barcode)
                    # تحديث البيانات للعرض
                    students_data.clear()
                    students_data.extend(get_students(group_id, barcode))
                    
                    # إذا وجد الطالب، قم بتسجيل حضوره مباشرة
                    if students_data:
                        student = students_data[0]  # نأخذ أول طالب (يفترض أن البحث بالباركود سيرجع طالب واحد)
                        student[3] = "حاضر"  # تحديث حالة الحضور
                        
                        # حفظ في قاعدة البيانات مباشرة
                        conn = sqlite3.connect(students_db_path)
                        c = conn.cursor()
                        
                        # الحصول على معرف الطالب من الكود
                        c.execute('SELECT id FROM students WHERE code=?', (student[1],))
                        student_id = c.fetchone()
                        
                        if student_id:
                            from utils.date_utils import normalize_date_format
                            today = normalize_date_format(datetime.now().strftime('%Y-%m-%d'))
                            days_ar = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]
                            day_idx = datetime.strptime(today, '%d-%m-%Y').weekday()
                            day_ar = days_ar[(day_idx + 1) % 7]
                            
                            # تحديث/إضافة سجل الحضور
                            c.execute('''INSERT INTO attendance (student_id, attendance_date, status, day) 
                                       VALUES (?, ?, ?, ?)
                                       ON CONFLICT(student_id, attendance_date) 
                                       DO UPDATE SET status=excluded.status, day=excluded.day''',
                                    (student_id[0], today, "حاضر", day_ar))
                            
                            # إرسال إشعار تليجرام
                            c.execute('''SELECT first_name || ' ' || father_name || ' ' || family_name, guardian_chat_id 
                                       FROM students WHERE id = ?''', (student_id[0],))
                            student_info = c.fetchone()
                            if student_info and student_info[1]:
                                from utils.telegram_bot import send_telegram_message
                                message = f"⏰ تحديث حالة الحضور\n"
                                message += f"الطالب: {student_info[0]}\n"
                                message += f"اليوم: {day_ar}\n"
                                message += f"التاريخ: {today}\n"
                                message += f"الحالة: حاضر\n"
                                try:
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    loop.run_until_complete(send_telegram_message(student_info[1], message))
                                finally:
                                    loop.close()
                            
                            conn.commit()
                            show_success_dialog(page, f"✅ تم تسجيل حضور الطالب: {student[0]}")
                        
                        conn.close()
                        attendance_table.refresh(students_data)
                    else:
                        show_error_dialog(page, "❌ لم يتم العثور على الطالب")
                    
                    # تفريغ حقل البحث والتركيز عليه للمسح التالي
                    e.control.value = ""
                    e.control.focus()
                    page.update()

        def on_group_change(e):
            group_id = std_group.value
            students_data.clear()
            students_data.extend(get_students(group_id))
            attendance_table.refresh(students_data)

        def on_update_click(e):
            group_id = std_group.value
            if not group_id:
                show_error_dialog(e.page, "يرجى اختيار مجموعة أولاً")
                return
                
            # تعيين الطلاب الذين لم يتم تحديد حالتهم كغائبين
            for student in students_data:
                if student[3] not in ["حاضر", "غائب", "معتذر"]:
                    student[3] = "غائب"
            # استيراد الدالة المساعدة في بداية الملف:
            from utils.date_utils import normalize_date_format
            
            conn = sqlite3.connect(students_db_path)
            c = conn.cursor()
            today = normalize_date_format(datetime.now().strftime('%Y-%m-%d'))
            # استخراج اليوم بالعربي
            days_ar = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]
            day_idx = datetime.strptime(today, '%d-%m-%Y').weekday()
            day_ar = days_ar[(day_idx + 1) % 7]
            # جلب الطلاب في المجموعة المختارة فقط
            c.execute('SELECT id, first_name || " " || father_name || " " || family_name FROM students WHERE group_id=?', (group_id,))
            group_students = {row[1]: row[0] for row in c.fetchall()}
            # حساب عدد الطلاب الذين سيتم تحديد حالتهم كغائبين تلقائياً
            unset_count = sum(1 for student in students_data if student[3] == "غير محدد")
            if unset_count > 0:
                show_success_dialog(e.page, f"سيتم اعتبار {unset_count} طالب غير محدد الحالة كغائبين")

            updated_count = 0
            for name, code, last_status, current_status in students_data:
                # البحث بالاسم أو الكود
                student_id = None
                if name in group_students:
                    student_id = group_students[name]
                else:
                    # جلب id بالكود إذا لم يوجد بالاسم
                    c.execute('SELECT id FROM students WHERE code=?', (code,))
                    result = c.fetchone()
                    if result:
                        student_id = result[0]
                if student_id:
                    # التحقق من صحة الحالة قبل الحفظ
                    # التأكد من أن الحالة صحيحة
                    if current_status not in ["حاضر", "غائب", "معتذر"]:
                        show_error_dialog(e.page, "يجب تحديد حالة الحضور (حاضر/غائب/معتذر)")
                        return
                    
                    # التحقق من الحالة الحالية في قاعدة البيانات
                    c.execute('''SELECT status FROM attendance 
                               WHERE student_id = ? AND attendance_date = ?''', (student_id, today))
                    current_db_status = c.fetchone()
                    
                    # تنفيذ الإدراج/التحديث
                    c.execute('''INSERT INTO attendance (student_id, attendance_date, status, day) VALUES (?, ?, ?, ?)
                        ON CONFLICT(student_id, attendance_date) DO UPDATE SET status=excluded.status, day=excluded.day''', 
                        (student_id, today, current_status, day_ar))
                    
                    # إرسال رسالة تليجرام لولي الأمر فقط إذا تغيرت الحالة
                    if not current_db_status or current_db_status[0] != current_status:
                        from utils.telegram_bot import send_telegram_message
                        # جلب معرف التليجرام لولي الأمر ومعلومات الطالب
                        c.execute('''SELECT s.first_name || ' ' || s.father_name || ' ' || s.family_name, s.guardian_chat_id 
                                   FROM students s WHERE s.id = ?''', (student_id,))
                        student_info = c.fetchone()
                        if student_info and student_info[1]:  # إذا كان لديه معرف تليجرام لولي الأمر
                            student_name, guardian_chat_id = student_info
                            message = f"⏰ تحديث حالة الحضور\n"
                            message += f"الطالب: {student_name}\n"
                            message += f"اليوم: {day_ar}\n"
                            message += f"التاريخ: {today}\n"
                            message += f"الحالة: {current_status}\n"
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                success, error_msg = loop.run_until_complete(send_telegram_message(guardian_chat_id, message))
                                if not success:
                                    show_error_dialog(e.page, f"تم تحديث الحضور ولكن فشل إرسال الإشعار لولي أمر {student_name}:\n{error_msg}")
                            finally:
                                loop.close()
                    
                    updated_count += 1
            conn.commit()
            conn.close()
            if updated_count:
                # تعديل رسالة النجاح لتشمل معلومات إرسال الإشعارات
                success_message = f"✅ تم تحديث حالة الحضور لعدد {updated_count} طالب في المجموعة"
                if any(s[1] for s in students_data if s[3] == current_status):  # إذا كان هناك طلاب لديهم معرف تليجرام
                    success_message += "\n📱 تم إرسال إشعارات لأولياء الأمور المسجلين في التليجرام"
                show_success_dialog(e.page, success_message)
            else:
                show_error_dialog(e.page, "لا يوجد طلاب في المجموعة المحددة")

        attendance_table = AttendanceTable(students_data, page)
        std_group.on_change = on_group_change

        return ft.Container(
            border=ft.border.all(2, "#FFFFFF"),
            expand=True,
            padding=20,
            # bgcolor="#0D6EFD",
            border_radius=12,
            alignment=ft.alignment.center,
            content=ft.Column(
                expand=True,
                controls=[
                    # العنوان فوق
                    ft.Text(
                        "تسجيل الحضور والغياب",
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
                                            search_bar("ابحث بالاسم أو الكود...",on_submit=on_search_submit,),
                                            std_group,
                                        ]
                                    )
                                ),

                    # 🔹 الجزء الأوسط بس هو اللي يسكرول
                    ft.Container(
                        expand=True,  # يتمدد ليأخذ المساحة المتبقية
                        padding=10,
                        bgcolor="#F4F4F4",  # مطابق لـ ExamTable
                        border_radius=15,
                        content=ft.Column(
                            [attendance_table],
                            expand=True,
                            scroll=ft.ScrollMode.AUTO,
                        ),
                    ),

                    # الزر تحت

                    ft.Row(
                        [
                            ft.ElevatedButton(
                                content=ft.Row(
                                    [
                                        ft.Text("حفظ", size=18, weight=ft.FontWeight.BOLD, color="#F5F5F5"),
                                        ft.Icon(ft.Icons.SAVE, size=28, color="#07C06A"),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=10
                                ),
                                height=50,
                                expand=True,
                                bgcolor="#0059DF",
                                on_click=on_update_click,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                        spacing=20,
                    ),
                ],
                spacing=20,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,  # يحافظ على العنوان فوق والزر تحت
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                rtl=True,
            ),
        )   

    def exam_container(page: ft.Page):
        # ------------------------
        # قائمة المجموعات
        # ------------------------
        std_group = ft.Dropdown(
            label="المجموعة",
            hint_text="اختر مجموعة",
            options=get_groups(),
            autofocus=True,
            expand=True
        )   

        # ------------------------
        # جلب بيانات الطلاب
        # ------------------------
        def get_students(group_id=None, search_name=None):
            conn = sqlite3.connect(students_db_path)
            c = conn.cursor()
            if group_id:
                c.execute('''SELECT s.code, s.first_name || ' ' || s.father_name || ' ' || s.family_name,
                            (SELECT student_score || '/' || total_score FROM exams WHERE student_id = s.id ORDER BY date(exam_date) DESC, id DESC LIMIT 1) as last_grade,
                            (SELECT COUNT(*) FROM exams WHERE student_id = s.id) as num_exams
                            FROM students s WHERE s.group_id=? ORDER BY s.first_name, s.father_name, s.family_name''', (group_id,))
            else:
                c.execute('''SELECT s.code, s.first_name || ' ' || s.father_name || ' ' || s.family_name,
                            (SELECT student_score || '/' || total_score FROM exams WHERE student_id = s.id ORDER BY date(exam_date) DESC, id DESC LIMIT 1) as last_grade,
                            (SELECT COUNT(*) FROM exams WHERE student_id = s.id) as num_exams
                            FROM students s ORDER BY s.first_name, s.father_name, s.family_name''')
            students = c.fetchall()
            conn.close()    

            if search_name:
                search_name = search_name.strip()
                students = [s for s in students if search_name in s[1] or search_name in str(s[0])] 

            students.sort(key=lambda s: s[1])
            return [[s[0], s[1], s[2] if s[2] else "غير متوفر", s[3]] for s in students]    

        students_data = []  

        def show_empty_message():
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.GROUP, size=64, color="#0059DF"),
                    ft.Text("برجاء اختيار مجموعة لعرض الطلاب",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color="#0059DF",
                            text_align=ft.TextAlign.CENTER)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.alignment.center,
                expand=True,
            )   

        # ------------------------
        # البحث
        # ------------------------
        def on_search_submit(e):
            name = e.control.value.strip()
            from utils.helpers import extract_unique_code
            group_id = std_group.value
            if name:
                name = extract_unique_code(name)
            students_data.clear()
            students_data.extend(get_students(group_id, name))
            exam_table.refresh(students_data)   

        # ------------------------
        # تغيير المجموعة
        # ------------------------
        def on_group_change(e):
            group_id = std_group.value
            if group_id:
                students_data.clear()
                students_data.extend(get_students(group_id))
                exam_table.refresh(students_data)
            else:
                students_data.clear()
                exam_table.refresh([])  

        # ------------------------
        # إنشاء الجدول
        # ------------------------
        exam_table = ExamTable(students_data, page, students_db_path)
        std_group.on_change = on_group_change   

        # ------------------------
        # الحاوية الكاملة
        # ------------------------
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
                                "تسجيل الدرجات",
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
                                        search_bar("ابحث بالاسم أو الكود...", on_submit=on_search_submit),
                                        std_group,
                                    ]
                                )
                            ),
                        ],
                        spacing=10,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(
                        expand=True,
                        padding=10,
                        bgcolor="#F4F4F4",
                        border_radius=15,
                        content=ft.Column(
                            [exam_table],
                            expand=True,
                            scroll=ft.ScrollMode.AUTO,
                        ),
                    ),
                    
                ],
                expand=True,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                rtl=True,
            ),
        )



    std_page = ft.Row(
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        # ========== Header ========== 
                        ft.Column(
                            [
                                ft.Text(
                                    "إدارة الطلاب",
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
    
                        # ========== Content (Scrollable Cards) ==========
                        ft.Container(
                            expand=True,
                            content=ft.Column(
                                controls=[
                                    ft.Container(
                                        content=ft.Row(
                                            [
                                                ft.Text("إضافة طالب", size=22, weight="bold", color="#ffffff"),
                                                ft.Icon(ft.Icons.PERSON_ADD, size=32, color="#ffffff"),
                                            ],
                                            alignment="center",
                                            spacing=12,
                                        ),
                                        # bgcolor="#0D6EFD",
                                        bgcolor="#0D6EFD",
                                        border_radius=12,
                                        height=80,
                                        expand=True,
                                        margin=5,
                                        padding=5,
                                        border=ft.border.all(2, "#0044A9"),
                                        ink=True,
                                        on_click=lambda e: update_side_content(add_student_container()),
                                        alignment=ft.alignment.center,
                                    ),
                                    ft.Container(
                                        content=ft.Row(
                                            [
                                                ft.Text("تعديل طالب", size=22, weight="bold", color="#ffffff"),
                                                ft.Icon(ft.Icons.EDIT, size=32, color="#ffffff"),
                                            ],
                                            alignment="center",
                                            spacing=12,
                                        ),
                                        # bgcolor="#FFC107",
                                        bgcolor="#3B7EFF",
                                        border_radius=12,
                                        height=80,
                                        expand=True,
                                        margin=5,
                                        padding=5,
                                        border=ft.border.all(2, "#0044A9"),
                                        ink=True,
                                        on_click=lambda e: update_side_content(edit_student_container(e=e)),
                                        alignment=ft.alignment.center,
                                    ),
                                    ft.Container(
                                        content=ft.Row(
                                            [
                                                ft.Text("تسجيل الدفع", size=22, weight="bold", color="#ffffff"),
                                                ft.Icon(ft.Icons.ATTACH_MONEY, size=32, color="#ffffff"),
                                            ],
                                            alignment="center",
                                            spacing=12,
                                        ),
                                        # bgcolor="#198754",
                                        bgcolor="#6196FF",
                                        border_radius=12,
                                        height=80,
                                        expand=True,
                                        margin=5,
                                        padding=5,
                                        border=ft.border.all(2, "#0044A9"),
                                        ink=True,
                                        on_click=lambda e: update_side_content(payment_container(page)),
                                        alignment=ft.alignment.center,
                                    ),
                                    ft.Container(
                                        content=ft.Row(
                                            [
                                                ft.Text("الحضور والغياب", size=22, weight="bold", color="#ffffff"),
                                                ft.Icon(ft.Icons.CHECKLIST, size=32, color="#ffffff"),
                                            ],
                                            alignment="center",
                                            spacing=12,
                                        ),
                                        # bgcolor="#FF8E8E",
                                        bgcolor="#739EFF",
                                        border_radius=12,
                                        height=80,
                                        expand=True,
                                        margin=5,
                                        padding=5,
                                        border=ft.border.all(2, "#0044A9"),
                                        ink=True,
                                        on_click=lambda e: update_side_content(attendance_container(page)),
                                        alignment=ft.alignment.center,
                                    ),
                                    ft.Container(
                                        content=ft.Row(
                                            [
                                                ft.Text("تسجيل الدرجات", size=22, weight="bold", color="#ffffff"),
                                                ft.Icon(ft.Icons.GRADE, size=32, color="#ffffff"),
                                            ],
                                            alignment="center",
                                            spacing=12,
                                        ),
                                        # bgcolor="#6F42C1",
                                        bgcolor="#80ADFF",
                                        border_radius=12,
                                        height=80,
                                        expand=True,
                                        margin=5,
                                        padding=5,
                                        border=ft.border.all(2, "#0044A9"),
                                        ink=True,
                                        on_click=lambda e: update_side_content(exam_container(page)),
                                        alignment=ft.alignment.center,
                                    ),
                                    ft.Container(
                                        content=ft.Row([
                                            ft.Text("عرض الطلاب", size=20, weight="bold", color="#ffffff"),
                                            ft.Icon(ft.Icons.REMOVE_RED_EYE_SHARP, size=36, color="#ffffff")
                                        ], alignment="center", spacing=12),
                                        # bgcolor="#949494",
                                        bgcolor="#99BFFF",
                                        border_radius=12,
                                        height=80,
                                        expand=True,
                                        margin=5,
                                        padding=5,
                                        border=ft.border.all(2, "#0044A9"),
                                        ink=True,
                                        on_click=lambda e:update_side_content(show_student_container(page)),
                                        alignment=ft.alignment.center
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
    
    return std_page



