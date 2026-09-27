import streamlit as st
import json
import os
import pandas as pd
from datetime import date, datetime
from google import genai

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتصميم العام
# ---------------------------------------------------------
st.set_page_config(
    page_title="منصة خطوة المتكاملة | التقييم والأرشيف الأرطوفوني",
    page_icon="👣",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تخصيص الاتجاه إلى العربية والواجهة بـ CSS
st.markdown("""
    <styleProcess>
    .main { text-align: right; direction: rtl; }
    div[data-testid="stSidebar"] { text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .metric-card {
        background-color: #f8f9fa;
        border-right: 5px solid #007bff;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </styleProcess>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. ملفات وقواعد البيانات والحفظ التلقائي
# ---------------------------------------------------------
USERS_FILE = "users_db.json"
DATA_FILE = "clinic_data.json"

def load_users():
    """تحميل قائمة الحسابات والمسؤولين"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # الحساب الأساسي للمسؤول الأول
    return {
        "malia benflis": {
            "password": "0660451073",
            "role": "admin",
            "full_name": "مالية بن فليس",
            "created_at": str(date.today())
        }
    }

def save_users(users_data):
    """حفظ الحسابات تلقائياً"""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_data, f, ensure_ascii=False, indent=4)

def load_all_data():
    """تحميل كل بيانات الأطفال والجلسات المقسمة حسب الحسابات"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_all_data(all_data):
    """حفظ بيانات العيادة تلقائياً"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)

# تهيئة المتغيرات في الجلسة (Session State)
if "users_db" not in st.session_state:
    st.session_state["users_db"] = load_users()

if "all_data" not in st.session_state:
    st.session_state["all_data"] = load_all_data()

# ---------------------------------------------------------
# 3. نظام الأمان وتسجيل الدخول المحمي
# ---------------------------------------------------------
def check_login():
    if "authenticated_user" not in st.session_state:
        st.session_state["authenticated_user"] = None

    if st.session_state["authenticated_user"] is None:
        st.markdown("<h1 style='text-align: center;'>👣 منصة خطوة الذكية</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: #555;'>نظام التقييم والتأهيل الأرطوفوني</h3>", unsafe_allow_html=True)
        st.write("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.subheader("🔒 تسجيل الدخول")
            username_input = st.text_input("اسم المستخدم أو اسم المختص")
            password_input = st.text_input("كلمة المرور / الكود", type="password")
            
            if st.button("دخول إلى النظام", use_container_width=True):
                users = st.session_state["users_db"]
                if username_input in users and users[username_input]["password"] == password_input:
                    st.session_state["authenticated_user"] = username_input
                    st.success(f"مرحباً بك {users[username_input].get('full_name', username_input)}!")
                    st.rerun()
                else:
                    st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة!")
        return False
    return True

if not check_login():
    st.stop()

# ---------------------------------------------------------
# 4. تخصيص المساحة الخاصة لكل مختص / مستخدم
# ---------------------------------------------------------
current_user = st.session_state["authenticated_user"]
user_info = st.session_state["users_db"][current_user]
user_role = user_info.get("role", "user")

# ضمان وجود ملف بيانات خاص بالمستخدم الحالي
if current_user not in st.session_state["all_data"]:
    st.session_state["all_data"][current_user] = {
        "children": [],
        "sessions": [],
        "evaluations": [],
        "appointments": []
    }

user_data = st.session_state["all_data"][current_user]

# ---------------------------------------------------------
# 5. القائمة الجانبية والشريط التوجيهي
# ---------------------------------------------------------
st.sidebar.title("منصة خطوة 👣")
st.sidebar.markdown(f"👤 **المختص:** `{user_info.get('full_name', current_user)}`")
st.sidebar.markdown(f"الرتبة: **{'مسؤول النظام (Admin)' if user_role == 'admin' else 'مختص أرطوفوني'}**")
st.sidebar.write("---")

menu_options = [
    "📊 لوحة القيادة والمواعيد",
    "➕ تسجيل طفل جديد",
    "📋 إجراء تقييم أرطوفوني",
    "📝 تسجيل الجلسات الميدانية",
    "🔍 أرشيف الأطفال والسجلات",
    "🤖 المساعد الذكي (Gemini AI)",
    "⚙️ إعدادات الحساب"
]

if user_role == "admin":
    menu_options.append("👑 إدارة الحسابات والمستخدمين")

menu = st.sidebar.radio("القائمة الرئيسية", menu_options)

st.sidebar.write("---")
if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
    st.session_state["authenticated_user"] = None
    st.rerun()

# ---------------------------------------------------------
# 6. تفاصيل ووظائف الصفحات
# ---------------------------------------------------------

# --- 1️⃣ لوحة القيادة والمواعيد ---
if menu == "📊 لوحة القيادة والمواعيد":
    st.title("📊 لوحة قيادة العيادة")
    st.caption("ملخص نشاطك الأرطوفوني والبيانات المحفوظة تلقائياً")
    
    total_children = len(user_data["children"])
    total_sessions = len(user_data["sessions"])
    total_evals = len(user_data.get("evaluations", []))
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي الأطفال المسجلين", f"{total_children} طفل")
    c2.metric("الجلسات المنجزة", f"{total_sessions} جلسة")
    c3.metric("التقييمات المكتملة", f"{total_evals} تقييم")
    c4.metric("حالة الحفظ التلقائي", "نشط 🟢")
    
    st.write("---")
    st.subheader("📅 المواعيد القادمة")
    
    col_app1, col_app2 = st.columns([2, 1])
    with col_app1:
        if user_data.get("appointments"):
            st.dataframe(pd.DataFrame(user_data["appointments"]), use_container_width=True)
        else:
            st.info("لا توجد مواعيد مسجلة حالياً.")
            
    with col_app2:
        with st.form("add_appointment_form"):
            st.write("➕ إضافة موعد جديد")
            app_child = st.selectbox("اختر الطفل", [c["name"] for c in user_data["children"]] if user_data["children"] else ["لا يوجد أطفال"])
            app_date = st.date_input("تاريخ الموعد")
            app_time = st.time_input("توقيت الجلسة")
            app_submit = st.form_submit_button("حفظ الموعد")
            
            if app_submit and app_child != "لا يوجد أطفال":
                user_data.setdefault("appointments", []).append({
                    "child": app_child,
                    "date": str(app_date),
                    "time": str(app_time)
                })
                save_all_data(st.session_state["all_data"])
                st.success("تم حفظ الموعد تلقائياً!")
                st.rerun()

# --- 2️⃣ تسجيل طفل جديد ---
elif menu == "➕ تسجيل طفل جديد":
    st.title("➕ تسجيل طفل جديد في سجلاتك")
    
    with st.form("add_child_full_form"):
        col1, col2 = st.columns(2)
        with col1:
            child_name = st.text_input("اسم الطفل الكامل *")
            birth_date = st.date_input("تاريخ الميلاد")
            gender = st.selectbox("الجنس", ["ذكر", "أنثى"])
            school_level = st.text_input("المستوى الدراسي / الروضة")
            
        with col2:
            parent_name = st.text_input("اسم ولي الأمر")
            phone = st.text_input("رقم الهاتف للتواصل")
            address = st.text_input("العنوان")
            medical_history = st.text_area("السوابق الطبية أو الوراثية")

        notes = st.text_area("سبب الاستشارة والأعراض الأولى")
        
        submitted = st.form_submit_button("حفظ بيانات الطفل تلقائياً")
        if submitted:
            if child_name:
                new_child = {
                    "id": len(user_data["children"]) + 1,
                    "name": child_name,
                    "birth_date": str(birth_date),
                    "gender": gender,
                    "school_level": school_level,
                    "parent_name": parent_name,
                    "phone": phone,
                    "address": address,
                    "medical_history": medical_history,
                    "notes": notes,
                    "created_at": str(date.today())
                }
                user_data["children"].append(new_child)
                save_all_data(st.session_state["all_data"])
                st.success(f"✅ تم تسجيل الحفظ التلقائي للطفل ({child_name}) بنجاح!")
            else:
                st.warning("يرجى كتابة اسم الطفل على الأقل.")

# --- 3️⃣ إجراء تقييم أرطوفوني ---
elif menu == "📋 إجراء تقييم أرطوفوني":
    st.title("📋 استمارة التقييم التشخيصي الأرطوفوني")
    
    if not user_data["children"]:
        st.warning("⚠️ يرجى إضافة طفل أولاً من قائمة 'تسجيل طفل جديد'.")
    else:
        child_names = [c["name"] for c in user_data["children"]]
        selected_child = st.selectbox("اختر الطفل المقيَّم", child_names)
        
        with st.form("evaluation_form"):
            st.subheader("1. الجانب اللغوي والسمعي")
            lang_comprehension = st.select_slider("الفهم اللغوي", options=["ضعيف جداً", "ضعيف", "متوسط", "جيد", "ممتاز"])
            lang_expression = st.select_slider("التعبير اللغوي والشفهي", options=["ضعيف جداً", "ضعيف", "متوسط", "جيد", "ممتاز"])
            articulation = st.multiselect("مشاكل النطق والاصوات (إن وجدت)", ["اضطراب التأتأة", "الحذف", "الإبدال", "التحريف/التبديل", "الخنف", "تأخر لغوي كلي"])
            
            st.subheader("2. التواصل والسلوك")
            eye_contact = st.selectbox("التواصل البصري", ["طبيعي وجيد", "متقطع", "نادر / معدوم"])
            behavior = st.multiselect("الملاحظات السلوكية", ["فرط حركة", "تشتت انتباه", "انطواء", "عدوانية", "استجابة ممتازة"])
            
            st.subheader("3. التوصيات الخطة العلاجية")
            recommendations = st.text_area("التوصيات والأهداف الأرطوفونية المقترحة")
            
            eval_submit = st.form_submit_button("حفظ التقييم الأرطوفوني")
            if eval_submit:
                new_eval = {
                    "child_name": selected_child,
                    "date": str(date.today()),
                    "comprehension": lang_comprehension,
                    "expression": lang_expression,
                    "articulation": articulation,
                    "eye_contact": eye_contact,
                    "behavior": behavior,
                    "recommendations": recommendations
                }
                user_data.setdefault("evaluations", []).append(new_eval)
                save_all_data(st.session_state["all_data"])
                st.success("✅ تم حفظ التقييم الأرطوفوني تلقائياً في ملف الطفل!")

# --- 4️⃣ تسجيل الجلسات الميدانية ---
elif menu == "📝 تسجيل الجلسات الميدانية":
    st.title("📝 متابعة وتأهيل الجلسات اليومية")
    
    if not user_data["children"]:
        st.warning("⚠️ يرجى إضافة طفل أولاً.")
    else:
        selected_child = st.selectbox("اختر الطفل", [c["name"] for c in user_data["children"]])
        
        with st.form("session_log_form"):
            session_number = st.number_input("رقم الجلسة", min_value=1, value=1)
            session_date = st.date_input("تاريخ الجلسة", value=date.today())
            targets = st.text_area("الأهداف المستهدفة في الجلسة")
            progress = st.select_slider("مدى استجابة الطفل وتطوره", options=["لم يستجب", "استجابة بسيطة", "استجابة متوسطة", "تحقق الهدف"])
            next_plan = st.text_area("خطة الجلسة القادمة والتوصيات للأهل")
            
            save_session = st.form_submit_button("تسجيل الجلسة وحفظها")
            if save_session:
                new_session = {
                    "child_name": selected_child,
                    "session_number": session_number,
                    "date": str(session_date),
                    "targets": targets,
                    "progress": progress,
                    "next_plan": next_plan
                }
                user_data["sessions"].append(new_session)
                save_all_data(st.session_state["all_data"])
                st.success("✅ تم حفظ تقرير الجلسة بنجاح!")

# --- 5️⃣ أرشيف الأطفال والسجلات ---
elif menu == "🔍 أرشيف الأطفال والسجلات":
    st.title("🔍 أرشيف الأطفال وسجل البيانات المحفوظة")
    
    tab1, tab2, tab3 = st.tabs(["📑 قائمة الأطفال", "📊 سجل الجلسات", "📋 التقييمات المحفوظة"])
    
    with tab1:
        if user_data["children"]:
            st.dataframe(pd.DataFrame(user_data["children"]), use_container_width=True)
        else:
            st.info("لا توجد بيانات أطفال مسجلة بعد.")
            
    with tab2:
        if user_data["sessions"]:
            st.dataframe(pd.DataFrame(user_data["sessions"]), use_container_width=True)
        else:
            st.info("لا توجد جلسات مسجلة بعد.")

    with tab3:
        if user_data.get("evaluations"):
            st.dataframe(pd.DataFrame(user_data["evaluations"]), use_container_width=True)
        else:
            st.info("لا توجد تقييمات محفوظة بعد.")

# --- 6️⃣ المساعد الذكي (Gemini AI) ---
elif menu == "🤖 المساعد الذكي (Gemini AI)":
    st.title("🤖 المساعد الأرطوفوني الذكي")
    st.caption("تحليل الحالات واقتراح التمارين التأهيلية بالذكاء الاصطناعي")
    
    api_key = st.text_input("مفتاح Google Gemini API (اختياري لتفعيل الذكاء الاصطناعي)", type="password")
    prompt_query = st.text_area("اطرح سؤالك الأرطوفوني أو ادخل حالة الطفل لتحليلها:")
    
    if st.button("تحليل واستشارة الذكاء الاصطناعي"):
        if not prompt_query:
            st.warning("يرجى كتابة السؤال أو الحالة أولاً.")
        elif not api_key:
            st.error("يرجى إدخال مفتاح Gemini API لتشغيل هذه الميزة.")
        else:
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt_query,
                )
                st.markdown("### 💡 التحليل والتوصيات الأرطوفونية:")
                st.write(response.text)
            except Exception as e:
                st.error(f"حدث خطأ أثناء الاتصال بالذكاء الاصطناعي: {e}")

# --- 7️⃣ إعدادات الحساب ---
elif menu == "⚙️ إعدادات الحساب":
    st.title("⚙️ إعدادات حسابك الشخصي")
    st.write(f"المستخدم الحالي: **{current_user}**")
    
    with st.form("change_password_form"):
        st.subheader("تغيير كلمة المرور / الكود الخاص بك")
        old_pass = st.text_input("كلمة المرور الحالية", type="password")
        new_pass = st.text_input("كلمة المرور الجديدة", type="password")
        confirm_pass = st.text_input("تأكيد كلمة المرور الجديدة", type="password")
        
        update_btn = st.form_submit_button("تحديث كلمة المرور")
        if update_btn:
            if user_info["password"] != old_pass:
                st.error("كلمة المرور الحالية غير صحيحة.")
            elif new_pass != confirm_pass or not new_pass:
                st.error("كلمات المرور الجديدة غير متطابقة.")
            else:
                st.session_state["users_db"][current_user]["password"] = new_pass
                save_users(st.session_state["users_db"])
                st.success("✅ تم تحديث كلمة المرور بنجاح!")

# --- 8️⃣ إدارة الحسابات والمستخدمين (للمسؤول فقط) ---
elif menu == "👑 إدارة الحسابات والمستخدمين" and user_role == "admin":
    st.title("👑 لوحة تحكم المسؤول | إدارة الحسابات والصلحيات")
    st.info("بصفتك المسؤول الرئيسي، يمكنك التحكم التام وإضافة مستخدمين جدد للنظام وتحديد أكوادهم.")
    
    t1, t2 = st.tabs(["➕ إنشاء حساب جديد", "📋 قائمة الحسابات المسجلة"])
    
    with t1:
        with st.form("create_new_user_admin"):
            new_username = st.text_input("اسم المستخدم الجديد (Login Username) *")
            new_fullname = st.text_input("الاسم الكامل للمختص / الموظف")
            new_password = st.text_input("كلمة المرور / الكود المخصص *", type="password")
            new_role = st.selectbox("الصلاحيات والنفوذ", ["user", "admin"], format_func=lambda x: "مختص أرطوفوني (عادي)" if x == "user" else "مسؤول نظام (Admin)")
            
            submit_user = st.form_submit_button("إنشاء وتفعيل الحساب")
            if submit_user:
                if new_username and new_password:
                    if new_username in st.session_state["users_db"]:
                        st.error("⚠️ اسم المستخدم هذا موجود ومسجل من قبل.")
                    else:
                        st.session_state["users_db"][new_username] = {
                            "password": new_password,
                            "role": new_role,
                            "full_name": new_fullname if new_fullname else new_username,
                            "created_at": str(date.today())
                        }
                        save_users(st.session_state["users_db"])
                        st.success(f"🎉 تم إنشاء وتفعيل حساب ({new_username}) بنجاح!")
                else:
                    st.warning("يرجى ملء كافة الحقول الأساسية.")
                    
    with t2:
        st.subheader("👥 الحسابات والأكواد الفعالة في النظام")
        users_list = []
        for uname, udata in st.session_state["users_db"].items():
            users_list.append({
                "اسم المستخدم": uname,
                "الاسم الكامل": udata.get("full_name", "-"),
                "الرتبة": "مسؤول نظام" if udata.get("role") == "admin" else "مختص",
                "تاريخ الإنشاء": udata.get("created_at", "-")
            })
        st.dataframe(pd.DataFrame(users_list), use_container_width=True)
