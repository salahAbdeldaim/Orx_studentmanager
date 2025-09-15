import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sqlite3

from utils.database import students_db_path

def init_codes():
    with sqlite3.connect(students_db_path) as conn:
        c = conn.cursor()

        # 1️⃣ إنشاء العمود لو مش موجود
        # إضافة عمود code للطلاب لو مش موجود
        c.execute("PRAGMA table_info(students)")
        columns = [row[1] for row in c.fetchall()]
        if "code" not in columns:
            c.execute('ALTER TABLE students ADD COLUMN code INTEGER')
        

        # 2️⃣ توزيع أكواد للطلاب القدامى
        c.execute("SELECT id, code FROM students ORDER BY id")
        students = c.fetchall()
        
        next_code = 1001
        for student_id, code in students:
            if code is None:  # الطالب معندوش كود
                c.execute("UPDATE students SET code = ? WHERE id = ?", (next_code, student_id))
                next_code += 1
            else:
                # تحديث العداد بحيث يفضل أكبر من أي كود موجود
                if code is not None:  # تأكد من أن الكود موجود
                    code_int = int(code)  # تحويل الكود لرقم صحيح
                    if code_int >= next_code:
                        next_code = code_int + 1

        conn.commit()
        print("✅ تم توزيع الأكواد بنجاح!")

def get_next_code():
    with sqlite3.connect(students_db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT MAX(code) FROM students")
        max_code = c.fetchone()[0]
        if not max_code:
            return 1001
        # Convert max_code to integer before comparison
        max_code = int(max_code)
        if max_code < 1000:
            return 1001
        return max_code + 1

init_codes()
print("الكود التالي اللي هيتوزع:", get_next_code())
