def get_student_welcome_message(student_name: str) -> str:
    """
    إنشاء رسالة ترحيبية للطالب
    :param student_name: اسم الطالب
    :return: نص رسالة 
    
    """
    return f"""مرحباً {student_name} 👋
    
شكراً لتفعيل حسابك في نظام متابعة الطلاب! 🌟

ستتلقى هنا:
📚 تقارير الاختبارات
📅 تحديثات الحضور والغياب
📝 الإعلانات المهمة
💡 نصائح وتوجيهات

نتمنى لك التوفيق والنجاح! 🎯"""

def get_guardian_welcome_message(student_name: str) -> str:
    """
    إنشاء رسالة ترحيبية لولي الأمر
    :param student_name: اسم الطالب
    :return: نص رسالة الترحيب
    """
    return f"""مرحباً بك ولي أمر الطالب {student_name} 👋
    
شكراً لتفعيل حسابك في نظام متابعة الطلاب! 🌟

ستصلك تقارير دورية عن:
📚 نتائج الاختبارات
📅 الحضور والغياب
💰 حالة المدفوعات
📢 الإعلانات المهمة

نشكر تعاونكم معنا لمتابعة مستوى الطالب 🤝"""

def get_activation_message(name: str, code: str, is_guardian: bool = False) -> str:
    """
    إنشاء رسالة تفعيل الحساب مع رابط التفعيل
    :param name: اسم المستخدم
    :param code: الكود الفريد للتفعيل
    :param is_guardian: هل المستخدم ولي أمر
    :return: نص رسالة التفعيل
    """
    user_type = "ولي أمر الطالب" if is_guardian else "الطالب"
    activation_code = f"{code}1" if is_guardian else code
    
    return f"""مرحباً {user_type} {name} 👋
    
لتفعيل حسابك في نظام متابعة الطلاب، يرجى الضغط على الرابط التالي:

🔗 t.me/studentMang_bot?start={activation_code}

⚠️ هذا الرابط خاص بك، لا تشاركه مع أحد.
"""