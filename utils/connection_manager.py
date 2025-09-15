"""
مدير الاتصال - Connection Manager

هذا الملف يوفر نظام مراقبة وإدارة حالة الاتصال بالإنترنت في التطبيق.
يستخدم نمط Singleton لضمان وجود نسخة واحدة فقط من مدير الاتصال في التطبيق.

يتكامل مع WhatsApp Manager من خلال:
1. استخدام دالة check_internet للتحقق من حالة الاتصال
2. توفير واجهة موحدة لفحص الاتصال لجميع أجزاء التطبيق
3. إدارة حالة الاتصال بشكل مركزي لتحسين الأداء وتجنب الفحص المتكرر
4. توفير نظام إخطارات للتغييرات في حالة الاتصال

المميزات:
- مراقبة مستمرة لحالة الاتصال في الخلفية
- إخطار جميع الأجزاء المهتمة بتغييرات حالة الاتصال
- تحسين أداء التطبيق من خلال مشاركة حالة الاتصال
- إمكانية إضافة مستمعين جدد في أي وقت
- معالجة آمنة للمتغيرات المشتركة باستخدام Threading Lock

الاستخدام النموذجي:
    conn_manager = ConnectionManager()
    conn_manager.start_monitoring()
    conn_manager.add_status_listener(my_status_handler)
"""

import flet as ft
from utils.whatsapp_manager import check_internet
from threading import Lock, Thread
import time


class ConnectionManager:
    """
    فئة مدير الاتصال - مسؤولة عن مراقبة وإدارة حالة الاتصال بالإنترنت
    
    تستخدم نمط Singleton لضمان وجود نسخة واحدة فقط في التطبيق
    وتدير مراقبة الاتصال في خيط منفصل للحفاظ على أداء التطبيق
    """
    _instance = None  # النسخة الوحيدة من الفئة
    _lock = Lock()    # قفل للتزامن بين الخيوط
    
    def __new__(cls):
        """
        منشئ النمط Singleton - يضمن وجود نسخة واحدة فقط من الفئة
        """
        with cls._lock:  # قفل للتزامن عند إنشاء النسخة
            if cls._instance is None:
                cls._instance = super(ConnectionManager, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """
        تهيئة الحالة الأولية لمدير الاتصال
        
        المتغيرات:
        - _is_online: حالة الاتصال الحالية
        - _status_listeners: قائمة الدوال المستمعة للتغييرات
        - _monitoring: حالة المراقبة (نشطة/متوقفة)
        - _monitor_thread: خيط مراقبة الاتصال
        """
        self._is_online = True
        self._status_listeners = []
        self._monitoring = False
        self._monitor_thread = None
    
    def start_monitoring(self):
        """
        بدء مراقبة حالة الاتصال في خيط منفصل
        
        - يتحقق أولاً من عدم وجود مراقبة نشطة
        - ينشئ خيطاً جديداً للمراقبة في الخلفية
        - يضبط الخيط كـ daemon لإيقافه تلقائياً عند إغلاق التطبيق
        """
        if not self._monitoring:
            self._monitoring = True
            self._monitor_thread = Thread(target=self._monitor_connection, daemon=True)
            self._monitor_thread.start()
    
    def stop_monitoring(self):
        """
        إيقاف مراقبة حالة الاتصال بشكل آمن
        
        - يضبط علامة التوقف
        - ينتظر انتهاء خيط المراقبة بمهلة محددة
        - يمنع تعليق التطبيق عند الإغلاق
        """
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)
    
    def _monitor_connection(self):
        """
        الدالة الرئيسية لمراقبة حالة الاتصال في الخلفية
        
        العملية:
        1. تعمل في حلقة مستمرة طالما المراقبة نشطة
        2. تفحص حالة الاتصال كل 5 ثوانٍ
        3. عند تغير الحالة:
           - تحدث المتغير _is_online
           - تخطر جميع المستمعين بالتغيير
        """
        while self._monitoring:
            new_status = check_internet()
            if new_status != self._is_online:
                self._is_online = new_status
                self._notify_listeners()
            time.sleep(5)  # فحص كل 5 ثوانٍ
    
    def add_status_listener(self, listener):
        """
        إضافة دالة مستمعة لتغييرات حالة الاتصال
        
        المعاملات:
        - listener: دالة تستقبل معامل واحد (is_online: bool)
                   سيتم استدعاؤها عند تغير حالة الاتصال
        
        تضيف المستمع فقط إذا لم يكن موجوداً مسبقاً
        """
        if listener not in self._status_listeners:
            self._status_listeners.append(listener)
    
    def remove_status_listener(self, listener):
        """
        إزالة دالة مستمعة من قائمة المستمعين
        
        المعاملات:
        - listener: الدالة المراد إزالتها من قائمة المستمعين
        
        تتجاهل الدالة محاولة إزالة مستمع غير موجود
        """
        if listener in self._status_listeners:
            self._status_listeners.remove(listener)
    
    def _notify_listeners(self):
        """
        إخطار جميع المستمعين المسجلين بتغيير حالة الاتصال
        
        - تستدعي كل دالة مستمعة مع الحالة الجديدة
        - تتجاهل أي أخطاء تحدث في دوال المستمعين
        - تمنع انتشار الأخطاء من المستمعين إلى نظام المراقبة
        """
        for listener in self._status_listeners:
            try:
                listener(self._is_online)
            except:
                pass  # تجاهل أي أخطاء في المستمعين
    
    @property
    def is_online(self):
        """
        خاصية للحصول على حالة الاتصال الحالية
        
        Returns:
            bool: True إذا كان متصل بالإنترنت، False إذا كان غير متصل
        """
        return self._is_online
    
    def check_connection(self, show_message=True, page=None):
        """
        فحص حالة الاتصال مع إمكانية عرض رسالة خطأ
        
        المعاملات:
        - show_message: bool - ما إذا كان يجب عرض رسالة في حالة عدم وجود اتصال
        - page: ft.Page - صفحة التطبيق لعرض رسالة الخطأ عليها
        
        Returns:
            bool: True إذا كان متصل بالإنترنت، False إذا كان غير متصل
        """
        if not self._is_online and show_message and page:
            from utils.helpers import show_error_dialog
            show_error_dialog(page, "لا يوجد اتصال بالإنترنت. يرجى التحقق من اتصالك والمحاولة مرة أخرى.")
        return self._is_online
    
    