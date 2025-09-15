# pages/group_page.py
import flet as ft
import sqlite3

# استيراد من الوحدات الأخرى في المشروع
from utils.database import students_db_path
from utils.helpers import show_error_dialog, show_success_dialog, search_bar, get_groups

def group_page(page):
    # حاوية العرض الجانبية
    side_rec_container_grp = ft.Container(
        margin=ft.margin.only(left=10, right=0, top=10, bottom=10),
        padding=10,
        alignment=ft.alignment.center,
        bgcolor="#3B7EFF",
        border_radius=10,
        expand=4,
        content=ft.Text("اختر عملية من القائمة", size=20, weight="bold")
    )

    def update_side_content(new_content):
        side_rec_container_grp.content = new_content
        side_rec_container_grp.update()
 
    def add_group_container():
        group_name = ft.TextField(label="اسم المجموعة", text_align=ft.TextAlign.RIGHT)
        group_day_1 = ft.Dropdown(
            label="اليوم الأول",
            hint_text="اختر اليوم",
            options=[ft.dropdown.Option(d) for d in ["السبت", "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]],
            text_align=ft.TextAlign.RIGHT,
            expand=True
        )
        group_day_2 = ft.Dropdown(
            label="اليوم الثاني",
            hint_text="اختر اليوم",
            options=[ft.dropdown.Option(d) for d in ["السبت", "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]],
            text_align=ft.TextAlign.RIGHT,
            expand=True
        )
        group_stage = ft.Dropdown(
            label="مرحلة المجموعة",
            hint_text="اختر المرحلة",
            options=[ft.dropdown.Option(s) for s in ["ابتدائي", "إعدادي", "ثانوي"]],
            text_align=ft.TextAlign.RIGHT,
            expand=True
        )

        def on_save_click(e):
            if not all([group_name.value, group_day_1.value, group_day_2.value, group_stage.value]):
                show_error_dialog(page, "يرجى ملء جميع الحقول")
                return
            days = f"{group_day_1.value} و {group_day_2.value}"
            with sqlite3.connect(students_db_path) as conn:
                c = conn.cursor()
                c.execute('SELECT COUNT(*) FROM groups WHERE name=?', (group_name.value.strip(),))
                if c.fetchone()[0] > 0:
                    show_error_dialog(e.page, "اسم المجموعة موجود بالفعل")
                    group_name.value = ""
                    group_name.update()
                    return
                try:
                    c.execute('INSERT INTO groups (name, days, stage) VALUES (?, ?, ?)',
                              (group_name.value.strip(), days, group_stage.value))
                    conn.commit()
                    show_success_dialog(e.page, "تم حفظ المجموعة بنجاح")
                    group_name.value = ""
                    group_name.update()
                except Exception as ex:
                    show_error_dialog(e.page, f"خطأ: {ex}")

        def on_clear_click(e):
            for field in [group_name, group_day_1, group_day_2, group_stage]:
                field.value = None
                field.update()

        return ft.Container(
            border=ft.border.all(2, "#FFFFFF"),
            expand=True,
            padding=20,
            # bgcolor="#0D6EFD",
            border_radius=12,
            content=ft.Column(
                [
                    ft.Text("إضافة مجموعة", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color="white"),
                    ft.Divider(height=20, color="white"),
                    ft.Column(
                        [group_name, ft.Row([group_day_1, group_day_2]), group_stage],
                        spacing=20,
                        scroll=ft.ScrollMode.AUTO,
                        expand=True
                    ),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                content=ft.Row(
                                    [
                                        ft.Text("حفظ", size=18, weight=ft.FontWeight.BOLD, color="#F5F5F5"),
                                        ft.Icon(ft.Icons.SAVE, size=24, color="#07C06A"),  # 👈 هنا تتحكم في الحجم
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=10
                                ),
                                height=50,
                                expand=True,
                                bgcolor="#0059DF",
                                on_click=on_save_click
                            ),

                            
                            ft.ElevatedButton(
                                content=ft.Row(
                                    [
                                        ft.Text("مسح", size=18, weight=ft.FontWeight.BOLD, color="#F5F5F5"),
                                        ft.Icon(ft.Icons.CLEAR, size=24, color="#FB4E5F"),  # 👈 تكبير الأيقونة

                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=10
                                ),
                                
                                height=50,
                                expand=True,
                                bgcolor="#0059DF",
                                on_click=on_clear_click
                            )

                        ],
                        alignment=ft.MainAxisAlignment.SPACE_AROUND
                    )
                ],
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=25,
                rtl=True
            )
        )

    def edit_group_container():
        group_name = ft.TextField(label="اسم المجموعة", text_align=ft.TextAlign.RIGHT)
        group_day_1 = ft.Dropdown(
            label="اليوم الأول",
            hint_text="اختر اليوم",
            options=[ft.dropdown.Option(d) for d in ["السبت", "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]],
            text_align=ft.TextAlign.RIGHT,
            expand=True
        )
        group_day_2 = ft.Dropdown(
            label="اليوم الثاني",
            hint_text="اختر اليوم",
            options=[ft.dropdown.Option(d) for d in ["السبت", "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]],
            text_align=ft.TextAlign.RIGHT,
            expand=True
        )
        group_stage = ft.Dropdown(
            label="مرحلة المجموعة",
            hint_text="اختر المرحلة",
            options=[ft.dropdown.Option(s) for s in ["ابتدائي", "إعدادي", "ثانوي"]],
            text_align=ft.TextAlign.RIGHT,
            expand=True
        )

        def search_group(name):
            with sqlite3.connect(students_db_path) as conn:
                c = conn.cursor()
                c.execute('SELECT id, name, days, stage FROM groups WHERE name = ?', (name.strip(),))
                return c.fetchone()

        def on_search_submit(e):
            name = e.control.value.strip()
            # إذا كان البحث عبارة عن كود رقمي، فلتره أولاً
            if name.isdigit():
                from utils.helpers import extract_unique_code
                name = extract_unique_code(name)
            result = search_group(name)
            if result:
                group_name.group_id = result[0]
                group_name.value = result[1]
                days = result[2].split(' و ')
                group_day_1.value = days[0] if len(days) > 0 else None
                group_day_2.value = days[1] if len(days) > 1 else None
                group_stage.value = result[3]
                for field in [group_name, group_day_1, group_day_2, group_stage]:
                    field.update()
            else:
                show_error_dialog(e.page, "المجموعة غير موجودة")

        def on_update_click(e):
            if not all([group_name.value, group_day_1.value, group_day_2.value, group_stage.value]):
                show_error_dialog(e.page, "يرجى ملء جميع الحقول")
                return
            days = f"{group_day_1.value} و {group_day_2.value}"
            with sqlite3.connect(students_db_path) as conn:
                c = conn.cursor()
                group_id = getattr(group_name, 'group_id', None)
                c.execute('SELECT COUNT(*) FROM groups WHERE name=? AND id<>?', (group_name.value.strip(), group_id))
                if c.fetchone()[0] > 0:
                    show_error_dialog(e.page, "اسم المجموعة موجود بالفعل، يرجى اختيار اسم آخر")
                    group_name.value = ""
                    group_name.update()
                    return
                try:
                    if group_id:
                        c.execute('UPDATE groups SET name=?, days=?, stage=? WHERE id=?',
                                  (group_name.value.strip(), days, group_stage.value, group_id))
                        conn.commit()
                        show_success_dialog(e.page, "تم تحديث بيانات المجموعة بنجاح")
                    else:
                        show_error_dialog(e.page, "يجب البحث عن المجموعة أولاً")
                except Exception as ex:
                    show_error_dialog(e.page, f"خطأ: {ex}")

        def on_delete_click(e):
            with sqlite3.connect(students_db_path) as conn:
                c = conn.cursor()
                c.execute('SELECT id FROM groups WHERE name=?', (group_name.value.strip(),))
                group_row = c.fetchone()
                if group_row:
                    group_id = group_row[0]
                    c.execute('SELECT id FROM students WHERE group_id=?', (group_id,))
                    students = c.fetchall()
                    for s in students:
                        c.execute('DELETE FROM payments WHERE student_id=?', (s[0],))
                        c.execute('DELETE FROM attendance WHERE student_id=?', (s[0],))
                        c.execute('DELETE FROM exams WHERE student_id=?', (s[0],))
                    c.execute('DELETE FROM students WHERE group_id=?', (group_id,))
                    c.execute('DELETE FROM groups WHERE id=?', (group_id,))
                    conn.commit()
                    show_success_dialog(e.page, "تم حذف المجموعة وجميع بيانات الطلاب المرتبطين بها")
                    for field in [group_name, group_day_1, group_day_2, group_stage]:
                        field.value = None
                        field.update()
                    try:
                        if hasattr(e.page, "std_group"):
                            e.page.std_group.options = get_groups()
                            e.page.std_group.update()
                    except Exception:
                        pass
                else:
                    show_error_dialog(e.page, "المجموعة غير موجودة")

        return ft.Container(
            border=ft.border.all(2, "#FFFFFF"),
            expand=True,
            padding=20,
            # bgcolor="#0D6EFD",
            border_radius=12,
            content=ft.Column(
                [
                    ft.Text("تعديل مجموعة", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color="white"),
                    ft.Divider(height=20, color="white"),
                    ft.Container(
                        expand=True,
                        content=ft.Column(
                            [
                                search_bar("ابحث عن مجموعة...", on_submit=on_search_submit),
                                group_name,
                                ft.Row([group_day_1, group_day_2]),
                                group_stage
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            rtl=True,
                            scroll=ft.ScrollMode.AUTO
                        )
                    ),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                content=ft.Row(
                                    [
                                        ft.Text("تحديث", size=18, weight=ft.FontWeight.BOLD, color="#F5F5F5"),
                                        ft.Icon(ft.Icons.UPDATE, size=28, color="#07C06A"),  # 👈 حجم الأيقونة أكبر
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=10
                                ),
                                height=50,
                                expand=True,
                                bgcolor="#0059DF",
                                on_click=on_update_click
                            ),

                            ft.ElevatedButton(
                                content=ft.Row(
                                    [
                                        ft.Text("حذف", size=18, weight=ft.FontWeight.BOLD, color="#F5F5F5"),
                                        ft.Icon(ft.Icons.DELETE, size=28, color="#FB4E5F"),  # 👈 أيقونة الحذف باللون الأحمر
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=10
                                ),
                                height=50,
                                expand=True,
                                bgcolor="#0059DF",
                                on_click=on_delete_click
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_AROUND
                    )

                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                rtl=True
            )
        )

    def group_details_container(name, page):

        def on_edit_click(e):
            student_id = e.control.data["id"]
            student_name = e.control.data["name"]
            # جلب كل المجموعات
            with sqlite3.connect(students_db_path) as conn:
                c = conn.cursor()
                c.execute('SELECT id, name FROM groups')
                all_groups = c.fetchall()
            group_dropdown = ft.Dropdown(
                label="المجموعة الجديدة",
                hint_text="اختر مجموعة جديدة",
                options=[ft.dropdown.Option(key=str(g[0]), text=g[1]) for g in all_groups],
                expand=True
            )
            def on_delete_student(ev):
                with sqlite3.connect(students_db_path) as conn:
                    c = conn.cursor()
                    # حذف الطالب وبياناته المرتبطة
                    c.execute('DELETE FROM payments WHERE student_id=?', (student_id,))
                    c.execute('DELETE FROM attendance WHERE student_id=?', (student_id,))
                    c.execute('DELETE FROM exams WHERE student_id=?', (student_id,))
                    c.execute('DELETE FROM students WHERE id=?', (student_id,))
                    conn.commit()
                show_success_dialog(page, "تم حذف الطالب")
                page.close(dlg_modal)
                page.update()
            def on_move_student(ev):
                new_group_id = group_dropdown.value
                if not new_group_id:
                    show_error_dialog(page, "يرجى اختيار مجموعة جديدة")
                    return
                # تحقق من عدم نقل الطالب لنفس مجموعته
                if str(new_group_id) == str(e.control.data.get("group_id")):
                    show_error_dialog(page, "لا يمكن نقل الطالب لنفس مجموعته الحالية")
                    return
                with sqlite3.connect(students_db_path) as conn:
                    c = conn.cursor()
                    c.execute('UPDATE students SET group_id=? WHERE id=?', (new_group_id, student_id))
                    conn.commit()
                show_success_dialog(page, "تم نقل الطالب بنجاح")
                page.close(dlg_modal)
                page.update()
            dlg_modal = ft.AlertDialog(
                modal=False,
                title=ft.Text(f"تعديل الطالب: {student_name}"),
                content=ft.Column([
                    group_dropdown,
                ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                actions=[
                    ft.Row([
                        ft.ElevatedButton(
                            bgcolor="#FB4E5F",
                            content=ft.Row([
                                ft.Icon(ft.Icons.DELETE, color="white"),
                                ft.Text("حذف الطالب", color="white"),
                            ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                            on_click=on_delete_student,
                        ),
                        ft.ElevatedButton(
                            bgcolor="#00409F",
                            content=ft.Row([
                                ft.Icon(ft.Icons.SWAP_HORIZ, color="white"),
                                ft.Text("نقل للمجموعة", color="white"),
                            ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                            on_click=on_move_student,
                        ),
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)
                ],
                actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                on_dismiss=lambda e: page.close(dlg_modal),
            )
            page.open(dlg_modal)
            return dlg_modal

        # جلب بيانات المجموعة وطلابها من قاعدة البيانات
        with sqlite3.connect(students_db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT id, name, days, stage FROM groups WHERE name=?', (name,))
            group_row = c.fetchone()
            if not group_row:
                return ft.Container(
                    expand=True,
                    padding=20,
                    bgcolor="#0D6EFD",
                    border_radius=15,
                    content=ft.Column([
                        ft.Text("تفاصيل المجموعة", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color="white"),
                        ft.Divider(height=20, color="white"),
                        ft.Text("المجموعة غير موجودة", size=20, color="white", text_align=ft.TextAlign.CENTER),
                    ], spacing=25, expand=True, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, rtl=True)
                )
            group_id, group_name, group_days, group_stage = group_row
            c.execute('SELECT COUNT(*) FROM students WHERE group_id=?', (group_id,))
            group_count = c.fetchone()[0]
            group_count_text = f"عدد طلاب المجموعة : {group_count}"
            group_stage_text = f"مرحلة المجموعة : {group_stage}"
            group_days_text = f"أيام المجموعة: {group_days}"
            # جلب الطلاب
            c.execute('''SELECT id, first_name, father_name, family_name, phone, guardian_phone, grade FROM students WHERE group_id=?''', (group_id,))
            students = c.fetchall()
            students_data = []
            for s in students:
                student_id, first_name, father_name, family_name, phone, guardian_phone, grade = s
                full_name = f"{first_name} {father_name} {family_name}"
                # جلب حالة الدفع
                c.execute('SELECT status FROM payments WHERE student_id=? ORDER BY month DESC LIMIT 1', (student_id,))
                payment_status = c.fetchone()
                payment_status = payment_status[0] if payment_status else "-"
                # جلب عدد الاختبارات
                c.execute('SELECT COUNT(*) FROM exams WHERE student_id=?', (student_id,))
                tests_count = c.fetchone()[0]
                # جلب الحضور
                c.execute('SELECT COUNT(*) FROM attendance WHERE student_id=? AND status="حاضر"', (student_id,))
                attended = c.fetchone()[0]
                c.execute('SELECT COUNT(*) FROM attendance WHERE student_id=?', (student_id,))
                total_att = c.fetchone()[0]
                attendance = f"{attended}/{total_att}" if total_att else "-"
                students_data.append({
                    "id": student_id,
                    "name": full_name,
                    "student_phone": phone,
                    "parent_phone": guardian_phone,
                    "grade": grade,
                    "payment_status": payment_status,
                    "tests_count": tests_count,
                    "attendance": attendance,
                    "group_id": group_id
                })

        if not students_data:
            return ft.Container(
                expand=True,
                padding=20,
                bgcolor="#0D6EFD",
                border_radius=15,
                content=ft.Column(
                    [
                        ft.Text(
                            "تفاصيل المجموعة",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER,
                            color="white"
                        ),
                        ft.Divider(height=20, color="white"),
                        ft.Text("لا يوجد طلاب في هذه المجموعة", size=20, color="white", text_align=ft.TextAlign.CENTER),
                    ],
                    spacing=25,
                    expand=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    rtl=True
                )
            )

        # ------------------------
        # إنشاء الجدول التفاعلي
        # ------------------------
        student_table = ft.DataTable(
            expand=True,
            column_spacing=30,
            data_row_min_height=50,
            heading_row_color="#1E3A8A",
            border=ft.border.all(1, "#1E3A8A"),
            divider_thickness=1,
            columns=[
                ft.DataColumn(ft.Text("#", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("الاسم الثلاثي", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("هاتف الطالب", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("هاتف ولي الأمر", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("الصف", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("حالة الدفع", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("عدد الاختبارات", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("الحضور", weight="bold", color="white", text_align="center")),
                ft.DataColumn(ft.Text("تعديل", weight="bold", color="white", text_align="center")),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(idx+1), text_align="center", color="#1E3A8A", weight="bold")),
                        ft.DataCell(ft.Text(student["name"], text_align="center", color="#000000", weight="bold")),
                        ft.DataCell(
                            ft.TextButton(
                                text=student["student_phone"] if student["student_phone"] else "-",
                                url=f"https://wa.me/{student['student_phone'].replace('+', '')}" if student["student_phone"] else None,
                                style=ft.ButtonStyle(color="#25D366"),
                                tooltip="تواصل واتساب مع الطالب",
                                disabled=not student["student_phone"]
                            )
                        ),
                        ft.DataCell(
                            ft.TextButton(
                                text=student["parent_phone"] if student["parent_phone"] else "-",
                                url=f"https://wa.me/{student['parent_phone'].replace('+', '')}" if student["parent_phone"] else None,
                                style=ft.ButtonStyle(color="#0D6EFD"),
                                tooltip="تواصل واتساب مع ولي الأمر",
                                disabled=not student["parent_phone"]
                            )
                        ),
                        ft.DataCell(ft.Text(student["grade"] if student["grade"] else "-", text_align="center", color="#000000", weight="bold")),
                        ft.DataCell(
                            ft.Text(
                                student["payment_status"],
                                color="green" if student["payment_status"] == "دفع" else "red",
                                text_align="center",
                                weight="bold"
                            )
                        ),
                        ft.DataCell(ft.Text(str(student["tests_count"]), text_align="center", color="#000000", weight="bold")),
                        ft.DataCell(ft.Text(student["attendance"], text_align="center", color="#000000", weight="bold")),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.Icons.EDIT,
                                icon_color="#FFC107",
                                tooltip="تعديل بيانات الطالب",
                                data={"id": student["id"], "name": student["name"], "group_id": student["group_id"]},
                                on_click=on_edit_click
                            )
                        ),
                    ]
                )
                for idx, student in enumerate(students_data)
            ],
        )

        # ------------------------
        # الحاوية الكاملة مع سكرول أفقي ورأسي
        # ------------------------      
        return ft.Container(
            border=ft.border.all(2, "#FFFFFF"),
            expand=True,
            padding=20,
            # bgcolor="#0D6EFD",
            border_radius=12,
            alignment=ft.alignment.center,
            content=ft.Column(
                controls = [
                    ft.Text(
                        f"تفاصيل المجموعة: {name}",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                        color="white"
                    ),
                    ft.Divider(height=20, color="white"),

                    ft.Row([ft.Column([
                        ft.Text(group_days_text, size=18, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.RIGHT, color="white"),
                        ft.Text(group_stage_text, size=18, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.RIGHT, color="white"),
                        ft.Text(group_count_text, size=18, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.RIGHT, color="white"),
                    ])]),
                    ft.Divider(height=20, color="white"),

                    ft.Container(
                        expand=True,
                        bgcolor="#F4F4F4",
                        border_radius=10,
                        padding=10,
                        border=ft.border.all(1, "#CBD5E1"),
                        content=ft.Column(
                            expand=True,
                            scroll=ft.ScrollMode.AUTO,  # ✅ سكرول عمودي
                            controls=[
                                ft.Row(
                                    controls=[
                                        student_table
                                    ],
                                    scroll=ft.ScrollMode.AUTO,  # ✅ سكرول أفقي
                                    expand=True,
                                )
                            ]
                        )
                    )

                ],
                spacing=25,
                expand=True,   # مهم جدا
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                rtl=True
            )
        )

    def show_groups_container(page):

        def group_card(name, count):
            def on_card_click(e):
                update_side_content(group_details_container(name, page))
            return ft.Container(
                content=ft.Column([
                    ft.Text(name, size=14, weight="bold", color="black"),
                    ft.Text(f"عدد الطلاب: {count}", size=12, color="black"),
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                margin=10,
                padding=10,
                alignment=ft.alignment.center,
                bgcolor="#D9D9D9",
                height=100,
                width=160,
                border_radius=10,
                border=ft.border.all(2, "#002050"),
                ink=True,
                on_click=on_card_click
            )

        # جلب المجموعات من قاعدة البيانات
        def fetch_groups_by_stage(stage):
            with sqlite3.connect(students_db_path) as conn:
                c = conn.cursor()
                c.execute('SELECT id, name FROM groups WHERE stage=?', (stage,))
                groups = c.fetchall()
                result = []
                for group_id, name in groups:
                    c.execute('SELECT COUNT(*) FROM students WHERE group_id=?', (group_id,))
                    count = c.fetchone()[0]
                    result.append((name, count))
                return result

        primary_groups = fetch_groups_by_stage("ابتدائي")
        prep_groups = fetch_groups_by_stage("إعدادي")
        secondary_groups = fetch_groups_by_stage("ثانوي")

        def make_col(title, groups):
            return ft.Column([
                ft.Text(title, size=16, weight="bold", color="white")
            ] + [group_card(name, str(count)) for name, count in groups],
                spacing=10, scroll=ft.ScrollMode.AUTO, alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        primary_col = make_col("الابتدائي", primary_groups)
        prep_col = make_col("الإعدادي", prep_groups)
        secondary_col = make_col("الثانوي", secondary_groups)

        return ft.Container(
            border=ft.border.all(2, "#FFFFFF"),
            expand=True,
            padding=20,
            # bgcolor="#0D6EFD",
            border_radius=12,
            content=ft.Column(
                [
                    ft.Text("المجموعات", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color="white"),
                    ft.Divider(height=20, color="white"),
                    ft.Column(
                        [ft.Row([
                            primary_col, prep_col, secondary_col
                        ], alignment=ft.MainAxisAlignment.SPACE_AROUND, vertical_alignment=ft.CrossAxisAlignment.START),],
                        spacing=20,
                        scroll=ft.ScrollMode.AUTO,
                        expand=True
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=25,
                rtl=True
            )
        )
    
    card_color = "#0D6EFD"

    return ft.Row(
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Column([
                            ft.Text("إدارة المجموعات", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color="#FFFFFF"),
                            ft.Divider(height=10, color="white"),
                            ft.Row(controls=[
                                search_bar("ابحث عن المجموعة...", on_submit=lambda e: update_side_content(group_details_container(e.control.value, e.page)))
                            ], alignment="center")
                        ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Container(
                            expand=True,
                            content=ft.Column(
                                controls=[
                                    ft.Container(
                                        content=ft.Row([
                                            ft.Text("إضافة مجموعة", size=20, weight="bold", color="#ffffff"),
                                            ft.Icon(ft.Icons.GROUP_ADD, size=36, color="#ffffff")
                                        ], alignment="center", spacing=12),
                                        # bgcolor="#0D6EFD",
                                        bgcolor="#0D6EFD",
                                        border_radius=12,
                                        height=80,
                                        expand=True,
                                        margin=5,
                                        padding=5,
                                        border=ft.border.all(2, "#0044A9"),
                                        ink=True,
                                        on_click=lambda e: update_side_content(add_group_container()),
                                        alignment=ft.alignment.center
                                    ),
                                    ft.Container(
                                        content=ft.Row([
                                            ft.Text("تعديل مجموعة", size=20, weight="bold", color="#ffffff"),
                                            ft.Icon(ft.Icons.EDIT, size=36, color="#ffffff")
                                        ], alignment="center", spacing=12),
                                        # bgcolor="#FFC107",
                                        bgcolor="#3B7EFF",
                                        border_radius=12,
                                        height=80,
                                        expand=True,
                                        margin=5,
                                        padding=5,
                                        border=ft.border.all(2, "#0044A9"),
                                        ink=True,
                                        on_click=lambda e: update_side_content(edit_group_container()),
                                        alignment=ft.alignment.center
                                    ),
                                    ft.Container(
                                        content=ft.Row([
                                            ft.Text("عرض المجموعات", size=20, weight="bold", color="#ffffff"),
                                            ft.Icon(ft.Icons.REMOVE_RED_EYE_SHARP, size=36, color="#ffffff")
                                        ], alignment="center", spacing=12),
                                        # bgcolor="#949494",
                                        bgcolor="#6196FF",
                                        border_radius=12,
                                        height=80,
                                        expand=True,
                                        margin=5,
                                        padding=5,
                                        border=ft.border.all(2, "#0044A9"),
                                        ink=True,
                                        on_click=lambda e:update_side_content(show_groups_container(e.page)),
                                        alignment=ft.alignment.center
                                    )
                                ],
                                spacing=20,
                                expand=True,
                                alignment=ft.MainAxisAlignment.START,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                scroll=ft.ScrollMode.AUTO
                            )
                        )
                    ],
                    expand=True,
                    alignment=ft.MainAxisAlignment.START,
                    spacing=20
                ),
                margin=ft.margin.only(left=10, right=10, top=10, bottom=10),
                padding=10,
                alignment=ft.alignment.center,
                bgcolor="#94BFFF",
                border_radius=10,
                expand=1,
            ),
            side_rec_container_grp
        ],
        expand=True
    )
 