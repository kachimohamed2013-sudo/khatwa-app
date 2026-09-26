import streamlit as st
import json
import os
import pandas as pd
from datetime import date

# ---------------------------------------------------------
# 1. إعدادات الصفحة الرئيسية
# ---------------------------------------------------------
st.set_page_config(
    page_title="منصة خطوة | النظام الذكي للتقييم الأرطوفوني للأطفال",
    page_icon="👣",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. إدارة وقواعد بيانات المستخدمين والحفظ التلقائي
# ---------------------------------------------------------
USERS_FILE = "users_db.json"
DATA_FILE = "data_store.json"

def load_users():
    """تحميل حسابات المستخدمين"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # الحساب الافتراضي للمسؤول الأساسي
    return {
        "malia benflis": {
            "password": "0660451073",
            "role": "admin"
        }
    }

def save_users(users_data):
    """حفظ الحسابات الجديدة تلقائياً"""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_data, f, ensure_ascii=False, indent=4)

def load_all_data():
    """تحميل كافة بيانات النظام"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_all_data(all_data):
    """حفظ بيانات النظام تلقائياً"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)

# تهيئة قاعدة البيانات والحسابات في الجلسة
if "users_db" not in st.session_state:
    st.session_state["users_db"] = load_users()

if "all_data" not in st.session_state:
    st.session_state["all_data"] = load_all_data()

# ---------------------------------------------------------
# 3. شاشة تسجيل الدخول وأمان النظام
# ---------------------------------------------------------
def check_login():
    if "authenticated_user" not in st.session_state:
        st.session_state["authenticated_user"] = None

    if st.session_state["authenticated_user"] is None:
        st.markdown("<h2 style='text-align: center;'>🔒 تسجيل الدخول إلى منصة خطوة</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            username_input = st.text_input("اسم المستخدم")
            password_input = st.text_input("كلمة السر / الكود", type="password")
            
            if st.button("تسجيل الدخول", use_container_width=True):
                users = st.session_state["users_db"]
                if username_input in users and users[username_input]["password"] == password_input:
                    st.session_state["authenticated_user"] = username_input
                    st.success(f"مرحباً بك {username_input}!")
                    st.rerun()
                else:
                    st.error("❌ اسم المستخدم أو كلمة السر غير صحيحة!")
        return False
    return True

if not check_login():
    st.stop()

# ---------------------------------------------------------
# 4. تحديد المستخدم الحالي وتحميل بياناته الخاصة فقط
# ---------------------------------------------------------
current_user = st.session_state["authenticated_user"]
user_role = st.session_state["users_db"][current_user].get("role", "user")

# التأكد من وجود مساحة حفظ خاصة بالمستخدم الحالي
if current_user not in st.session_state["all_data"]:
    st.session_state["all_data"][current_user] = {"children": [], "sessions": []}

user_data = st.session_state["all_data"][current_user]

# ---------------------------------------------------------
# 5. القائمة الجانبية وتوجيه الصفحات
# ---------------------------------------------------------
st.sidebar.title("منصة خطوة 👣")
st.sidebar.markdown(f"👤 **المستخدم:** `{current_user}`")

menu_options = [
    "📊 لوحة التحكم والمواعيد", 
    "➕ إضافة تقييم طفل جديد", 
    "🔍 الأرشيف وسجلات الأطفال", 
    "⚙️ إعدادات العيادة"
]

# إضافة خيار إدارة الحسابات للمسؤول فقط (malia benflis)
if user_role == "admin":
    menu_options.append("👑 إدارة الحسابات والمستخدمين")

menu = st.sidebar.radio("القائمة الرئيسية", menu_options)

if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
    st.session_state["authenticated_user"] = None
    st.rerun()

# ---------------------------------------------------------
# 6. محتوى الصفحات
# ---------------------------------------------------------

# --- الصفحة 1: لوحة التحكم ---
if menu == "📊 لوحة التحكم والمواعيد":
    st.title("📊 لوحة قيادة العيادة")
    st.caption("تنسيق وحفظ البيانات الخاص بك فقط")
    
    total_children = len(user_data["children"])
    total_sessions = len(user_data["sessions"])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("إجمالي أطفالك المسجلين", f"{total_children} طفل")
    col2.metric("جلساتك اليوم", f"{total_sessions} جلسة")
    col3.metric("مستحقات غير مدفوعة", "0 حالات")
    col4.metric("حالة الحفظ التلقائي", "نشط 🟢")

# --- الصفحة 2: إضافة طفل جديد ---
elif menu == "➕ إضافة تقييم طفل جديد":
    st.title("➕ إضافة طفل جديد إلى ملفك الخاص")
    
    with st.form("add_child_form"):
        child_name = st.text_input("اسم الطفل الكامل")
        child_age = st.number_input("العمر (سنوات)", min_value=1, max_value=18, value=5)
        notes = st.text_area("تشخيص أو ملاحظات أولية")
        
        submitted = st.form_submit_button("حفظ الطفل تلقائياً")
        if submitted:
            if child_name:
                new_child = {
                    "id": len(user_data["children"]) + 1,
                    "name": child_name,
                    "age": child_age,
                    "notes": notes,
                    "created_at": str(date.today())
                }
                # إضافة بيانات الطفل لمساحة المستخدم الحالي
                user_data["children"].append(new_child)
                
                # حفظ التغييرات تلقائياً في الملف
                save_all_data(st.session_state["all_data"])
                st.success(f"✅ تم حفظ بيانات الطفل ({child_name}) في حسابك بنجاح!")
            else:
                st.warning("يرجى إدخال اسم الطفل.")

# --- الصفحة 3: الأرشيف ---
elif menu == "🔍 الأرشيف وسجلات الأطفال":
    st.title("🔍 الأرشيف والبيانات المحفوظة لحسابك")
    if user_data["children"]:
        st.dataframe(pd.DataFrame(user_data["children"]), use_container_width=True)
    else:
        st.info("لا توجد بيانات أطفال محفوظة في حسابك بعد.")

# --- الصفحة 4: الإعدادات ---
elif menu == "⚙️ إعدادات العيادة":
    st.title("⚙️ إعدادات العيادة والحفظ التلقائي")
    st.success(f"🔒 الحفظ التلقائي مفعّل ومخصص لحساب: **{current_user}**")

# --- الصفحة 5: إضافة مستخدمين (للمسؤول فقط) ---
elif menu == "👑 إدارة الحسابات والمستخدمين" and user_role == "admin":
    st.title("👑 إضافة مستخدمين جدد للنظام")
    st.info("بصفتك المسؤول الوحيد، يمكنك إنشاء حسابات جديدة بأسماء وأكواد مختلفة للآخرين.")
    
    with st.form("add_user_form"):
        new_username = st.text_input("اسم المستخدم الجديد")
        new_password = st.text_input("كلمة السر / الكود للمستخدم الجديد")
        
        create_user_btn = st.form_submit_button("إنشاء الحساب الجديد")
        if create_user_btn:
            if new_username and new_password:
                if new_username in st.session_state["users_db"]:
                    st.error("⚠️ اسم المستخدم هذا موجود بالفعل!")
                else:
                    st.session_state["users_db"][new_username] = {
                        "password": new_password,
                        "role": "user"
                    }
                    save_users(st.session_state["users_db"])
                    st.success(f"🎉 تم إنشاء حساب جديد للمستخدم ({new_username}) بنجاح!")
            else:
                st.warning("يرجى ملء جميع الحقول.")
                
    st.subheader("📋 قائمة الحسابات المسجلة حالياً:")
    st.write(list(st.session_state["users_db"].keys()))
