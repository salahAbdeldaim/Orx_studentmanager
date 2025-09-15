from datetime import datetime
import sqlite3
import logging

class DateManager:
    DATE_FORMAT = '%d-%m-%Y'

    @staticmethod
    def normalize_date(date_str):
        """توحيد تنسيق التاريخ إلى dd-mm-yyyy"""
        if not date_str or date_str == '-' or date_str == "":
            return None
            
        try:
            date_str = date_str.strip().replace('/', '-')
            formats = [
                '%Y-%m-%d', 
                '%d-%m-%Y', 
                '%d-%m-%y',
                '%Y/%m/%d',
                '%d/%m/%Y',
                '%m-%d-%Y',
                '%Y.%m.%d',
                '%d.%m.%Y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt).strftime(DateManager.DATE_FORMAT)
                except ValueError:
                    continue
            return None
        except Exception as e:
            logging.error(f"Error normalizing date {date_str}: {str(e)}")
            return None

    @staticmethod
    def get_today():
        """الحصول على تاريخ اليوم بالتنسيق الموحد"""
        return datetime.now().strftime(DateManager.DATE_FORMAT)

    @staticmethod
    def clean_database(db_path):
        """تنظيف وتوحيد جميع التواريخ في قاعدة البيانات"""
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            updates = {
                'attendance': {
                    'table': 'attendance',
                    'date_column': 'attendance_date',
                    'count': 0,
                    'total': 0,
                    'errors': []
                },
                'payments': {
                    'table': 'payments',
                    'date_column': 'payment_date',
                    'count': 0,
                    'total': 0,
                    'errors': []
                },
                'exams': {
                    'table': 'exams',
                    'date_column': 'exam_date',
                    'count': 0,
                    'total': 0,
                    'errors': []
                }
            }
            
            # معالجة كل جدول
            for key, info in updates.items():
                table = info['table']
                date_column = info['date_column']
                logging.info(f"Cleaning {table} dates...")
                
                # جلب كل السجلات
                c.execute(f'SELECT id, {date_column} FROM {table}')
                rows = c.fetchall()
                info['total'] = len(rows)
                
                for row_id, old_date in rows:
                    if old_date and old_date != '-':
                        try:
                            new_date = DateManager.normalize_date(old_date)
                            if new_date and new_date != old_date:
                                # تحديث التاريخ بالتنسيق الجديد
                                update_query = f'''
                                    UPDATE {table} 
                                    SET {date_column} = ? 
                                    WHERE id = ?
                                '''
                                c.execute(update_query, (new_date, row_id))
                                info['count'] += 1
                                logging.info(f"Updated {table} date: {old_date} -> {new_date} (ID: {row_id})")
                            elif not new_date:
                                error_msg = f"Could not normalize date: {old_date} in {table} (ID: {row_id})"
                                info['errors'].append(error_msg)
                                logging.warning(error_msg)
                        except Exception as e:
                            error_msg = f"Error processing date {old_date} in {table} (ID: {row_id}): {str(e)}"
                            info['errors'].append(error_msg)
                            logging.error(error_msg)

            # تحديث قاعدة البيانات
            conn.commit()
            
            # إحصائيات التنظيف
            stats = {
                'summary': {
                    'total_records': sum(info['total'] for info in updates.values()),
                    'total_updated': sum(info['count'] for info in updates.values()),
                    'total_errors': sum(len(info['errors']) for info in updates.values())
                }
            }

            # إضافة تفاصيل لكل جدول
            for key, info in updates.items():
                stats[key] = {
                    'total_records': info['total'],
                    'updated_records': info['count'],
                    'errors': info['errors']
                }
            
            conn.close()
            return True, stats
            
        except Exception as e:
            logging.error(f"Error cleaning database: {str(e)}")
            return False, str(e)

    @staticmethod
    def is_valid_date(date_str):
        """التحقق من صحة تنسيق التاريخ"""
        if not date_str:
            return False
        try:
            datetime.strptime(date_str, DateManager.DATE_FORMAT)
            return True
        except ValueError:
            return False

    @staticmethod
    def compare_dates(date1, date2):
        """مقارنة تاريخين وإرجاع الفرق بينهما"""
        try:
            d1 = datetime.strptime(date1, DateManager.DATE_FORMAT)
            d2 = datetime.strptime(date2, DateManager.DATE_FORMAT)
            return (d1 - d2).days
        except:
            return None