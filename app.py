import streamlit as st
import json
import os
import hashlib
import pandas as pd
import plotly.express as px
from datetime import datetime, date
from google import genai
import shutil

# ==========================================
# 1. إعدادات الصفحة وواجهة المستخدم (UI/UX)
# ==========================================
st.set_page_config(page_title="عيادة خطوة | النظام الأرطوفوني الشامل", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

# تصميم CSS احترافي شامل لجميع العناصر
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap');
    
    * { font-family: 'Tajawal', sans-serif !important; direction: rtl; text-align: right; }
    body, .stApp { background-color: #f4f7f6; }
    div[data-testid="stSidebar"] { background-color: #1e293b; color: #ffffff; }
    div[data-testid="stSidebar"] * { color: #f8fafc !important; }
    
    /* البطاقات التفاعلية */
    .metric-card {
        background: #ffffff; border-radius: 15px; padding: 25px; margin-bottom: 20px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.05); border-right: 6px solid #3b82f6;
        transition: transform 0.3s, box-shadow 0.3s;
    }
    .metric-card:hover { transform: translateY(-5px); box-shadow: 0 15px 25px rgba(0,0,0,0.1); }
    .metric-title { font-size: 1.1rem; color: #64748b; font-weight: 700; margin-bottom: 10px;}
    .metric-value { font-size: 2.5rem; color: #0f172a; font-weight: 900; }
    
    /* الأزرار الاحترافية */
    .stButton>button {
        background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white !important;
        border-radius: 10px; padding: 12px 24px; font-size: 1.1rem; font-weight: bold;
        border: none; box-shadow: 0 4px 6px rgba(37,99,235,0.3); transition: all 0.3s;
    }
    .stButton>button:hover { background: linear-gradient(135deg, #1d4ed8, #1e40af); transform: scale(1.02); }
    
    /* الجداول والنصوص */
    .stDataFrame { border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    h1, h2, h3 { color: #0f172a; font-weight: 900; }
    hr { border: 0; height: 1px; background: #e2e8f0; margin: 30px 0; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. نظام الأمان وإدارة قواعد البيانات (Security & DB)
# ==========================================
USERS_FILE = "users_db.json"
DATA_FILE = "clinic_data.json"
BACKUP_DIR = "backups"

# تشفير كلمات المرور (حماية من الاختراق)
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# إنشاء مجلد النسخ الاحتياطي إذا لم يكن موجوداً
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

def create_backup():
    """نظام نسخ احتياطي تلقائي للبيانات لمنع ضياعها"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if os.path.exists(DATA_FILE):
        shutil.copy(DATA_FILE, os.path.join(BACKUP_DIR, f"clinic_data_backup_{timestamp}.json"))

def load_data(file_path, default_structure):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"⚠️ خطأ في قراءة قاعدة البيانات: {e}")
    return default_structure

def save_data(file_path, data):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        if file_path == DATA_FILE:
            create_backup() # أخذ نسخة احتياطية عند كل تغيير مهم
    except Exception as e:
        st.error(f"⚠️ فشل في حفظ البيانات: {e}")

# تهيئة قواعد البيانات
default_users = {
    "malia benflis": {
        "password": hash_password("0660451073"), 
        "role": "admin", 
        "full_name": "الأخصائية مالية بن فليس",
        "phone": "0660451073",
        "created_at": str(date.today())
    }
}

if "users_db" not in st.session_state:
    st.session_state["users_db"] = load_data(USERS_FILE, default_users)
if "all_data" not in st.session_state:
    st.session_state["all_data"] = load_data(DATA_FILE, {})

# ==========================================
# 3. نظام تسجيل الدخول المحمي بالكامل
# ==========================================
if st.session_state.get("authenticated_user") is None:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
        <div style="background:white; padding:40px; border-radius:20px; box-shadow:0 20px 40px rgba(0,0,0,0.1); text-align:center;">
            <h1 style="color:#2563eb; font-size: 3.5rem; margin-bottom: 0;">🏥 منصة خطوة</h1>
            <p style="color:#64748b; font-size: 1.2rem; margin-top: 10px;">النظام الذكي الشامل للعيادات الأرطوفونية</p>
            <hr>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        
        with st.form("login_form"):
            username = st.text_input("👤 اسم المستخدم")
            password = st.text_input("🔑 كلمة المرور", type="password")
            submit = st.form_submit_button("تسجيل الدخول للنظام 🔒", use_container_width=True)
            
            if submit:
                users = st.session_state["users_db"]
                hashed_input = hash_password(password)
                
                if username in users and users[username]["password"] == hashed_input:
                    st.session_state["authenticated_user"] = username
                    st.rerun()
                else:
                    st.error("❌ بيانات الدخول غير صحيحة، يرجى المحاولة مجدداً.")
    st.stop()

# ==========================================
# 4. إعداد مساحة عمل المستخدم (Data Isolation)
# ==========================================
current_user = st.session_state["authenticated_user"]
user_info = st.session_state["users_db"][current_user]
user_role = user_info.get("role", "therapist")

# بناء هيكل البيانات المتقدم لكل مستخدم
if current_user not in st.session_state["all_data"]:
    st.session_state["all_data"][current_user] = {
        "patients": [], "sessions": [], "evaluations": [], "finances": []
    }
db = st.session_state["all_data"][current_user]

# ==========================================
# 5. القائمة الجانبية (Sidebar) والملاحة
# ==========================================
st.sidebar.markdown(f"## 👩‍⚕️ {user_info.get('full_name', current_user)}")
st.sidebar.markdown(f"💼 **الرتبة:** {'المدير العام (Admin)' if user_role == 'admin' else 'أخصائي أرطوفوني'}")
st.sidebar.write("---")

menu_items = [
    "📊 لوحة القيادة والمؤشرات",
    "👥 إدارة المرضى (CRM)",
    "📋 التقييمات والمقاييس العلمية",
    "📝 سجل الجلسات والمتابعة",
    "💰 الإدارة المالية والفوترة",
    "🤖 المساعد الذكي (AI Consultant)",
    "📚 مكتبة العيادة والأدوات",
    "⚙️ إعدادات الحساب والأمان"
]

if user_role == "admin":
    menu_items.append("👑 إدارة النظام والمستخدمين")

menu = st.sidebar.radio("📌 القائمة الرئيسية", menu_items)
st.sidebar.write("---")

if st.sidebar.button("🚪 تسجيل الخروج بأمان", use_container_width=True):
    st.session_state["authenticated_user"] = None
    st.rerun()

# ==========================================
# 6. محرك الصفحات (Core Engine)
# ==========================================

# ------------------------------------------
# الصفحة 1: لوحة القيادة والمؤشرات
# ------------------------------------------
if menu == "📊 لوحة القيادة والمؤشرات":
    st.title("📊 لوحة القيادة (Dashboard)")
    
    patients_count = len(db.get("patients", []))
    sessions_count = len(db.get("sessions", []))
    total_revenue = sum([f["amount"] for f in db.get("finances", []) if f["type"] == "مداخيل"])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f'<div class="metric-card" style="border-color: #3b82f6;"><div class="metric-title">المرضى المسجلين</div><div class="metric-value">{patients_count}</div></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="metric-card" style="border-color: #10b981;"><div class="metric-title">الجلسات المنجزة</div><div class="metric-value">{sessions_count}</div></div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="metric-card" style="border-color: #f59e0b;"><div class="metric-title">التقييمات المكتملة</div><div class="metric-value">{len(db.get("evaluations", []))}</div></div>', unsafe_allow_html=True)
    col4.markdown(f'<div class="metric-card" style="border-color: #8b5cf6;"><div class="metric-title">إجمالي المداخيل</div><div class="metric-value">{total_revenue} د.ج</div></div>', unsafe_allow_html=True)

    st.write("---")
    st.subheader("📈 نشاط العيادة (نمو الجلسات)")
    
    if sessions_count > 0:
        df_sessions = pd.DataFrame(db["sessions"])
        df_sessions['date'] = pd.to_datetime(df_sessions['date'])
        daily_sessions = df_sessions.groupby('date').size().reset_index(name='count')
        fig = px.line(daily_sessions, x='date', y='count', title='عدد الجلسات عبر الزمن', markers=True, template="plotly_white")
        fig.update_traces(line_color='#2563eb', line_width=3, marker_size=8)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("لا توجد بيانات كافية لعرض الرسم البياني.")

# ------------------------------------------
# الصفحة 2: إدارة المرضى (CRM)
# ------------------------------------------
elif menu == "👥 إدارة المرضى (CRM)":
    st.title("👥 السجل الطبي الشامل (CRM)")
    
    t1, t2 = st.tabs(["➕ تسجيل حالة جديدة", "🔍 البحث وإدارة الملفات"])
    
    with t1:
        st.markdown("### البيانات الشخصية والطبية للطفل")
        with st.form("patient_registration"):
            c1, c2, c3 = st.columns(3)
            p_name = c1.text_input("الاسم الكامل *")
            p_dob = c2.date_input("تاريخ الميلاد", min_value=date(2000, 1, 1), max_value=date.today())
            p_gender = c3.selectbox("الجنس", ["ذكر", "أنثى"])
            
            c4, c5 = st.columns(2)
            p_parent = c4.text_input("اسم ولي الأمر")
            p_phone = c5.text_input("رقم الهاتف للتواصل *")
            
            p_diagnosis = st.selectbox("التصنيف الأساسي", ["تأخر نمو لغوي (Retard de langage)", "طيف التوحد (TSA)", "تلعثم/تأتأة (Bégaiement)", "اضطرابات نطق (Troubles d'articulation)", "إعاقة سمعية", "متلازمة داون", "صعوبات تعلم", "أخرى"])
            p_history = st.text_area("تاريخ الحالة (الحمل، الولادة، الأمراض، النمو الحركي)")
            
            if st.form_submit_button("حفظ الملف وإنشاء السجل"):
                if p_name and p_phone:
                    patient_id = f"PAT-{datetime.now().strftime('%y%m%d%H%M%S')}"
                    db["patients"].append({
                        "id": patient_id, "name": p_name, "dob": str(p_dob), "gender": p_gender,
                        "parent": p_parent, "phone": p_phone, "diagnosis": p_diagnosis,
                        "history": p_history, "created_at": str(date.today()), "status": "نشط"
                    })
                    save_data(DATA_FILE, st.session_state["all_data"])
                    st.success(f"✅ تم فتح ملف طبي جديد للطفل: {p_name} برقم {patient_id}")
                else:
                    st.error("⚠️ يرجى ملء الحقول الإجبارية (الاسم ورقم الهاتف).")

    with t2:
        if db["patients"]:
            df_pat = pd.DataFrame(db["patients"])
            search_term = st.text_input("🔍 ابحث بالاسم أو الهاتف...")
            if search_term:
                df_pat = df_pat[df_pat['name'].str.contains(search_term) | df_pat['phone'].str.contains(search_term)]
            
            st.dataframe(df_pat[["id", "name", "diagnosis", "phone", "status", "created_at"]], use_container_width=True)
        else:
            st.info("سجل المرضى فارغ حالياً.")

# ------------------------------------------
# الصفحة 3: التقييمات والمقاييس
# ------------------------------------------
elif menu == "📋 التقييمات والمقاييس العلمية":
    st.title("📋 المقاييس والاختبارات الأرطوفونية")
    
    if not db["patients"]:
        st.warning("⚠️ يجب إضافة مرضى أولاً لإجراء التقييمات.")
    else:
        patients_dict = {p["id"]: p["name"] for p in db["patients"]}
        selected_id = st.selectbox("اختر الطفل للتقييم", list(patients_dict.keys()), format_func=lambda x: patients_dict[x])
        
        test_type = st.radio("اختر نوع المقياس:", ["التقييم اللغوي الشامل", "مقياس كارز (CARS) للتوحد - مصغر", "فحص النطق (Articulation)"])
        
        with st.form("evaluation_form"):
            st.subheader(f"إجراء {test_type}")
            
            if test_type == "التقييم اللغوي الشامل":
                comp = st.slider("مستوى الفهم اللغوي (10=ممتاز، 0=معدوم)", 0, 10, 5)
                expr = st.slider("مستوى التعبير الشفهي (10=ممتاز، 0=معدوم)", 0, 10, 5)
                prag = st.slider("التوظيف البراغماتي (الاجتماعي)", 0, 10, 5)
                notes = st.text_area("ملاحظات الأخصائي")
                score_data = {"الفهم": comp, "التعبير": expr, "البراغماتية": prag}
                
            elif test_type == "مقياس كارز (CARS) للتوحد - مصغر":
                st.info("تقييم من 1 إلى 4 لكل بند (1=طبيعي، 4=شاذ بشدة)")
                c_rel = st.number_input("العلاقة بالناس", 1.0, 4.0, 1.0, 0.5)
                c_imi = st.number_input("التقليد", 1.0, 4.0, 1.0, 0.5)
                c_emo = st.number_input("الاستجابة العاطفية", 1.0, 4.0, 1.0, 0.5)
                c_bod = st.number_input("استخدام الجسم", 1.0, 4.0, 1.0, 0.5)
                notes = st.text_area("ملاحظات إضافية")
                total_score = c_rel + c_imi + c_emo + c_bod
                score_data = {"مجموع النقاط (المصغر)": total_score}
                st.write(f"**المجموع المؤقت:** {total_score} (من 16)")

            elif test_type == "فحص النطق (Articulation)":
                errors = st.multiselect("الأخطاء الصوتية المرصودة", ["حذف", "إبدال", "تحريف", "إضافة"])
                phonemes = st.text_input("الأصوات المتأثرة (مثال: ر، س، ش)")
                notes = st.text_area("وضع أعضاء النطق (اللسان، الأسنان، الشفاه)")
                score_data = {"الأخطاء": errors, "الأصوات": phonemes}

            if st.form_submit_button("حفظ نتيجة التقييم في الملف"):
                db["evaluations"].append({
                    "eval_id": f"EV-{datetime.now().strftime('%y%m%d%H%M')}",
                    "patient_id": selected_id,
                    "patient_name": patients_dict[selected_id],
                    "type": test_type,
                    "date": str(date.today()),
                    "scores": score_data,
                    "notes": notes
                })
                save_data(DATA_FILE, st.session_state["all_data"])
                st.success("✅ تم حفظ التقييم بنجاح في أرشيف المريض!")

# ------------------------------------------
# الصفحة 4: سجل الجلسات والمتابعة
# ------------------------------------------
elif menu == "📝 سجل الجلسات والمتابعة":
    st.title("📝 المتابعة اليومية للجلسات")
    
    if not db["patients"]:
        st.warning("⚠️ الأرشيف فارغ.")
    else:
        patients_dict = {p["id"]: p["name"] for p in db["patients"]}
        
        col_log, col_history = st.columns([1, 1])
        with col_log:
            st.subheader("تدوين جلسة جديدة")
            with st.form("session_log"):
                s_pat = st.selectbox("المريض", list(patients_dict.keys()), format_func=lambda x: patients_dict[x])
                s_date = st.date_input("التاريخ")
                s_type = st.selectbox("نوع الجلسة", ["تقييمية", "علاجية", "إرشاد أُسري"])
                s_goals = st.text_area("أهداف الجلسة (مثال: إخراج صوت الراء من مخرج صحيح)")
                s_progress = st.slider("نسبة الإنجاز واستجابة الطفل (%)", 0, 100, 50)
                s_homework = st.text_area("توصيات وبرنامج المنزل")
                
                if st.form_submit_button("حفظ الجلسة وتحديث السجل"):
                    db["sessions"].append({
                        "session_id": f"SS-{datetime.now().strftime('%y%m%d%H%M')}",
                        "patient_id": s_pat, "patient_name": patients_dict[s_pat],
                        "date": str(s_date), "type": s_type,
                        "goals": s_goals, "progress": s_progress, "homework": s_homework
                    })
                    save_data(DATA_FILE, st.session_state["all_data"])
                    st.success("✅ تم توثيق الجلسة بنجاح!")
        
        with col_history:
            st.subheader("سجل آخر الجلسات")
            if db["sessions"]:
                df_sess = pd.DataFrame(db["sessions"]).sort_values("date", ascending=False).head(10)
                st.dataframe(df_sess[["patient_name", "date", "progress", "type"]], use_container_width=True)
            else:
                st.info("لم يتم تسجيل أي جلسة بعد.")

# ------------------------------------------
# الصفحة 5: الإدارة المالية
# ------------------------------------------
elif menu == "💰 الإدارة المالية والفوترة":
    st.title("💰 الصندوق المالي للعيادة")
    
    st.markdown("إدارة المداخيل والمصاريف الخاصة بعيادتك للحفاظ على استقرارك المالي.")
    
    c1, c2 = st.columns(2)
    with c1:
        with st.form("finance_form"):
            f_type = st.radio("العملية", ["مداخيل", "مصاريف"])
            f_desc = st.text_input("البيان / الوصف (مثال: دفع جلسة علاجية، شراء بطاقات...)")
            f_amount = st.number_input("المبلغ (د.ج)", min_value=0)
            f_date = st.date_input("التاريخ")
            
            if st.form_submit_button("تسجيل العملية"):
                if f_amount > 0 and f_desc:
                    db["finances"].append({
                        "date": str(f_date), "type": f_type, "desc": f_desc, "amount": f_amount
                    })
                    save_data(DATA_FILE, st.session_state["all_data"])
                    st.success("✅ تمت العملية بنجاح!")
                else:
                    st.error("يرجى إدخال الوصف والمبلغ.")
    
    with c2:
        total_in = sum([f["amount"] for f in db.get("finances", []) if f["type"] == "مداخيل"])
        total_out = sum([f["amount"] for f in db.get("finances", []) if f["type"] == "مصاريف"])
        net_profit = total_in - total_out
        
        st.markdown(f'<div class="metric-card"><div class="metric-title">إجمالي المداخيل</div><div class="metric-value" style="color:#10b981;">{total_in} د.ج</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-card"><div class="metric-title">إجمالي المصاريف</div><div class="metric-value" style="color:#ef4444;">{total_out} د.ج</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-card"><div class="metric-title">صافي الأرباح</div><div class="metric-value" style="color:{"#10b981" if net_profit >= 0 else "#ef4444"};">{net_profit} د.ج</div></div>', unsafe_allow_html=True)

# ------------------------------------------
# الصفحة 6: المساعد الذكي (AI)
# ------------------------------------------
elif menu == "🤖 المساعد الذكي (AI Consultant)":
    st.title("🤖 المستشار الأرطوفوني الذكي (مدعوم بـ Google Gemini)")
    
    st.info("💡 هذا النظام يحلل الحالات المعقدة، يقترح خطط علاجية، ويكتب تقارير احترافية.")
    
    api_key = st.text_input("🔑 مفتاح التفعيل (API Key)", type="password", help="أدخل مفتاح Gemini الخاص بك لتفعيل العقل المدبر")
    
    query_type = st.selectbox("ماذا تريد من المساعد أن يفعل؟", ["تحليل حالة وبناء خطة علاجية", "اقتراح تمارين نطق محددة", "صياغة تقرير للأهل"])
    context = st.text_area("أدخل تفاصيل الحالة (الأعراض، العمر، الملاحظات...)", height=150)
    
    if st.button("🧠 تشغيل الذكاء الاصطناعي", use_container_width=True):
        if not api_key:
            st.error("يرجى إدخال مفتاح API للعمل.")
        elif not context:
            st.warning("يرجى إدخال معلومات الحالة أولاً.")
        else:
            with st.spinner("🤖 جاري تحليل البيانات واستخراج التوصيات الدقيقة..."):
                try:
                    prompt = f"أنت خبير أرطوفوني عالمي. المهمة: {query_type}\nتفاصيل الحالة: {context}\nقم بتقديم إجابة علمية، دقيقة، مقسمة لعناوين، وباللغة العربية الفصحى."
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                    st.success("✅ تمت العملية بنجاح!")
                    st.markdown("### 📄 التقرير الذكي:")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"خطأ في الاتصال بالذكاء الاصطناعي: {e}")

# ------------------------------------------
# الصفحة 7: مكتبة العيادة
# ------------------------------------------
elif menu == "📚 مكتبة العيادة والأدوات":
    st.title("📚 مكتبة الموارد والأدوات الرقمية")
    
    t_cards, t_books, t_forms = st.tabs(["🖼️ البطاقات التفاعلية (Flashcards)", "📖 الكتب والمراجع", "📄 النماذج الجاهزة للطباعة"])
    
    with t_cards:
        st.markdown("استخدم هذه الأزرار لعرض المجموعات الضمنية على الطفل عبر الجهاز:")
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("🍎 الفواكه والخضار"): st.success("تم فتح مكتبة الفواكه (يمكنك ربط مسار الصور هنا)")
        if c2.button("🦁 حيوانات الغابة"): st.success("تم فتح مكتبة الحيوانات")
        if c3.button("🚗 وسائل النقل"): st.success("تم فتح مكتبة وسائل النقل")
        if c4.button("👕 الملابس والمهن"): st.success("تم فتح مكتبة الملابس")
        
    with t_books:
        st.markdown("""
        - 📘 **علم أمراض التخاطب** - د. عبد العزيز الشخص
        - 📘 **اضطرابات النطق واللغة** - د. فيصل الزراد
        - 📘 **التدخل المبكر لأطفال التوحد**
        """)
        
    with t_forms:
        st.markdown("""
        - 📥 [تحميل استمارة المقابلة الأولية (PDF)](#)
        - 📥 [تحميل جدول تعزيز السلوك (PDF)](#)
        - 📥 [تحميل خطة علاجية فارغة (Word)](#)
        """)

# ------------------------------------------
# الصفحة 8: الإعدادات والأمان
# ------------------------------------------
elif menu == "⚙️ إعدادات الحساب والأمان":
    st.title("⚙️ إعدادات حسابك والأمان")
    
    st.subheader("🔑 تغيير كلمة المرور")
    with st.form("change_pwd"):
        old_p = st.text_input("كلمة المرور القديمة", type="password")
        new_p = st.text_input("كلمة المرور الجديدة", type="password")
        if st.form_submit_button("تحديث الحماية"):
            if hash_password(old_p) == user_info["password"]:
                st.session_state["users_db"][current_user]["password"] = hash_password(new_p)
                save_data(USERS_FILE, st.session_state["users_db"])
                st.success("✅ تم تغيير كلمة المرور بنجاح!")
            else:
                st.error("❌ الكلمة القديمة غير صحيحة.")
                
    st.subheader("💾 إدارة النسخ الاحتياطي")
    st.info(f"النظام يقوم بحفظ بياناتك تلقائياً كلما قمت بتعديل، وتُحفظ النسخ في مجلد `{BACKUP_DIR}` في مشروعك لضمان عدم ضياع أي حرف.")

# ------------------------------------------
# الصفحة 9: الإدارة العليا (Admin Only)
# ------------------------------------------
elif menu == "👑 إدارة النظام والمستخدمين" and user_role == "admin":
    st.title("👑 مركز التحكم والإدارة العليا (Admin Center)")
    st.info("هنا يمكنك إدارة الطاقم الطبي، إضافة أخصائيين جدد، ومراقبة النظام.")
    
    with st.form("new_user_form"):
        st.subheader("إضافة مختص جديد للنظام")
        c1, c2 = st.columns(2)
        n_user = c1.text_input("اسم المستخدم (للدخول) *")
        n_pass = c2.text_input("كلمة المرور (تُشفر تلقائياً) *", type="password")
        n_name = c1.text_input("الاسم الكامل")
        n_role = c2.selectbox("الصلاحيات", ["therapist", "admin"])
        
        if st.form_submit_button("إنشاء الحساب والتشفير"):
            if n_user and n_pass:
                if n_user not in st.session_state["users_db"]:
                    st.session_state["users_db"][n_user] = {
                        "password": hash_password(n_pass),
                        "role": n_role, "full_name": n_name, "created_at": str(date.today())
                    }
                    save_data(USERS_FILE, st.session_state["users_db"])
                    st.success(f"✅ تم فتح الحساب لـ {n_user} بنجاح!")
                else:
                    st.error("المستخدم موجود مسبقاً.")
            else:
                st.warning("يرجى ملء الحقول الإجبارية.")

    st.subheader("📋 قائمة الطاقم الطبي المسجل")
    users_list = []
    for uname, udata in st.session_state["users_db"].items():
        users_list.append({"اسم المستخدم": uname, "الاسم": udata.get("full_name",""), "الرتبة": udata.get("role",""), "الإنشاء": udata.get("created_at","")})
    st.dataframe(pd.DataFrame(users_list), use_container_width=True)
