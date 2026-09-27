

التشغيل

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py

أول دخول

اسم المستخدم: malia benflis
كلمة المرور المؤقتة: 0660451073

غيّر كلمة المرور مباشرة من:
الإعدادات والأمان → كلمة المرور.

Gemini

يمكن وضع المفتاح في متغير البيئة:
Windows PowerShell:

$env:GEMINI_API_KEY="YOUR_KEY"
streamlit run app.py

أو إدخاله من واجهة المساعد الذكي.

التخزين

كل البيانات المحلية داخل:
clinic_storage/

وهناك:

users_db.json للحسابات.

clinic_data.json لبيانات العيادة.

settings.json للإعدادات.

backups/ للنسخ الاحتياطية.

media/ للملفات المرفوعة.

تنبيه

هذا نظام إدارة معلومات محلي. لا تعتبر نماذج التقييم المضمنة بديلاً عن الاختبارات الأرطوفونية المقننة أو الحكم السريري المهني.
