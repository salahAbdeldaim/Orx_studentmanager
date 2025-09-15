import sqlite3
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.database import students_db_path
from datetime import datetime, date

def clear_barcode_paths():
    try:
        with sqlite3.connect(students_db_path) as conn:
            c = conn.cursor()
            # تفريغ المسارات فقط
            c.execute("UPDATE students SET barcode_path = NULL")
            affected = c.rowcount  # عدد السجلات اللي اتحدثت
            conn.commit()
            print(f" تم مسح {affected} مسار باركود من قاعدة البيانات.")
    except Exception as e:
        print(f" خطأ أثناء المسح: {e}")


def clean_old_payments(before_year: int = None):
    """
    دالة لحذف بيانات الدفع القديمة من قاعدة البيانات.
    - before_year: حذف جميع السجلات قبل هذه السنة (افتراضي: السنة الحالية - 2).
    - هذا يساعد في الحفظ بشكل سليم بتجنب التكرارات أو البيانات القديمة غير الضرورية.
    """
    if before_year is None:
        before_year = int(datetime.now().strftime('%Y')) - 2  # حذف قبل سنتين افتراضياً
    conn = None
    try:
        conn = sqlite3.connect(students_db_path)
        c = conn.cursor()
        # حذف السجلات حيث month < 'YYYY-01' للسنة المحددة
        cutoff_month = f"{before_year}-01"
        c.execute('DELETE FROM payments WHERE month < ?', (cutoff_month,))
        deleted_rows = c.rowcount
        conn.commit()
        print(f"تم حذف {deleted_rows} سجل من بيانات الدفع القديمة قبل {before_year}.")
    except Exception as e:
        print(f"خطأ في حذف البيانات القديمة: {str(e)}")
    finally:
        if conn:
            conn.close()

def clear_all_payments():
    """
    دالة لحذف جميع بيانات الدفع من قاعدة البيانات.
    - يحذف كل السجلات في جدول payments لإعادة التعيين الكامل.
    """
    conn = None
    try:
        conn = sqlite3.connect(students_db_path)
        c = conn.cursor()
        c.execute('DELETE FROM payments')
        deleted_rows = c.rowcount
        conn.commit()
        print(f"تم حذف جميع {deleted_rows} سجل من بيانات الدفع.")
    except Exception as e:
        print(f"خطأ في حذف جميع بيانات الدفع: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    clear_all_payments()
