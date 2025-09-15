import os
import shutil
import sqlite3
import logging
from datetime import datetime

# إعداد الـ logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# تحديد المسارات
base_path = os.path.expanduser(r"~\AppData\Local\StudentManager")
students_db_path = os.path.join(base_path, "students.db")

# دالة للحصول على مسار قاعدة بيانات قابلة للكتابة
def get_writable_db_path():
    data_dir = base_path
    writable_path = os.path.join(data_dir, "students.db")
    
    # تحديد المسار النسبي لملف قاعدة البيانات المصدر
    try:
        exe_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:  # __file__ غير معرّف في REPL أو اختبار
        exe_dir = os.getcwd()
        logging.warning("تحذير: __file__ غير معرّف، استخدام المجلد الحالي كمسار افتراضي")
    project_root = os.path.dirname(os.path.dirname(exe_dir))
    asset_db_path = os.path.join(project_root, "assets", "students.db")
    
    logging.info(f"Data directory: {data_dir}")
    logging.info(f"Checking for students.db at: {writable_path}")
    logging.info(f"Looking for source students.db at: {asset_db_path}")

    try:
        os.makedirs(data_dir, exist_ok=True)
    except Exception as e:
        logging.error(f"خطأ أثناء إنشاء المجلد {data_dir}: {e}")

    if not os.path.exists(writable_path):
        if os.path.exists(asset_db_path):
            logging.info(f"نسخ قاعدة البيانات من {asset_db_path} إلى {writable_path}")
            try:
                shutil.copy(asset_db_path, writable_path)
                logging.info("تم نسخ قاعدة البيانات بنجاح!")
            except Exception as e:
                logging.error(f"خطأ أثناء نسخ قاعدة البيانات: {e}")
        else:
            logging.warning(f"ملف المصدر {asset_db_path} غير موجود! سيتم إنشاء قاعدة بيانات فارغة.")
            try:
                conn = sqlite3.connect(writable_path)
                conn.close()
                logging.info(f"تم إنشاء قاعدة بيانات فارغة في {writable_path}")
            except Exception as e:
                logging.error(f"خطأ أثناء إنشاء قاعدة بيانات فارغة: {e}")
    else:
        logging.info(f"ملف students.db موجود بالفعل في {writable_path}")
    return writable_path

# استدعاء الدالة للحصول على مسار قاعدة البيانات
students_db_path = get_writable_db_path()

def init_db():
    logging.info("بدء تهيئة قاعدة البيانات")
    try:
        with sqlite3.connect(students_db_path) as conn:
            c = conn.cursor()

            # إنشاء جدول groups
            c.execute('''CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                days TEXT,
                students_count INTEGER DEFAULT 0,
                stage TEXT
            )''')
            logging.info("تم إنشاء/التحقق من جدول groups")

            try:
                c.execute('ALTER TABLE groups ADD COLUMN stage TEXT')
                logging.info("تم إضافة عمود stage إلى groups")
            except sqlite3.OperationalError:
                pass  # العمود موجود بالفعل

            # إنشاء جدول students
            c.execute('''CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                father_name TEXT NOT NULL,
                family_name TEXT NOT NULL,
                phone TEXT,
                guardian_phone TEXT,
                grade TEXT,
                group_id INTEGER,
                email TEXT,
                gender TEXT,
                chat_id TEXT, 
                guardian_chat_id TEXT, 
                barcode_path TEXT,
                code TEXT,
                UNIQUE(first_name, father_name, family_name),
                FOREIGN KEY(group_id) REFERENCES groups(id)
            )''')
            logging.info("تم إنشاء/التحقق من جدول students")

            # التحقق من وجود الأعمدة قبل إضافتها
            c.execute("PRAGMA table_info(students)")
            columns = [row[1] for row in c.fetchall()]
            if "email" not in columns:
                c.execute('ALTER TABLE students ADD COLUMN email TEXT')
                logging.info("تم إضافة عمود email إلى students")
            if "gender" not in columns:
                c.execute('ALTER TABLE students ADD COLUMN gender TEXT')
                logging.info("تم إضافة عمود gender إلى students")
            if "code" not in columns:
                c.execute('ALTER TABLE students ADD COLUMN code TEXT')
                logging.info("تم إضافة عمود code إلى students")
            if "chat_id" not in columns:
                c.execute('ALTER TABLE students ADD COLUMN chat_id TEXT')
                logging.info("تم إضافة عمود chat_id إلى students")
            if "guardian_chat_id" not in columns:
                c.execute('ALTER TABLE students ADD COLUMN guardian_chat_id TEXT')
                logging.info("تم إضافة عمود guardian_chat_id إلى students")
            if "barcode_path" not in columns:
                c.execute('ALTER TABLE students ADD COLUMN barcode_path TEXT')
                logging.info("تم إضافة عمود barcode_path إلى students")

            # إنشاء جدول exams
            c.execute('''CREATE TABLE IF NOT EXISTS exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                exam_date TEXT,
                total_score INTEGER,
                student_score INTEGER,
                FOREIGN KEY(student_id) REFERENCES students(id)
            )''')
            logging.info("تم إنشاء/التحقق من جدول exams")
            
            # إنشاء جدول attendance
            c.execute('''CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                attendance_date TEXT,
                status TEXT,
                day TEXT,
                attendance_time TEXT,
                UNIQUE(student_id, attendance_date),
                FOREIGN KEY(student_id) REFERENCES students(id)
            )''')
            logging.info("تم إنشاء/التحقق من جدول attendance")
            
            try:
                c.execute('ALTER TABLE attendance ADD COLUMN day TEXT')
                logging.info("تم إضافة عمود day إلى attendance")
            except sqlite3.OperationalError:
                pass  # العمود موجود بالفعل
            
            try:
                c.execute('ALTER TABLE attendance ADD COLUMN attendance_time TEXT')
                logging.info("تم إضافة عمود attendance_time إلى attendance")
            except sqlite3.OperationalError:
                pass  # العمود موجود بالفعل

            # إنشاء جدول payments
            c.execute('''CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                month TEXT,
                status TEXT,
                payment_date TEXT,
                UNIQUE(student_id, month),
                FOREIGN KEY(student_id) REFERENCES students(id)
            )''')
            logging.info("تم إنشاء/التحقق من جدول payments")
            
            try:
                c.execute('ALTER TABLE payments ADD COLUMN payment_date TEXT')
                logging.info("تم إضافة عمود payment_date إلى payments")
            except sqlite3.OperationalError:
                pass
                
            # إنشاء جدول teachers
            c.execute('''CREATE TABLE IF NOT EXISTS teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                subject TEXT
            )''')
            logging.info("تم إنشاء/التحقق من جدول teachers")
            
            c.execute("PRAGMA table_info(teachers)")
            teacher_columns = [row[1] for row in c.fetchall()]
            if "name" not in teacher_columns:
                c.execute('ALTER TABLE teachers ADD COLUMN name TEXT NOT NULL')
                logging.info("تم إضافة عمود name إلى teachers")
            
            # إنشاء جدول pending_notifications
            c.execute('''CREATE TABLE IF NOT EXISTS pending_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )''')
            logging.info("تم إنشاء/التحقق من جدول pending_notifications")
            
            # إضافة فهارس لتحسين الأداء
            try:
                c.execute('CREATE INDEX IF NOT EXISTS idx_students_code ON students(code)')
                logging.info("تم إضافة فهرسة على code في students")
                c.execute('CREATE INDEX IF NOT EXISTS idx_students_name ON students(first_name, father_name, family_name)')
                logging.info("تم إضافة فهرسة على first_name, father_name, family_name في students")
                c.execute('CREATE INDEX IF NOT EXISTS idx_exams_student ON exams(student_id)')
                logging.info("تم إضافة فهرسة على student_id في exams")
                c.execute('CREATE INDEX IF NOT EXISTS idx_payments_student_month ON payments(student_id, month)')
                logging.info("تم إضافة فهرسة على student_id, month في payments")
                c.execute('CREATE INDEX IF NOT EXISTS idx_attendance_student_date ON attendance(student_id, attendance_date)')
                logging.info("تم إضافة فهرسة على student_id, attendance_date في attendance")
            except sqlite3.OperationalError as e:
                logging.warning(f"تحذير أثناء إنشاء الفهارس: {e}")
            
            conn.commit()
            logging.info("تم تهيئة قاعدة البيانات بنجاح")
    except Exception as e:
        logging.error(f"خطأ أثناء تهيئة قاعدة البيانات: {e}", exc_info=True)
        conn.rollback()
        raise

# استدعاء تهيئة قاعدة البيانات
try:
    init_db()
    logging.info("تم استدعاء init_db بنجاح")
except Exception as e:
    logging.error(f"خطأ في init_db: {e}")
    raise

def get_next_code():
    with sqlite3.connect(students_db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT MAX(CAST(code AS INTEGER)) FROM students")
        max_code = c.fetchone()[0]
        if not max_code or max_code < 1000:
            return 1001
        return max_code + 1

def get_student_code(student_name: str) -> str:
    """
    الحصول على الكود الفريد للطالب باستخدام اسمه الكامل
    :param student_name: اسم الطالب الكامل (الأول والأب والعائلة)
    :return: الكود الفريد للطالب أو None إذا لم يتم العثور عليه
    """
    try:
        # تقسيم الاسم إلى أجزائه
        names = student_name.strip().split()
        if len(names) < 3:
            logging.error(f"الاسم '{student_name}' غير مكتمل")
            return None
            
        first_name = names[0]
        father_name = names[1]
        family_name = names[-1]
        
        with sqlite3.connect(students_db_path) as conn:
            c = conn.cursor()
            c.execute("""
                SELECT code 
                FROM students 
                WHERE first_name = ? AND father_name = ? AND family_name = ?
            """, (first_name, father_name, family_name))
            
            result = c.fetchone()
            if result and result[0]:
                return str(result[0])  # تحويل الكود إلى نص
            
            logging.warning(f"لم يتم العثور على كود للطالب: {student_name}")
            return None
            
    except Exception as e:
        logging.error(f"خطأ في الحصول على كود الطالب {student_name}: {e}")
        return None