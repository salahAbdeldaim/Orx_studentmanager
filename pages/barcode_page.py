import flet as ft
import sqlite3
import os
import platform
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

try:
    import win32print
    import win32api
except ImportError:
    win32print = None
    win32api = None

# استيراد من الوحدات الأخرى في المشروع
from utils.database import students_db_path
from utils.helpers import show_error_dialog, show_success_dialog, search_bar, get_groups, extract_unique_code

def barcode_page(page):
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

    def displaying_students_container(page):
        filter_level = {"value": None}
        filter_search = {"value": ""}
        filter_group = {"value": None}

        def fetch_students(filter_level, filter_search, filter_group):
            try:
                with sqlite3.connect(students_db_path) as conn:
                    c = conn.cursor()
                    query = '''SELECT s.id, s.code, s.first_name, s.father_name, s.family_name, s.barcode_path FROM students s'''
                    params = []
                    where = []

                    if filter_level["value"]:
                        where.append("s.grade = ?")
                        params.append(filter_level["value"])

                    if filter_group["value"]:
                        where.append("s.group_id = ?")
                        params.append(filter_group["value"])

                    if filter_search["value"]:
                        search_val = filter_search["value"].strip()
                        if search_val.isdigit():
                            filtered_code = extract_unique_code(search_val)
                            if filtered_code:
                                where.append("CAST(s.code AS TEXT) LIKE ?")
                                params.append(f"%{filtered_code}%")
                            else:
                                search_val = search_val[-4:]
                                where.append("CAST(s.code AS TEXT) LIKE ?")
                                params.append(f"%{search_val}%")
                        else:
                            val = f"%{search_val}%"
                            where.append("(s.first_name LIKE ? OR s.father_name LIKE ? OR s.family_name LIKE ? OR CAST(s.code AS TEXT) LIKE ?)")
                            params += [val, val, val, val]

                    if where:
                        query += " WHERE " + " AND ".join(where)

                    query += " ORDER BY s.first_name, s.father_name, s.family_name"
                    c.execute(query, params)
                    students = c.fetchall()
                    result = []
                    for s in students:
                        student_id, code, first_name, father_name, family_name, barcode_path = s
                        full_name = f"{first_name} {father_name} {family_name}"
                        result.append({
                            "id": student_id,
                            "code": code,
                            "name": full_name,
                            "barcode_path": barcode_path
                        })
                    return result
            except Exception as e:
                show_error_dialog(page, f"خطأ في جلب الطلاب: {e}")
                return []

        def show_barcode_dialog(student):
            barcode_path = student["barcode_path"]
            student_name = student["name"]
            img = ft.Image(src=barcode_path, width=400, height=180, fit=ft.ImageFit.CONTAIN) if barcode_path else ft.Text("لا يوجد باركود", color="red")

            def on_export_click(e):
                file_picker = ft.FilePicker()
                def on_result(fp_event):
                    if fp_event.path:
                        try:
                            import shutil
                            shutil.copy(barcode_path, fp_event.path)
                            show_success_dialog(page, f"تم حفظ الصورة في {fp_event.path}")
                        except Exception as ex:
                            show_error_dialog(page, f"خطأ في حفظ الصورة: {ex}")
                file_picker.on_result = on_result
                page.overlay.append(file_picker)
                page.update()
                file_picker.save_file(
                    dialog_title="اختر مكان حفظ صورة الباركود",
                    file_name=f"barcode_{student['code']}.png",
                    allowed_extensions=["png"]
                )

            def on_export_pdf(e):
                file_picker = ft.FilePicker()
                def on_result(fp_event):
                    if fp_event.path:
                        try:
                            c = canvas.Canvas(fp_event.path, pagesize=A4)
                            c.setFont("Helvetica-Bold", 14)
                            c.drawImage(barcode_path, 150, 600, width=300, height=120)
                            c.save()
                            show_success_dialog(page, f"تم حفظ PDF في {fp_event.path}")
                        except Exception as ex:
                            show_error_dialog(page, f"خطأ في إنشاء PDF: {ex}")
                file_picker.on_result = on_result
                page.overlay.append(file_picker)
                page.update()
                file_picker.save_file(
                    dialog_title="اختر مكان حفظ ملف PDF",
                    file_name=f"barcode_{student['code']}.pdf",
                    allowed_extensions=["pdf"]
                )

            def on_print_click(e):
                try:
                    if platform.system() == "Windows" and win32print and win32api:
                        printer_name = win32print.GetDefaultPrinter()
                        win32api.ShellExecute(
                            0, "print", barcode_path, f'"{printer_name}"', ".", 0
                        )
                        show_success_dialog(page, f"تم إرسال الباركود للطابعة {printer_name}")
                    else:
                        show_error_dialog(page, "خاصية الطباعة المباشرة مدعومة حاليًا على Windows فقط")
                except Exception as ex:
                    show_error_dialog(page, f"خطأ أثناء الطباعة: {ex}")

            dlg = ft.AlertDialog(
                bgcolor="#0D6EFD",
                title=ft.Text(
                    f"باركود الطالب: {student_name}",
                    text_align=ft.TextAlign.CENTER,
                    size=18,
                    weight=ft.FontWeight.BOLD,
                ),
                content=ft.Container(
                    width=350,
                    height=500,
                    bgcolor="#FFFFFF",
                    border_radius=15,
                    padding=20,
                    content=ft.Column(
                        [
                            img,
                            ft.Divider(height=10),
                            ft.ElevatedButton("تصدير كـ PNG", icon=ft.Icons.DOWNLOAD, on_click=on_export_click, bgcolor="#0059DF", color="white", height=45),
                            ft.ElevatedButton("تصدير كـ PDF", icon=ft.Icons.PICTURE_AS_PDF, on_click=on_export_pdf, bgcolor="#28A745", color="white", height=45),
                            ft.ElevatedButton("طباعة", icon=ft.Icons.PRINT, on_click=on_print_click, bgcolor="#DC3545", color="white", height=45),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=20,
                    ),
                ),
                actions=[
                    ft.TextButton(
                        "إغلاق",
                        on_click=lambda e: (setattr(dlg, "open", False), page.update())
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.CENTER,
            )

            if dlg not in page.overlay:
                page.overlay.append(dlg)
            dlg.open = True
            page.update()

        def refresh_table():
            try:
                students_data = fetch_students(filter_level, filter_search, filter_group)
                if not students_data:
                    student_table.rows = [
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text("اختر مستوى أو مجموعة أو ابحث لعرض الطلاب", text_align="center", color="red", weight="bold")),
                                ft.DataCell(ft.Text("")),
                                ft.DataCell(ft.Text("")),
                                ft.DataCell(ft.Text(""))
                            ]
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
                                        on_click=lambda e, student=s: show_barcode_dialog(student),
                                        style=ft.ButtonStyle(color="#0059DF"),
                                        tooltip="عرض الباركود"
                                    )
                                ),
                                ft.DataCell(
                                    ft.Image(src=s["barcode_path"] if s["barcode_path"] else None, width=120, height=40, fit=ft.ImageFit.CONTAIN)
                                    if s["barcode_path"] else ft.Text("لا يوجد باركود", text_align="center", color="red")
                                ),
                            ]
                        )
                        for idx, s in enumerate(students_data)
                    ]
                page.update()
            except Exception as e:
                show_error_dialog(page, f"حدث خطأ أثناء جلب الطلاب: {e}")

        def on_search_submit(e=None):
            try:
                filter_search["value"] = e.control.value.strip() if e and e.control else ""
                refresh_table()
            except Exception as e:
                show_error_dialog(page, f"خطأ في البحث: {e}")

        def on_level_change(e):
            try:
                filter_level["value"] = std_level.value
                refresh_table()
            except Exception as e:
                show_error_dialog(page, f"خطأ في فلترة المرحلة: {e}")

        def on_group_change(e):
            try:
                filter_group["value"] = std_group.value
                refresh_table()
            except Exception as e:
                show_error_dialog(page, f"خطأ في فلترة المجموعة: {e}")

        std_group = ft.Dropdown(
            label="المجموعة",
            hint_text="اختر مجموعة",
            options=get_groups(),
            expand=True,
            on_change=on_group_change
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
                ft.DataColumn(ft.Text("الباركود", weight="bold", color="white", text_align="center")),
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
                                std_level,
                                std_group
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

    def PDF_export_container(page):
        selected_group = {"value": None}
        students_count_text = ft.Text("", size=16, color="yellow", weight="bold")

        def export_pdf_for_group(group_id, group_name):
            try:
                with sqlite3.connect(students_db_path) as conn:
                    c = conn.cursor()
                    c.execute("""
                        SELECT s.code, s.first_name, s.father_name, s.family_name, s.barcode_path 
                        FROM students s 
                        WHERE s.group_id = ? AND s.barcode_path IS NOT NULL
                        ORDER BY s.first_name, s.father_name, s.family_name
                    """, (group_id,))
                    students = c.fetchall()

                    if not students:
                        show_error_dialog(page, f"لا يوجد طلاب لديهم باركود في المجموعة: {group_name}")
                        return

                    file_picker = ft.FilePicker()
                    def on_result(fp_event):
                        num_rows = int(number_of_row.value) if number_of_row.value else 6
                        num_columns = int(number_of_col.value) if number_of_col.value else 3

                        if fp_event.path:
                            try:
                                cpdf = canvas.Canvas(fp_event.path, pagesize=A4)
                                page_width, page_height = A4

                                # ---------------- إعدادات التخطيط المحسنة ----------------
                                margin_x = 40
                                margin_y = 40
                                base_barcode_width = 150  # العرض الأساسي
                                base_col_gap = 30  # مسافة أصغر لتوفير المساحة
                                barcode_height = 80
                                row_gap = 50

                                # حساب العرض المتاح وتعديل barcode_width ديناميكيًا
                                available_width = page_width - 2 * margin_x
                                required_width = num_columns * base_barcode_width + (num_columns - 1) * base_col_gap
                                if required_width > available_width:
                                    # تقليل العرض ليتناسب
                                    barcode_width = max(80, (available_width - (num_columns - 1) * base_col_gap) / num_columns)
                                    col_gap = base_col_gap
                                    print(f"تم تعديل العرض: {barcode_width:.1f} (لـ {num_columns} أعمدة)")  # للاختبار، أزل بعد
                                else:
                                    barcode_width = base_barcode_width
                                    col_gap = base_col_gap

                                x_positions = [margin_x + col * (barcode_width + col_gap) for col in range(num_columns)]
                                y_start = page_height - margin_y - barcode_height
                                row_height = barcode_height + row_gap
                                row_count = 0

                                print(f"عدد الأعمدة: {num_columns}, مواقع X: {x_positions}")  # للاختبار، أزل بعد

                                # ---------------- إدراج الباركودات ----------------
                                for idx, (code, fn, father, family, barcode_path) in enumerate(students):
                                    if os.path.exists(barcode_path):
                                        # رسم الباركود num_columns مرات (تكرار لكل طالب)
                                        for col in range(num_columns):
                                            x = x_positions[col]
                                            y = y_start - (row_count * row_height)
                                            cpdf.drawImage(barcode_path, x, y, width=barcode_width, height=barcode_height)
                                            print(f"رسم باركود طالب {code} في العمود {col}: x={x:.1f}, y={y:.1f}")  # للاختبار

                                    # الانتقال إلى الصف التالي بعد كل طالب
                                    row_count += 1

                                    # صفحة جديدة إذا وصلنا num_rows
                                    if row_count == num_rows:
                                        cpdf.showPage()
                                        row_count = 0

                                cpdf.save()
                                show_success_dialog(page, f"تم تصدير باركودات {len(students)} طالب إلى PDF (مع {num_columns} تكرارات لكل طالب)")
                            except Exception as ex:
                                show_error_dialog(page, f"خطأ أثناء إنشاء PDF: {ex}")
                    file_picker.on_result = on_result
                    page.overlay.append(file_picker)
                    page.update()
                    file_picker.save_file(
                        dialog_title="اختر مكان حفظ ملف PDF",
                        file_name=f"group_{group_name}_barcodes.pdf",
                        allowed_extensions=["pdf"]
                    )
            except Exception as e:
                show_error_dialog(page, f"خطأ أثناء التصدير: {e}")

        def on_group_change(e):
            try:
                selected_group["value"] = std_group.value
                if std_group.value:
                    with sqlite3.connect(students_db_path) as conn:
                        c = conn.cursor()
                        c.execute("SELECT COUNT(*) FROM students WHERE group_id = ?", (std_group.value,))
                        count = c.fetchone()[0]
                        students_count_text.value = f"عدد طلاب المجموعة: {count}"
                else:
                    students_count_text.value = ""
                students_count_text.update()
                page.update()
            except Exception as e:
                show_error_dialog(page, f"خطأ في تحديث عدد الطلاب: {e}")

        std_group = ft.Dropdown(
            label="المجموعة",
            hint_text="اختر مجموعة لتصدير باركوداتها",
            options=get_groups(),
            expand=True,
            on_change=on_group_change
        )

        export_btn = ft.ElevatedButton(
            "تصدير باركودات المجموعة كـ PDF",
            icon=ft.Icons.PICTURE_AS_PDF,
            bgcolor="#28A745",
            color="white",
            on_click=lambda e: (
                export_pdf_for_group(std_group.value, std_group.value)
                if std_group.value else show_error_dialog(page, "من فضلك اختر مجموعة أولاً")
            )
        )

        number_of_col = ft.Dropdown(
            label="عدد مرات تكرار الباركود لكل طالب",
            hint_text="اختر عدد التكرارات",
            value="3",
            options=[ft.dropdown.Option(str(i)) for i in range(1, 11)],
            expand=True,
        )

        number_of_row = ft.Dropdown(
            label="عدد الطلاب في كل صفحة",
            hint_text="اختر عدد الطلاب",
            value="6",
            options=[ft.dropdown.Option(str(i)) for i in range(1, 11)],
            expand=True,
        )

        return ft.Container(
            expand=True,
            padding=20,
            border_radius=12,
            content=ft.Column(
                controls=[
                    ft.Text("تصدير الباركود", size=24, weight="bold", text_align="center", color="white"),
                    ft.Divider(height=20, color="white"),
                    std_group,
                    students_count_text,
                    ft.Row([number_of_row, number_of_col]),
                    export_btn
                ],
                spacing=20,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.START
            )
        )

    def generate_and_save_student_barcodes(page):
        barcodes_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'barcodes'))
        os.makedirs(barcodes_dir, exist_ok=True)

        writer = ImageWriter()
        writer.set_options({
            "module_width": 0.35,
            "module_height": 20.0,
            "font_size": 12,
            "text_distance": 2,
            "quiet_zone": 1.0,
            "write_text": True,
        })

        try:
            with sqlite3.connect(students_db_path) as conn:
                c = conn.cursor()
                c.execute('SELECT id, code, first_name, father_name, family_name, barcode_path FROM students WHERE code IS NOT NULL')
                students = c.fetchall()
                generated_count = 0

                for student_id, code, first_name, father_name, family_name, barcode_path in students:
                    file_missing = True
                    if barcode_path and os.path.exists(barcode_path):
                        file_missing = False

                    if not code or not file_missing:
                        continue

                    try:
                        student_name = f"{first_name} {father_name} {family_name}"
                        padded_code = str(code).zfill(4)
                        barcode_value = padded_code.rjust(12, "0")

                        EAN = barcode.get_barcode_class('ean13')
                        my_code = EAN(barcode_value, writer=writer)
                        barcode_file_path = os.path.join(barcodes_dir, str(code))
                        my_code.save(barcode_file_path)
                        barcode_path_in_db = barcode_file_path + ".png"

                        img = Image.open(barcode_path_in_db).convert("RGB")
                        img_width, img_height = img.size

                        try:
                            reshaped = arabic_reshaper.reshape(student_name)
                            bidi_text = get_display(reshaped)
                        except Exception:
                            bidi_text = student_name

                        font_size = 22
                        font_paths = [
                            "Amiri-Bold.ttf",
                            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                            "arialbd.ttf",
                            "NotoNaskhArabic-Bold.ttf",
                        ]
                        font = None
                        for p in font_paths:
                            try:
                                font = ImageFont.truetype(p, font_size)
                                break
                            except:
                                continue

                        if font is None:
                            font = ImageFont.load_default()

                        draw = ImageDraw.Draw(img)
                        bbox = draw.textbbox((0, 0), bidi_text, font=font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]

                        extra = font_size + 20
                        new_height = img_height + extra
                        new_img = Image.new("RGB", (img_width, new_height), "white")
                        draw_new = ImageDraw.Draw(new_img)

                        x = max(3, (img_width - text_width) / 2)
                        y = 10
                        draw_new.text((x, y), bidi_text, font=font, fill="black")
                        new_img.paste(img, (0, text_height + 20))
                        new_img.save(barcode_path_in_db)

                        c.execute('UPDATE students SET barcode_path = ? WHERE id = ?', (barcode_path_in_db, student_id))
                        generated_count += 1

                    except Exception as e:
                        show_error_dialog(page, f"خطأ في إنشاء الباركود للطالب {code}: {e}")

                try:
                    conn.commit()
                    if generated_count > 0:
                        show_success_dialog(page, f"تم إنشاء {generated_count} باركود بنجاح")
                        update_side_content(ft.Container(content=ft.Text(f"تم إنشاء {generated_count} باركود بنجاح", size=20, color="white")))
                    else:
                        show_success_dialog(page, "جميع الباركودات موجودة بالفعل")
                        update_side_content(ft.Container(content=ft.Text("جميع الباركودات موجودة بالفعل", size=20, color="white")))
                except Exception as e:
                    show_error_dialog(page, f"خطأ في حفظ البيانات: {e}")
        except Exception as e:
            show_error_dialog(page, f"خطأ في الوصول لقاعدة البيانات: {e}")

    return ft.Row(
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Column([
                            ft.Text("إدارة المجموعات", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color="#FFFFFF"),
                            ft.Divider(height=10, color="white"),
                        ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Container(
                            expand=True,
                            content=ft.Column(
                                controls=[
                                    ft.Container(
                                        content=ft.Row([
                                            ft.Text("عرض الطلاب", size=20, weight="bold", color="#ffffff"),
                                            ft.Icon(ft.Icons.REMOVE_RED_EYE_SHARP, size=36, color="#ffffff")
                                        ], alignment="center", spacing=12),
                                        bgcolor="#0D6EFD",
                                        border_radius=12,
                                        height=80,
                                        expand=True,
                                        margin=5,
                                        padding=5,
                                        border=ft.border.all(2, "#0044A9"),
                                        ink=True,
                                        on_click=lambda e: update_side_content(displaying_students_container(page)),
                                        alignment=ft.alignment.center
                                    ),
                                    ft.Container(
                                        content=ft.Row([
                                            ft.Text("تصدير الباركود", size=20, weight="bold", color="#ffffff"),
                                            ft.Icon(ft.Icons.QR_CODE, size=36, color="#ffffff")
                                        ], alignment="center", spacing=12),
                                        bgcolor="#3B7EFF",
                                        border_radius=12,
                                        height=80,
                                        expand=True,
                                        margin=5,
                                        padding=5,
                                        border=ft.border.all(2, "#0044A9"),
                                        ink=True,
                                        on_click=lambda e: update_side_content(PDF_export_container(page)),
                                        alignment=ft.alignment.center
                                    ),
                                    ft.Container(
                                        content=ft.Row([
                                            ft.Text("إنشاء الباركودات", size=20, weight="bold", color="#ffffff"),
                                            ft.Icon(ft.Icons.AUTO_AWESOME, size=36, color="#ffffff")
                                        ], alignment="center", spacing=12),
                                        bgcolor="#3B7EFF",
                                        border_radius=12,
                                        height=80,
                                        expand=True,
                                        margin=5,
                                        padding=5,
                                        border=ft.border.all(2, "#0044A9"),
                                        ink=True,
                                        on_click=lambda e: generate_and_save_student_barcodes(page),
                                        alignment=ft.alignment.center
                                    ),
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