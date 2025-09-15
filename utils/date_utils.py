from datetime import datetime

def normalize_date_format(date_str):
    """
    توحيد تنسيق التاريخ إلى dd-mm-yyyy
    يقبل التنسيقات التالية:
    - yyyy-mm-dd
    - dd-mm-yyyy
    - d-m-yyyy
    - yyyy/mm/dd
    - dd/mm/yyyy
    """
    if not date_str or date_str == '-':
        return date_str
        
    try:
        # إزالة أي مسافات
        date_str = date_str.strip()
        
        # تحويل / إلى -
        date_str = date_str.replace('/', '-')
        
        # تجربة التنسيقات المختلفة
        formats = [
            '%Y-%m-%d',  # yyyy-mm-dd
            '%d-%m-%Y',  # dd-mm-yyyy
            '%d-%m-%y',  # dd-mm-yy
            '%Y/%m/%d',  # yyyy/mm/dd
            '%d/%m/%Y',  # dd/mm/yyyy
        ]
        
        parsed_date = None
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue
                
        if parsed_date is None:
            return date_str
            
        # تحويل إلى التنسيق المطلوب dd-mm-yyyy
        return parsed_date.strftime('%d-%m-%Y')
        
    except Exception as e:
        print(f"Error normalizing date {date_str}: {str(e)}")
        return date_str