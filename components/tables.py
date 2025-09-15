import flet as ft
import sqlite3
import asyncio
import threading
from datetime import datetime
from utils.database import students_db_path
from utils.helpers import show_error_dialog
from utils.date_utils import normalize_date_format


class PaymentTable(ft.Column):
    MONTHS_AR = [
        "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
        "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
    ]

    def __init__(self, data: list[list[str]], page: ft.Page):
        super().__init__()
        self.data = data
        self.page = page
        self.rows = []
        self.expand = True
        self.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
        self.alignment = ft.MainAxisAlignment.START
        self.selected_month = None  # لتخزين الشهر المختار (سيكون بتنسيق YYYY-MM)

        self.table = ft.DataTable(
            expand=True,
            column_spacing=50,
            data_row_min_height=50,
            heading_row_color="#1E3A8A",
            data_row_color={"odd": "#F3F4F6", "even": "#FFFFFF"},
            border=ft.border.all(1, "#1E3A8A"),
            divider_thickness=1,
            columns=[
                ft.DataColumn(ft.Text("#", weight="bold", color="white", text_align="center"), tooltip="الترقيم"),
                ft.DataColumn(ft.Text("الكود", weight="bold", color="white", text_align="center"), tooltip="كود الطالب"),
                ft.DataColumn(ft.Text("الاسم", weight="bold", color="white", text_align="center"), tooltip="اسم الطالب"),
                ft.DataColumn(ft.Text("حالة الدفع", weight="bold", color="white", text_align="center"), tooltip="حالة دفع الطالب"),
                ft.DataColumn(ft.Text("الشهر", weight="bold", color="white", text_align="center"), tooltip="شهر الدفع"),
            ],
            rows=self.rows
        )

        self.controls = [
            ft.Container(
                expand=True,
                bgcolor="#F4F4F4",
                border_radius=10,
                padding=10,
                border=ft.border.all(1, "#CBD5E1"),
                content=ft.ListView(controls=[self.table], expand=True, auto_scroll=False)
            )
        ]

    @classmethod
    def get_current_month(cls):
        return datetime.now().strftime('%Y-%m')  # تنسيق ثابت YYYY-MM

    @classmethod
    def arabic_month_to_numeric(cls, arabic_month, year=None):
        if year is None:
            year = datetime.now().strftime('%Y')
        try:
            month_idx = cls.MONTHS_AR.index(arabic_month) + 1
            return f"{year}-{month_idx:02d}"
        except ValueError:
            return cls.get_current_month()

    @classmethod
    def numeric_month_to_arabic(cls, numeric_month):
        try:
            month_idx = int(numeric_month.split('-')[1])
            return cls.MONTHS_AR[month_idx - 1]
        except:
            return cls.MONTHS_AR[int(datetime.now().strftime('%m')) - 1]

    def did_mount(self):
        self.load_data()

    def load_data(self):
        self.rows.clear()
        current_month = self.selected_month if self.selected_month else self.get_current_month()  # YYYY-MM
        conn = None

        try:
            conn = sqlite3.connect(students_db_path)
            c = conn.cursor()

            for index, row in enumerate(self.data):
                name = row[0]  # الاسم
                code = row[1]  # الكود
                status = "لم يدفع"  # الحالة الافتراضية

                c.execute('''SELECT id FROM students 
                           WHERE first_name || " " || father_name || " " || family_name = ?''', (name,))
                student = c.fetchone()

                if student:
                    c.execute('''SELECT status FROM payments 
                               WHERE student_id = ? AND month = ?
                               ORDER BY payment_date DESC LIMIT 1''', (student[0], current_month))
                    payment = c.fetchone()
                    if payment:
                        status = payment[0]

                if len(row) >= 3:
                    row[2] = status
                else:
                    row.append(status)

                if len(row) >= 4:
                    row[3] = self.numeric_month_to_arabic(current_month)
                else:
                    row.append(self.numeric_month_to_arabic(current_month))

                color = "green" if status.strip() == "دفع" else "red"

                self.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(index+1), text_align="center", weight="bold", color="#1E3A8A")),
                            ft.DataCell(ft.Text(str(code), text_align="center", weight="bold", color="#000000")),
                            ft.DataCell(
                                ft.Text(name, text_align="center", weight="bold", color="#000000"),
                                on_tap=lambda e, idx=index, n=name: self.show_edit_dialog(idx, n, status, current_month)
                            ),
                            ft.DataCell(ft.Text(status, color=color, text_align="center", weight="bold")),
                            ft.DataCell(ft.Text(self.numeric_month_to_arabic(current_month), text_align="center", weight="bold", color="#000000"))
                        ]
                    )
                )

        except Exception as e:
            show_error_dialog(self.page, f"خطأ في تحميل البيانات: {str(e)}")
        finally:
            if conn:
                conn.close()

        self.table.rows = self.rows
        self.update()

    def show_edit_dialog(self, index, name, current_status, current_month):
        status_dropdown = ft.Dropdown(
            label="حالة الدفع",
            value=current_status,
            options=[
                ft.dropdown.Option("دفع"),
                ft.dropdown.Option("لم يدفع"),
            ],
            text_align=ft.TextAlign.RIGHT,
            expand=True
        )

        month_dropdown = ft.Dropdown(
            label="الشهر",
            value=self.numeric_month_to_arabic(current_month),
            options=[ft.dropdown.Option(month) for month in self.MONTHS_AR],
            expand=True
        )

        edit_dialog = ft.AlertDialog(
            title=ft.Text(f"تعديل حالة الدفع لـ {name}", text_align=ft.TextAlign.RIGHT),
            content=ft.Column(
                controls=[status_dropdown, month_dropdown],
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            actions=[
                ft.TextButton("حفظ", on_click=lambda e: self._sync_save_payment_status(index, status_dropdown.value, month_dropdown.value, edit_dialog)),
                ft.TextButton("إلغاء", on_click=lambda e: self.page.close(edit_dialog))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        self.page.open(edit_dialog)

    def get_or_create_eventloop(self):
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def _sync_save_payment_status(self, index, new_status, new_month_ar, dialog):
        try:
            loop = self.get_or_create_eventloop()
            loop.run_until_complete(self._async_save_payment_status(index, new_status, new_month_ar, dialog))
        except Exception as e:
            show_error_dialog(self.page, f"خطأ في حفظ حالة الدفع: {str(e)}")
        finally:
            self.page.close(dialog)

    async def _async_save_payment_status(self, index, new_status, new_month_ar, dialog):
        conn = None
        try:
            new_month = self.arabic_month_to_numeric(new_month_ar)
            conn = sqlite3.connect(students_db_path)
            c = conn.cursor()
            name = self.data[index][0]

            c.execute('SELECT id, first_name || " " || father_name || " " || family_name, guardian_chat_id FROM students WHERE first_name || " " || father_name || " " || family_name = ?', (name,))
            student = c.fetchone()

            if student:
                student_id, student_name, guardian_chat_id = student
                c.execute('SELECT id, status FROM payments WHERE student_id=? AND month=?', (student_id, new_month))
                payment = c.fetchone()

                payment_date = normalize_date_format(datetime.now().strftime('%Y-%m-%d')) if new_status == "دفع" else ""

                if payment:
                    if payment[1] != new_status:
                        print(f"🔄 تحديث حالة الطالب {student_name} من {payment[1]} إلى {new_status}")
                        c.execute('UPDATE payments SET status=?, payment_date=? WHERE id=?', 
                                  (new_status, payment_date, payment[0]))
                    else:
                        print(f"⏭️ الطالب {student_name} حالته بالفعل {new_status} → تجاهل")
                else:
                    print(f"🆕 إدراج حالة جديدة للطالب {student_name} -> {new_status}")
                    c.execute('INSERT INTO payments (student_id, month, status, payment_date) VALUES (?, ?, ?, ?)', 
                              (student_id, new_month, new_status, payment_date))

                conn.commit()

                # تحديث البيانات المحلية
                self.data[index][2] = new_status
                self.data[index][3] = self.numeric_month_to_arabic(new_month)
                self.selected_month = new_month
                self.load_data()

                # إرسال إشعار
                if guardian_chat_id and guardian_chat_id != "None":
                    from utils.telegram_bot import send_telegram_message
                    message = f"💰 تحديث حالة الدفع\n"
                    message += f"الطالب: {student_name}\n"
                    message += f"الشهر: {new_month_ar}\n"
                    message += f"التاريخ: {payment_date}\n"
                    message += f"الحالة: {new_status}\n"
                    success, error_msg = await send_telegram_message(guardian_chat_id, message)
                    if success:
                        print(f"📨 تم إرسال إشعار لولي أمر {student_name}")
                    else:
                        print(f"❌ فشل إرسال الإشعار لولي أمر {student_name}: {error_msg}")
                        show_error_dialog(self.page, f"فشل إرسال الإشعار لولي أمر {student_name}: {error_msg}")
                else:
                    print(f"⚠️ لا يوجد guardian_chat_id صالح للطالب {student_name}")
                    show_error_dialog(self.page, f"لا يوجد guardian_chat_id صالح للطالب {student_name}")

            else:
                show_error_dialog(self.page, "لم يتم العثور على الطالب")

        except Exception as e:
            show_error_dialog(self.page, f"خطأ في حفظ حالة الدفع: {str(e)}")

        finally:
            if 'conn' in locals():
                conn.close()
            self.page.close(dialog)

    def refresh(self, new_data):
        self.data = new_data
        self.load_data()

class AttendanceTable(ft.Column):
    def __init__(self, data: list[list[str]], page: ft.Page):
        super().__init__()
        self.data = data
        self.page = page
        self.rows = []
        self.expand = True  # Ensure AttendanceTable fills available space
        self.horizontal_alignment = ft.CrossAxisAlignment.STRETCH  # Stretch children horizontally
        self.alignment = ft.MainAxisAlignment.START  # Align content to start vertically

        # الجدول مع نفس ألوان وشكل PaymentTable
        self.table = ft.DataTable(
            expand=True,
            column_spacing=50,
            data_row_min_height=50,
            heading_row_color="#1E3A8A",
            data_row_color={"odd": "#F3F4F6", "even": "#FFFFFF"},
            border=ft.border.all(1, "#1E3A8A"),
            divider_thickness=1,
            columns=[
                ft.DataColumn(
                    ft.Text("#", weight="bold", color="white", text_align="center"),
                    tooltip="الترقيم"
                ),
                ft.DataColumn(
                    ft.Text("الكود", weight="bold", color="white", text_align="center"),
                    tooltip="كود الطالب"
                ),
                ft.DataColumn(
                    ft.Text("الاسم", weight="bold", color="white", text_align="center"),
                    tooltip="اسم الطالب"
                ),
                ft.DataColumn(
                    ft.Text("اخر حصة", weight="bold", color="white", text_align="center"),
                    tooltip="حالة الحضور في الحصة السابقة"
                ),
                ft.DataColumn(
                    ft.Text("حاضر", weight="bold", color="white", text_align="center"),
                    tooltip="حالة الحضور الحالية"
                ),
            ],
            rows=self.rows
        )

        # حاوية الجدول مع ListView لتفاعلية مشابهة لـ PaymentTable
        self.controls = [
            ft.Container(
                expand=True,
                bgcolor="#F4F4F4",  # Match PaymentTable container background
                border_radius=10,  # Match PaymentTable border radius
                padding=10,  # Match PaymentTable padding
                border=ft.border.all(1, "#CBD5E1"),  # Match PaymentTable border
                content=ft.ListView(
                    controls=[self.table],
                    expand=True,
                    auto_scroll=False
                )
            )
        ]

    def did_mount(self):
        self.load_data()

    def load_data(self):
        self.rows.clear()
        for index, row in enumerate(self.data):
            # Expect row = [name, code, last_status, current_status]
            if len(row) == 4:
                name, code, last_status, current_status = row
            else:
                name = row[0] if len(row) > 0 else ""
                code = row[1] if len(row) > 1 else ""
                last_status = row[2] if len(row) > 2 else "غير محدد"
                current_status = row[3] if len(row) > 3 else "غير محدد"
            last_color = self.get_status_color(last_status)
            current_color = self.get_status_color(current_status)
            self.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Text(str(index+1), text_align="center", weight="bold", color="#1E3A8A")
                        ),
                        ft.DataCell(
                            ft.Text(str(code), text_align="center", weight="bold", color="#000000")
                        ),
                        ft.DataCell(
                            ft.Text(name, text_align="center", weight="bold", color="#000000"),
                            on_tap=lambda e, idx=index, n=name: self.show_edit_dialog(idx, n, current_status)
                        ),
                        ft.DataCell(
                            ft.Text(last_status, color=last_color, text_align="center", weight="bold")
                        ),
                        ft.DataCell(
                            ft.Text(current_status, color=current_color, text_align="center", weight="bold")
                        ),
                    ]
                )
            )
        self.table.rows = self.rows
        self.update()

    def get_status_color(self, status):
        status = status.strip()
        if status == "حاضر":
            return ft.Colors.GREEN_700
        elif status == "غائب":
            return ft.Colors.RED_700
        elif status == "معتذر":
            return ft.Colors.ORANGE_700
        elif status == "-":
            return ft.Colors.GREY_500
        else:
            return ft.Colors.GREY_700  # للحالة "غير محدد"

    def show_edit_dialog(self, index, name, current_status):
        status_dropdown = ft.Dropdown(
            label="حالة الحضور الحالي",
            value=current_status,
            options=[
                ft.dropdown.Option("حاضر"),
                ft.dropdown.Option("غائب"),
                ft.dropdown.Option("معتذر"),
            ],
            text_align=ft.TextAlign.RIGHT,
            expand=True
        )
        edit_dialog = ft.AlertDialog(
            title=ft.Text(f"تعديل حالة الحضور لـ {name}", text_align=ft.TextAlign.RIGHT),
            content=ft.Column(
                controls=[status_dropdown],
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            actions=[
                ft.TextButton("حفظ", on_click=lambda e: self.save_attendance_status(index, status_dropdown.value, edit_dialog)),
                ft.TextButton("إلغاء", on_click=lambda e: self.page.close(edit_dialog))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        self.page.open(edit_dialog)

    def save_attendance_status(self, index, new_status, dialog):
        # تحديث البيانات المحلية
        student_name = self.data[index][0]  # اسم الطالب
        student_code = self.data[index][1]  # كود الطالب
        
        # تحديث الحالة في البيانات المحلية
        self.data[index][3] = new_status
        
        # تحديث الجدول مباشرة
        self.load_data()
        self.page.close(dialog)
        self.page.update()

    def refresh(self, new_data):
        self.data = new_data
        self.load_data()
 


class ExamTable(ft.Column):
    def __init__(self, data: list[list], page: ft.Page, students_db_path: str):
        super().__init__()
        self.data = data
        self.page = page
        self.students_db_path = students_db_path
        self.rows = []
        self.expand = True
        self.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
        self.alignment = ft.MainAxisAlignment.START

        self.table = ft.DataTable(
            expand=True,
            column_spacing=50,
            data_row_min_height=50,
            heading_row_color="#1E3A8A",
            data_row_color={"odd": "#F3F4F6", "even": "#FFFFFF"},
            border=ft.border.all(1, "#1E3A8A"),
            divider_thickness=1,
            columns=[
                ft.DataColumn(ft.Text("#", weight="bold", color="white", text_align="center"), tooltip="الترقيم"),
                ft.DataColumn(ft.Text("الكود", weight="bold", color="white", text_align="center"), tooltip="كود الطالب"),
                ft.DataColumn(
                    ft.Text("الاسم", weight="bold", color="white", text_align="center"),
                    tooltip="اسم الطالب"
                ),
                ft.DataColumn(
                    ft.Text("آخر درجة", weight="bold", color="white", text_align="center"),
                    tooltip="آخر درجة حصل عليها الطالب"
                ),
                ft.DataColumn(
                    ft.Text("عدد الاختبارات", weight="bold", color="white", text_align="center"),
                    tooltip="عدد الاختبارات التي أداها الطالب"
                ),
            ],
            rows=self.rows
        )

        self.controls = [
            ft.Container(
                expand=True,
                bgcolor="#F4F4F4",
                border_radius=10,
                padding=10,
                border=ft.border.all(1, "#CBD5E1"),
                content=ft.ListView(
                    controls=[self.table],
                    expand=True,
                    auto_scroll=False
                )
            )
        ]

    def did_mount(self):
        self.load_data()

    def load_data(self):
        self.rows.clear()
        for index, (student_code, name, last_grade, num_exams) in enumerate(self.data):
            color = self.get_grade_color(last_grade)
            self.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(index+1), text_align="center", weight="bold", color="#1E3A8A")),
                        ft.DataCell(ft.Text(str(student_code), text_align="center", weight="bold", color="#000000")),
                        ft.DataCell(
                            ft.Text(name, text_align="center", weight="bold", color="#000000"),
                            on_tap=lambda e, idx=index, n=name: self.show_add_exam_dialog(idx, n)
                        ),
                        ft.DataCell(ft.Text(last_grade, color=color, text_align="center", weight="bold")),
                        ft.DataCell(ft.Text(str(num_exams), text_align="center", weight="bold", color="#000000")),
                    ]
                )
            )
        self.table.rows = self.rows
        self.update()

    def get_grade_color(self, grade):
        if grade == "غير متوفر":
            return "gray"
        try:
            student_grade, total_grade = map(int, grade.split('/'))
            return "red" if student_grade < total_grade / 2 else "green"
        except ValueError:
            return "gray"

    def get_or_create_eventloop(self):
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def show_add_exam_dialog(self, index, name):
        student_grade = ft.TextField(label="درجة الطالب", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.RIGHT)
        total_grade = ft.TextField(label="الدرجة النهائية", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.RIGHT)
        add_dialog = ft.AlertDialog(
            title=ft.Text(f"تسجيل درجة اختبار جديد لـ {name}", text_align=ft.TextAlign.RIGHT),
            content=ft.Column(
                controls=[student_grade, total_grade],
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            actions=[
                ft.TextButton("حفظ", on_click=lambda e: self._handle_save_exam(index, student_grade.value, total_grade.value, add_dialog)),
                ft.TextButton("إلغاء", on_click=lambda e: self.page.close(add_dialog))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        self.page.open(add_dialog)

    def _handle_save_exam(self, index, student_grade, total_grade, dialog):
        if not student_grade or not total_grade:
            show_error_dialog(self.page, "يرجى ملء الحقول")
            self.page.close(dialog)
            return
        
        try:
            student_g = int(student_grade)
            total_g = int(total_grade)
            if not (0 <= student_g <= total_g):
                show_error_dialog(self.page, "درجة الطالب يجب أن تكون بين 0 والدرجة النهائية")
                self.page.close(dialog)
                return
        except ValueError:
            show_error_dialog(self.page, "يرجى إدخال أرقام صحيحة")
            self.page.close(dialog)
            return

        def async_callback():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(self._async_save_exam_grade(index, student_grade, total_grade, dialog))
                if success:
                    self.page.close(dialog)
            except Exception as e:
                print(f"❌ خطأ في حفظ درجة الامتحان: {str(e)}")
                show_error_dialog(self.page, f"خطأ في حفظ درجة الامتحان: {str(e)}")
                self.page.close(dialog)
            finally:
                loop.close()

        # تشغيل العملية في خيط منفصل
        threading.Thread(target=async_callback).start()

    async def _async_save_exam_grade(self, index, student_grade, total_grade, dialog):
        if not student_grade or not total_grade:
            show_error_dialog(self.page, "يرجى ملء الحقول")
            self.page.close(dialog)
            return
        
        try:
            student_g = int(student_grade)
            total_g = int(total_grade)
            if not (0 <= student_g <= total_g):
                show_error_dialog(self.page, "درجة الطالب يجب أن تكون بين 0 والدرجة النهائية")
                self.page.close(dialog)
                return
        except ValueError:
            show_error_dialog(self.page, "يرجى إدخال أرقام صحيحة")
            self.page.close(dialog)
            return

        try:
            # Note: Removed recursive call that was causing infinite loop
            student_g = int(student_grade)
            total_g = int(total_grade)
            new_grade_str = f"{student_g}/{total_g}"
            print(f"🆕 جاري تسجيل درجة جديدة للطالب {self.data[index][1]}: {new_grade_str}")

            conn = sqlite3.connect(self.students_db_path)
            c = conn.cursor()
            student_code = self.data[index][0]

            c.execute('SELECT id, guardian_chat_id FROM students WHERE code = ?', (student_code,))
            student = c.fetchone()
            if student:
                student_id, guardian_chat_id = student
                today = datetime.now().strftime('%Y-%m-%d')
                c.execute('''INSERT INTO exams (student_id, exam_date, total_score, student_score) VALUES (?, ?, ?, ?)''',
                          (student_id, today, total_g, student_g))
                conn.commit()

                c.execute('''SELECT 
                            (SELECT student_score || '/' || total_score FROM exams WHERE student_id = ? ORDER BY date(exam_date) DESC, id DESC LIMIT 1) as last_grade,
                            (SELECT COUNT(*) FROM exams WHERE student_id = ?) as num_exams''', 
                        (student_id, student_id))
                last_grade, num_exams = c.fetchone()
                
                self.data[index][2] = last_grade if last_grade else "غير متوفر"
                self.data[index][3] = num_exams
                
                if guardian_chat_id and guardian_chat_id != "None":
                    from utils.telegram_bot import send_telegram_message
                    message = f"📝 تحديث درجة الامتحان\n"
                    message += f"الطالب: {self.data[index][1]}\n"
                    message += f"الدرجة: {new_grade_str}\n"
                    message += f"التاريخ: {today}\n"
                    success, error_msg = await send_telegram_message(guardian_chat_id, message)
                    if not success:
                        c.execute('''INSERT INTO pending_notifications (chat_id, message, created_at) VALUES (?, ?, ?)''',
                                  (guardian_chat_id, message, today))
                        conn.commit()
                
                self.load_data()
                self.page.update()
                return True
            else:
                show_error_dialog(self.page, "لم يتم العثور على الطالب")
                return False

        except Exception as e:
            print(f"❌ خطأ في حفظ درجة الامتحان: {str(e)}")
            show_error_dialog(self.page, f"خطأ في حفظ درجة الامتحان: {str(e)}")
            return False
        finally:
            if 'conn' in locals() and conn:
                conn.close()
            self.page.close(dialog)

    async def _async_save_exam_grade(self, index, student_grade, total_grade, dialog):
        """تحديث درجة الامتحان للطالب"""
        try:
            student_g = int(student_grade)
            total_g = int(total_grade)
            new_grade_str = f"{student_g}/{total_g}"
            print(f"🆕 جاري تسجيل درجة جديدة للطالب {self.data[index][1]}: {new_grade_str}")

            conn = sqlite3.connect(self.students_db_path)
            c = conn.cursor()
            student_code = self.data[index][0]

            c.execute('SELECT id, guardian_chat_id FROM students WHERE code = ?', (student_code,))
            student = c.fetchone()
            if student:
                student_id, guardian_chat_id = student
                today = datetime.now().strftime('%Y-%m-%d')
                c.execute('''INSERT INTO exams (student_id, exam_date, total_score, student_score) VALUES (?, ?, ?, ?)''',
                          (student_id, today, total_g, student_g))
                conn.commit()

                c.execute('''SELECT 
                            (SELECT student_score || '/' || total_score FROM exams WHERE student_id = ? ORDER BY date(exam_date) DESC, id DESC LIMIT 1) as last_grade,
                            (SELECT COUNT(*) FROM exams WHERE student_id = ?) as num_exams''', 
                        (student_id, student_id))
                last_grade, num_exams = c.fetchone()
                
                self.data[index][2] = last_grade if last_grade else "غير متوفر"
                self.data[index][3] = num_exams
                print(f"🔄 تم تحديث بيانات الطالب {self.data[index][1]}: آخر درجة = {self.data[index][2]}, عدد الاختبارات = {self.data[index][3]}")

                if guardian_chat_id and guardian_chat_id != "None":
                    from utils.telegram_bot import send_telegram_message
                    message = f"📝 تحديث درجة الامتحان\n"
                    message += f"الطالب: {self.data[index][1]}\n"
                    message += f"الدرجة: {new_grade_str}\n"
                    message += f"التاريخ: {today}\n"
                    success, error_msg = await send_telegram_message(guardian_chat_id, message)
                    if success:
                        print(f"📨 تم إرسال إشعار لولي أمر {self.data[index][1]}")
                    else:
                        print(f"❌ فشل إرسال الإشعار لولي أمر {self.data[index][1]}: {error_msg}")
                        c.execute('''INSERT INTO pending_notifications (chat_id, message, created_at) VALUES (?, ?, ?)''',
                                  (guardian_chat_id, message, today))
                        conn.commit()
                        print(f"📥 تم حفظ الإشعار المؤجل للطالب {self.data[index][1]}")
                        show_error_dialog(self.page, f"فشل إرسال الإشعار لولي أمر {self.data[index][1]} بسبب انقطاع الإنترنت. سيتم إعادة المحاولة لاحقاً.")
                else:
                    print(f"⚠️ لا يوجد guardian_chat_id صالح للطالب {self.data[index][1]}")
                    show_error_dialog(self.page, f"لا يوجد guardian_chat_id صالح للطالب {self.data[index][1]}")
                
                self.load_data()
                self.page.update()
                return True
            else:
                print(f"⚠️ لم يتم العثور على الطالب بكود {student_code}")
                show_error_dialog(self.page, "لم يتم العثور على الطالب")
                return False

        except ValueError:
            print(f"❌ خطأ في إدخال الأرقام للطالب {self.data[index][1]}: درجة الطالب = {student_grade}, الدرجة النهائية = {total_grade}")
            show_error_dialog(self.page, "يرجى إدخال أرقام صحيحة")
            return False
        except Exception as e:
            print(f"❌ خطأ غير متوقع: {str(e)}")
            show_error_dialog(self.page, f"حدث خطأ غير متوقع: {str(e)}")
            return False
        finally:
            if 'conn' in locals() and conn:
                conn.close()

    def refresh(self, new_data):
        self.data = new_data
        self.load_data()

