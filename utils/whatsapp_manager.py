"""
مدير خدمة الواتساب - WhatsApp Manager

هذا الملف يوفر واجهة آمنة وموثوقة للتعامل مع خدمة واتساب في التطبيق.
يتضمن الوظائف التالية:
1. فحص الاتصال بالإنترنت بشكل آمن
2. استيراد مكتبة pywhatkit بشكل كسول (فقط عند الحاجة)
3. إرسال رسائل واتساب مع معالجة الأخطاء
4. التحقق من توفر الخدمة قبل استخدامها

مميزات:
- يعمل بشكل آمن حتى عند عدم توفر اتصال إنترنت
- يتعامل مع جميع أنواع الأخطاء المحتملة
- يوفر رسائل خطأ واضحة باللغة العربية
- يدعم إعادة المحاولة تلقائياً عند فشل الاتصال
"""

import importlib
import requests
from functools import wraps


def check_internet():
    """
    فحص الاتصال بالإنترنت بشكل آمن وسريع 
    
    الوظيفة:
    - تحاول الاتصال بمواقع موثوقة للتأكد من وجود اتصال إنترنت
    - تستخدم طريقة HEAD بدلاً من GET لتقليل استهلاك البيانات
    - تجرب مواقع بديلة في حالة فشل الموقع الأول
    
    يتم استخدام هذه الدالة بواسطة:
    1. ConnectionManager لمراقبة حالة الاتصال
    2. وظائف WhatsApp للتحقق قبل إرسال الرسائل
    
    المخرجات:
    - True: إذا كان هناك اتصال بالإنترنت
    - False: إذا لم يكن هناك اتصال أو حدث خطأ
    """
    try:
        # محاولة الاتصال بموقع موثوق وسريع مع تقليل مهلة الانتظار
        response = requests.head("https://www.google.com", timeout=1.5)
        return response.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        # في حالة عدم وجود اتصال أو انتهاء المهلة
        try:
            # محاولة ثانية مع موقع بديل
            response = requests.head("https://www.cloudflare.com", timeout=1.5)
            return response.status_code == 200
        except:
            return False
    except:
        return False

def lazy_import_pywhatkit():
    """
    استيراد مكتبة pywhatkit بشكل كسول (فقط عند الحاجة)
    
    الوظيفة:
    - تحميل مكتبة pywhatkit فقط عند الحاجة إليها
    - تجنب فشل بدء التشغيل عند عدم توفر اتصال
    - معالجة أخطاء الاستيراد بشكل آمن
    
    المخرجات:
    - كائن مكتبة pywhatkit في حالة نجاح الاستيراد
    - None في حالة فشل الاستيراد
    """
    try:
        return importlib.import_module('pywhatkit')
    except Exception as e:
        print(f"Error importing pywhatkit: {str(e)}")
        return None


def requires_internet(func):
    """
    مزخرف (Decorator) للتأكد من وجود اتصال إنترنت قبل تنفيذ الدالة
    
    الوظيفة:
    - فحص الاتصال بالإنترنت قبل تنفيذ أي دالة
    - منع تنفيذ العمليات التي تحتاج إنترنت عند عدم توفره
    - إرجاع رسالة خطأ مناسبة في حالة عدم وجود اتصال
    
    المعاملات:
    - func: الدالة المراد تنفيذها
    
    المخرجات:
    - نتيجة الدالة الأصلية في حالة وجود اتصال
    - (False, رسالة خطأ) في حالة عدم وجود اتصال
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not check_internet():
            return False, "يرجى التحقق من اتصال الإنترنت الخاص بك"
        return func(*args, **kwargs)
    return wrapper

@requires_internet
def send_whatsapp_message(phone_number, message):
    """
    إرسال رسالة واتساب بشكل آمن مع معالجة كاملة للأخطاء
    
    يتكامل مع ConnectionManager من خلال:
    1. استخدام المزخرف @requires_internet للتحقق من الاتصال
    2. الاعتماد على حالة الاتصال المشتركة
    3. إرجاع رسائل خطأ متسقة مع نظام إدارة الاتصال
    
    الوظيفة:
    - التحقق من صحة رقم الهاتف وتنسيقه
    - فحص الاتصال بالإنترنت قبل محاولة الإرسال
    - تحميل مكتبة pywhatkit بشكل آمن
    - جدولة الرسالة للإرسال في الوقت المناسب
    - معالجة جميع الأخطاء المحتملة
    
    المعاملات:
    - phone_number: رقم الهاتف المراد الإرسال إليه
    - message: نص الرسالة المراد إرسالها
    
    المخرجات:
    - tuple يحتوي على:
      * العنصر الأول: True في حالة النجاح، False في حالة الفشل
      * العنصر الثاني: رسالة توضيحية عن نتيجة العملية
    
    الأخطاء المعالجة:
    - عدم وجود اتصال بالإنترنت
    - رقم هاتف غير صالح
    - فشل في تحميل مكتبة pywhatkit
    - عدم تسجيل الدخول في واتساب
    - انتهاء مهلة الاتصال
    - أخطاء غير متوقعة
    """
    try:
        from datetime import datetime
        
        # التأكد من صحة رقم الهاتف
        formatted_phone = str(phone_number).strip()
        if not formatted_phone.startswith("+"):
            formatted_phone = "+" + formatted_phone
        if not formatted_phone.replace("+", "").isdigit():
            return False, "رقم الهاتف غير صالح"

        # استيراد pywhatkit بشكل كسول
        pwk = lazy_import_pywhatkit()
        if not pwk:
            return False, "فشل في تهيئة خدمة واتساب"

        # تجهيز وقت الإرسال (بعد دقيقتين)
        current_time = datetime.now()
        hour = current_time.hour
        minute = current_time.minute + 2
        if minute >= 60:
            hour += 1
            minute -= 60

        # محاولة إرسال الرسالة
        pwk.sendwhatmsg(formatted_phone, message, hour, minute)
        return True, "تم إرسال الرسالة بنجاح"

    except Exception as ex:
        # تحليل نوع الخطأ وإرجاع رسالة مناسبة
        error_msg = str(ex).lower()
        if "internet" in error_msg:
            return False, "حدث خطأ في الاتصال بالإنترنت"
        elif "failed to locate" in error_msg:
            return False, "تأكد من تسجيل الدخول إلى واتساب على المتصفح"
        elif "timeout" in error_msg:
            return False, "انتهت مهلة الاتصال، يرجى المحاولة مرة أخرى"
        elif "connection" in error_msg:
            return False, "فشل الاتصال بخدمة واتساب"
        else:
            return False, f"حدث خطأ غير متوقع: {str(ex)}"