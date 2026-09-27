import streamlit as st
import json
import os
import pandas as pd
from datetime import date
from google import genai

# ==========================================
# 1. إعدادات الصفحة والتصميم الاحترافي (CSS)
# ==========================================
st.set_page_config(page_title="عيادة خطوة | النظام الأرطوفوني الشامل", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap');
    
    * { font-family: 'Tajawal', sans-serif !important; }
    
    .stApp { background-color: #f0f4f8; direction: rtl; text-align: right; }
    div[data-testid="stSidebar"] { background-color: #ffffff; border-left: 1px solid #e0e0e0; }
    
    /* تصميم البطاقات (Cards) */
    .dashboard-card {
        background: white; border-radius: 12px; padding: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px;
        border-right: 5px solid #0056b3; transition: transform 0.3s ease;
    }
    .dashboard-card:hover { transform: translateY(-5px); }
    .card-title { font-size: 1.2rem; color: #6c757d; margin-bottom: 10px; font-weight: 700;}
    .card-value { font-size: 2rem; color: #2c3e50; font-weight: 900; }
    
    /* تصميم الأزرار */
    .stButton>button {
        background-color: #0056b3; color: white; border-radius: 8px;
        padding: 10px 20px; font-weight: bold; border: none; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #004494; color: white; box-shadow: 0 4px 8px rgba(0,0,0,0.1);}
    
    /* العناوين */
    h1, h2, h3 { color: #1a252f; font-weight: 700; }
    hr { border-color: #dce1e6; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. إدارة قواعد البيانات (JSON)
# ==========================================
USERS_FILE = "users_db.json"
DATA_FILE = "clinic_data.json"

def load_data(file_name, default_data):
    if os.path.exists(file_name):
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return default_data

def save_data(file_name, data):
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if "users_db" not in st.session_state:
    st.session_state["users_db"] = load_data(USERS_FILE, {"malia benflis": {"password": "123", "role": "admin", "full_name": "الأخصائية مالية بن فليس"}})
if "all_data" not in st.session_state:
    st.session_state["all_data"] = load_data(DATA_FILE, {})

# ==========================================
# 3. شاشة تسجيل الدخول الأنيقة
# ==========================================
if st.session_state.get("authenticated_user") is None:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="background:white; padding:40px; border-radius:15px; box-shadow:0 10px 25px rgba(0,0,0,0.1); text-align:center;">
            <h1 style="color:#0056b3; font-size: 3rem;">🏥 عيادة خطوة</h1>
            <p style="color:#7f8c8d; font-size: 1.2rem;">النظام الأرطوفوني الذكي لإدارة العيادات</p>
            <hr>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        username = st.text_input("👤 اسم المستخدم")
        password = st.text_input("🔑 كلمة المرور", type="password")
        
        if st.button("تسجيل الدخول 🚀", use_container_width=True):
            users = st.session_state["users_db"]
            if username in users and users[username]["password"] == password:
                st.session_state["authenticated_user"] = username
                st.rerun()
            else:
                st.error("❌ بيانات الدخول غير صحيحة!")
    st.stop()

current_user = st.session_state["authenticated_user"]
user_info = st.session_state["users_db"][current_user]

if current_user not in st.session_state["all_data"]:
    st.session_state["all_data"][current_user] = {"patients": [], "sessions": []}
db = st.session_state["all_data"][current_user]

# ==========================================
# 4. القائمة الجانبية (Sidebar Navigation)
# ==========================================
st.sidebar.markdown(f"### 👩‍⚕️ مرحباً، {user_info.get('full_name', current_user)}")
st.sidebar.write("---")

menu = st.sidebar.radio("📌 لوحة التحكم", [
    "🏠 الرئيسية والإحصائيات",
    "👥 إدارة المرضى والملفات",
    "🧠 المستشار الذكي (تحليل الحالات)",
    "📚 مكتبة الموارد والأدوات",
    "📝 سجل الجلسات والمتابعة"
])

st.sidebar.write("---")
if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
    st.session_state["authenticated_user"] = None
    st.rerun()

# ==========================================
# 5. صفحات النظام (الصفحة الرئيسية)
# ==========================================
if menu == "🏠 الرئيسية والإحصائيات":
    st.title("🏠 نظرة عامة على العيادة")
    
    total_patients = len(db["patients"])
    total_sessions = len(db["sessions"])
    
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"""
        <div class="dashboard-card">
            <div class="card-title">إجمالي الحالات المسجلة</div>
            <div class="card-value">{total_patients} طفل</div>
        </div>
    """, unsafe_allow_html=True)
    
    c2.markdown(f"""
        <div class="dashboard-card" style="border-right-color: #27ae60;">
            <div class="card-title">الجلسات المنجزة</div>
            <div class="card-value">{total_sessions} جلسة</div>
        </div>
    """, unsafe_allow_html=True)
    
    c3.markdown(f"""
        <div class="dashboard-card" style="border-right-color: #f39c12;">
            <div class="card-title">حالة النظام</div>
            <div class="card-value">مستقر ومحمي 🔒</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.subheader("📅 آخر الحالات المسجلة")
    if db["patients"]:
        df = pd.DataFrame(db["patients"]).tail(5)
        st.dataframe(df[["name", "age", "diagnosis", "created_at"]], use_container_width=True)
    else:
        st.info("لم يتم تسجيل مرضى بعد.")

# ==========================================
# 6. إدارة المرضى
# ==========================================
elif menu == "👥 إدارة المرضى والملفات":
    st.title("👥 سجلات المرضى والتقييم")
    
    tab1, tab2 = st.tabs(["➕ إضافة حالة جديدة", "🔍 البحث في الأرشيف"])
    
    with tab1:
        with st.form("new_patient_form"):
            st.subheader("البيانات الشخصية والطبية")
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("اسم الطفل *")
            age = c2.number_input("العمر", min_value=1, max_value=20, value=5)
            gender = c3.selectbox("الجنس", ["ذكر", "أنثى"])
            
            diagnosis = st.selectbox("التشخيص المبدئي", ["تأخر لغوي", "اضطراب طيف التوحد (ASD)", "تأتأة (تلعثم)", "اضطرابات نطق (لدغات)", "صعوبات تعلم", "أخرى"])
            history = st.text_area("السوابق الطبية (حمل، ولادة، أمراض وراثية)")
            
            if st.form_submit_button("حفظ الملف الطبي"):
                if name:
                    db["patients"].append({
                        "id": len(db["patients"]) + 1, "name": name, "age": age, "gender": gender,
                        "diagnosis": diagnosis, "history": history, "created_at": str(date.today())
                    })
                    save_data(DATA_FILE, st.session_state["all_data"])
                    st.success("✅ تم حفظ الملف بنجاح!")
                else:
                    st.error("يرجى إدخال اسم الطفل.")
                    
    with tab2:
        if db["patients"]:
            st.dataframe(pd.DataFrame(db["patients"]), use_container_width=True)
        else:
            st.info("الأرشيف فارغ.")

# ==========================================
# 7. المستشار الذكي (أقوى ميزة - تحليل الحالات)
# ==========================================
elif menu == "🧠 المستشار الذكي (تحليل الحالات)":
    st.title("🧠 المستشار الأرطوفوني الذكي (AI)")
    st.markdown("""
    <div style="background:#e8f4f8; padding:15px; border-radius:10px; border-right: 5px solid #3498db; margin-bottom: 20px;">
        هذا القسم يستخدم الذكاء الاصطناعي. أدخل أعراض الطفل وملاحظاتك، وسيقوم المساعد بتحليل الحالة وإعطائك <b>خطة علاجية مقترحة، وأهداف الجلسات، ونصائح للأهل</b>.
    </div>
    """, unsafe_allow_html=True)
    
    api_key = st.text_input("🔑 أدخل مفتاح Google Gemini API لتفعيل المساعد:", type="password")
    
    st.subheader("📝 وصف الحالة")
    case_age = st.number_input("عمر الطفل (سنوات)", 1, 18, 4)
    case_symptoms = st.text_area("ما هي الأعراض والملاحظات؟ (مثال: لا ينطق حرف الراء، يتجنب التواصل البصري، حصيلة لغوية ضعيفة جداً...)")
    
    if st.button("🔍 تحليل الحالة واستخراج الخطة العلاجية", use_container_width=True):
        if not api_key:
            st.error("⚠️ يرجى إدخال مفتاح API للذكاء الاصطناعي أولاً.")
        elif not case_symptoms:
            st.warning("⚠️ يرجى وصف الأعراض.")
        else:
            with st.spinner("🤖 جاري تحليل الحالة واستخراج التوصيات العلمية..."):
                try:
                    prompt = f"""
                    أنت خبير أرطوفوني (Speech Therapist) مختص. 
                    لدينا طفل عمره {case_age} سنوات.
                    الأعراض والملاحظات: {case_symptoms}
                    
                    يرجى تقديم تقرير احترافي ومنسق يحتوي على:
                    1. التشخيص المبدئي المحتمل (الفرضيات).
                    2. الأهداف العلاجية قصيرة المدى وطويلة المدى.
                    3. اقتراح 3 تدريبات أو تمارين محددة للقيام بها في الجلسة.
                    4. نصائح توجيهية لأولياء الأمور لتطبيقها في المنزل.
                    """
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                    
                    st.success("✅ تم التحليل بنجاح!")
                    st.markdown("### 📄 التقرير الأرطوفوني المقترح:")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"حدث خطأ في الاتصال بالذكاء الاصطناعي: {e}")

# ==========================================
# 8. مكتبة الموارد والأدوات
# ==========================================
elif menu == "📚 مكتبة الموارد والأدوات":
    st.title("📚 مكتبة العيادة (أدوات، بطاقات، مراجع)")
    
    t1, t2, t3 = st.tabs(["🖼️ بطاقات التخاطب (Flashcards)", "📝 مقاييس واختبارات", "📖 مراجع وكتب"])
    
    with t1:
        st.subheader("بطاقات المجموعات الضمنية (للتدريب)")
        c1, c2, c3, c4 = st.columns(4)
        c1.button("🍎 فواكه وخضروات")
        c2.button("🦁 حيوانات الغابة")
        c3.button("🚗 وسائل النقل")
        c4.button("👕 الملابس")
        st.info("💡 يمكنك لاحقاً ربط هذه الأزرار بملفات PDF أو صور ليتم عرضها للطفل مباشرة من الشاشة.")
        
    with t2:
        st.subheader("نماذج التقييم السريع")
        st.checkbox("مقياس كارز (CARS) لتقييم التوحد")
        st.checkbox("اختبار بيبودي (PPVT) للحصيلة اللغوية")
        st.checkbox("استمارة دراسة الحالة الأرطوفونية الشاملة")
        
    with t3:
        st.subheader("الكتب المرجعية")
        st.markdown("- 📖 **كتاب:** اضطرابات النطق واللغة (د. فيصل الزراد)")
        st.markdown("- 📖 **كتاب:** التدخل المبكر والتربية الخاصة")
        st.markdown("- 📖 **دليل:** تدريبات أعضاء النطق والكلام")

# ==========================================
# 9. سجل الجلسات
# ==========================================
elif menu == "📝 سجل الجلسات والمتابعة":
    st.title("📝 تسجيل ومتابعة الجلسات")
    
    if not db["patients"]:
        st.warning("يرجى إضافة مرضى أولاً من قائمة إدارة المرضى.")
    else:
        patient_names = [p["name"] for p in db["patients"]]
        selected_patient = st.selectbox("اختر الطفل لتسجيل جلسته:", patient_names)
        
        with st.form("session_form"):
            session_date = st.date_input("تاريخ الجلسة")
            session_goals = st.text_input("أهداف الجلسة (مثال: التدريب على نطق صوت /س/)")
            patient_response = st.select_slider("استجابة الطفل", ["سيئة", "ضعيفة", "متوسطة", "جيدة", "ممتازة"])
            homework = st.text_area("الواجب المنزلي للأهل")
            
            if st.form_submit_button("حفظ الجلسة"):
                db["sessions"].append({
                    "patient": selected_patient, "date": str(session_date), 
                    "goals": session_goals, "response": patient_response, "homework": homework
                })
                save_data(DATA_FILE, st.session_state["all_data"])
                st.success("✅ تم تسجيل الجلسة بنجاح!")
        
        st.subheader("📊 سجل جلسات العيادة")
        if db["sessions"]:
            st.dataframe(pd.DataFrame(db["sessions"]), use_container_width=True)
