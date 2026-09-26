import streamlit as st
import json
import os
import re
import pandas as pd
from datetime import datetime, date, time
from google import genai

# 1. إعدادات الصفحة
st.set_page_config(
    page_title="منصة خطوة | النظام الذكي للتقييم الأرطوفوني للأطفال",
    page_icon="👣",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. تصميم الواجهة بالعربية
st.markdown("""
    <style>
    .stApp {
        direction: rtl;
        text-align: right;
        background-color: #f8f9fa;
    }
    h1, h2, h3, h4, h5, h6, p, label, div, span {
        text-align: right !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .metric-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.04);
        border-right: 5px solid #1a73e8;
        margin-bottom: 15px;
    }
    .metric-title { font-size: 14px; color: #5f6368; margin-bottom: 5px; }
    .metric-value { font-size: 24px; font-weight: bold; color: #202124; }
    .content-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #1a73e8 0%, #1557b0 100%);
        color: white;
        font-size: 16px !important;
        font-weight: 600;
        border-radius: 8px;
        padding: 12px;
        border: none;
    }
    .ai-response-box {
        background-color: #f3f8ff;
        border: 1px solid #c2e7ff;
        border-radius: 10px;
        padding: 20px;
        color: #041e49;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename).strip().replace(' ', '_')

RECORDS_DIR = "records"
if not os.path.exists(RECORDS_DIR):
    os.makedirs(RECORDS_DIR)

all_records = []
for f_name in os.listdir(RECORDS_DIR):
    if f_name.endswith('.json'):
        try:
            with open(os.path.join(RECORDS_DIR, f_name), 'r', encoding='utf-8') as f:
                all_records.append(json.load(f))
        except:
            pass

with st.sidebar:
    st.image("https://img.icons8.com/isometric-folders/100/hospital-folder.png", width=70)
    st.title("منصة خطوة 👣")
    st.caption("نظام التقييم والتأهيل الأرطوفوني للأطفال")
    st.divider()

    menu = st.radio("القائمة الرئيسية", [
        "📊 لوحة التحكم والمواعيد",
        "➕ إضافة تقييم طفل جديد",
        "🔍 الأرشيف وسجلات الأطفال",
        "🧠 المساعد الذكي (Gemini)",
        "⚙️ إعدادات العيادة"
    ])

    st.divider()
    api_key = st.text_input("🔑 مفتاح Gemini API:", type="password")

if menu == "📊 لوحة التحكم والمواعيد":
    st.title("📊 لوحة قيادة العيادة")
    st.caption("نظرة شاملة ومباشرة على أداء وجلسات العيادة اليومية")

    today_str = str(date.today())
    today_sessions = [r for r in all_records if r.get("إدارة_الجلسة", {}).get("تاريخ_الحصة") == today_str]
    unpaid_sessions = [r for r in all_records if r.get("إدارة_الجلسة", {}).get("حالة_الدفع") == "غير مدفوع"]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'''<div class="metric-card"><div class="metric-title">إجمالي الأطفال المسجلين</div><div class="metric-value">{len(all_records)} طفل</div></div>''', unsafe_allow_html=True)
    with col2:
        st.markdown(f'''<div class="metric-card" style="border-right-color: #34a853;"><div class="metric-title">جلسات اليوم</div><div class="metric-value">{len(today_sessions)} جلسة</div></div>''', unsafe_allow_html=True)
    with col3:
        st.markdown(f'''<div class="metric-card" style="border-right-color: #ea4335;"><div class="metric-title">مستحقات غير مدفوعة</div><div class="metric-value">{len(unpaid_sessions)} حالات</div></div>''', unsafe_allow_html=True)
    with col4:
        st.markdown(f'''<div class="metric-card" style="border-right-color: #fbbc04;"><div class="metric-title">تنبيهات النظام</div><div class="metric-value">نشطة 🟢</div></div>''', unsafe_allow_html=True)

    st.subheader("📅 جدول مواعيد الجلسات والتقييمات")
    if all_records:
        table_data = []
        for r in all_records:
            p = r.get("البيانات_الأساسية", {})
            s = r.get("إدارة_الجلسة", {})
            table_data.append({
                "اسم الطفل": p.get("الاسم", "غير محدد"),
                "الهاتف": p.get("الهاتف", "-"),
                "تاريخ الحصة": s.get("تاريخ_الحصة", "-"),
                "وقت الحصة": s.get("الوقت", "-"),
                "المكان": s.get("المكان", "-"),
                "نوع الحصة": s.get("نوع_الحصة", "-"),
                "حالة الدفع": s.get("حالة_الدفع", "-")
            })
        st.dataframe(pd.DataFrame(table_data), use_container_width=True)
    else:
        st.info("لا توجد بيانات أو جلسات مسجلة في النظام حتى الآن.")

elif menu == "➕ إضافة تقييم طفل جديد":
    st.title("➕ إدخال تقييم أرطوفوني جديد")
    
    with st.form("new_patient_form"):
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.subheader("1️⃣ البيانات الأساسية وتوقيت الجلسة")
        c1, c2, c3 = st.columns(3)
        with c1:
            patient_name = st.text_input("اسم الطفل واللقب:*")
            gender = st.selectbox("الجنس:", ["ذكر", "أنثى"])
        with c2:
            birth_date = st.date_input("تاريخ الميلاد:", value=datetime(2019, 1, 1))
            age = st.text_input("العمر الحالي:")
        with c3:
            parent_phone = st.text_input("رقم هاتف الولي:*")
            file_num = st.text_input("رقم الملف:")

        s_col1, s_col2, s_col3 = st.columns(3)
        with s_col1:
            session_date = st.date_input("تاريخ الجلسة:", value=date.today())
            session_time = st.time_input("وقت الجلسة:", value=time(10, 0))
        with s_col2:
            session_location = st.selectbox("مكان الجلسة:", ["القاعة 1", "القاعة 2", "أونلاين", "زيارة منزلي"])
            session_type = st.selectbox("نوع الحصة:", ["تقييم أولي", "علاج أرطوفوني", "تعديل سلوك", "تنمية مهارات"])
        with s_col3:
            payment_status = st.selectbox("حالة الدفع:", ["مدفوع", "غير مدفوع", "اشتراك شهري"])
            reason_from_escort = st.text_area("الشكوى الرئيسية لولي الأمر:*", height=68)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.subheader("2️⃣ الفحص الأرطوفوني واللغوي")
        o_col1, o_col2 = st.columns(2)
        with o_col1:
            eye_contact = st.selectbox("التواصل البصري:", ["ممتاز وطبيعي", "متوسط", "ضعيف / معدوم"])
            name_response = st.selectbox("الاستجابة للاسم:", ["يستجيب دائماً", "يستجيب أحياناً", "لا يستجيب إطلاقاً"])
            comprehension = st.selectbox("فهم الكلام واللغة الاستقبالية:", ["يفهم الأوامر المركبة", "يفهم الأوامر البسيطة بالإشارة", "لا يفهم الأوامر"])
        with o_col2:
            speech_level = st.selectbox("المستوى اللغوي التعبيري:", ["جمل كاملة مع أخطاء", "جمل قصيرة من كلمتين", "كلمات منفردة فقط", "أصوات ومقاطع فقط", "صمات تام"])
            tongue_issue = st.checkbox("وجود رباط اللسان (Frein de langue)")
            palate_issue = st.checkbox("وجود شق الحلق أو الشفة")
            b_hyper = st.checkbox("فرط حركة وعدم استقرار")
            b_attention = st.checkbox("ضعف تركيز وتشتت انتباه")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.subheader("3️⃣ التشخيص المبدئي والتوصيات")
        case_summary = st.text_area("التقرير والتشخيص الأرطوفوني للأخصائي(ة):", height=100)
        recommendations = st.text_area("التوصيات والتمارين المنزلية للوالدين:", height=100)
        specialist_name = st.text_input("اسم الأخصائي(ة) المعالج(ة):")
        st.markdown("</div>", unsafe_allow_html=True)

        submitted = st.form_submit_button("💾 حفظ ملف الطفل وجدولة الجلسة")
        if submitted:
            clean_name = sanitize_filename(patient_name)
            if not clean_name or not parent_phone:
                st.error("⚠️ يرجى التأكد من إدخال اسم الطفل ورقم الهاتف!")
            else:
                record = {
                    "البيانات_الأساسية": {"الاسم": patient_name, "الجنس": gender, "تاريخ_الميلاد": str(birth_date), "العمر": age, "الهاتف": parent_phone, "الملف": file_num},
                    "إدارة_الجلسة": {"تاريخ_الحصة": str(session_date), "الوقت": str(session_time), "المكان": session_location, "نوع_الحصة": session_type, "حالة_الدفع": payment_status},
                    "الفحص_الأرطوفوني": {"التواصل_البصري": eye_contact, "الاستجابة_للاسم": name_response, "فهم_الكلام": comprehension, "المستوى_اللغوي": speech_level, "رباط_اللسان": tongue_issue, "شق_الحلق": palate_issue, "فرط_حركة": b_hyper, "تشتت_انتباه": b_attention},
                    "التشخيص_والتوصيات": {"الشكوى": reason_from_escort, "التقرير": case_summary, "التوصيات": recommendations, "الأخصائي": specialist_name}
                }
                file_path = os.path.join(RECORDS_DIR, f"{clean_name}_تقييم.json")
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(record, f, ensure_ascii=False, indent=4)
                st.success(f"✅ تم حفظ الملف بنجاح! ({clean_name})")

elif menu == "🔍 الأرشيف وسجلات الأطفال":
    st.title("🔍 أرشيف العيادة واستعراض التقرير")
    saved_files = [f for f in os.listdir(RECORDS_DIR) if f.endswith('.json')]
    if saved_files:
        selected_file = st.selectbox("اختر ملف طفل للاستعراض:", ["-- اختر ملف --"] + saved_files)
        if selected_file != "-- اختر ملف --":
            with open(os.path.join(RECORDS_DIR, selected_file), "r", encoding="utf-8") as f:
                data = json.load(f)
            p = data.get("البيانات_الأساسية", {})
            s = data.get("إدارة_الجلسة", {})
            o = data.get("الفحص_الأرطوفوني", {})
            d = data.get("التشخيص_والتوصيات", {})
            st.markdown(f"""
            <div style="background-color: white; padding: 30px; border-radius: 12px; border: 1px solid #e0e0e0;">
                <h2>👣 بطاقة تقييم وتأهيل أرطوفوني</h2>
                <p><b>اسم الطفل:</b> {p.get('الاسم')} | <b>العمر:</b> {p.get('العمر')} | <b>الهاتف:</b> {p.get('الهاتف')}</p>
                <hr/>
                <h4>🗣️ نتائج الفحص:</h4>
                <p><b>المستوى اللغوي:</b> {o.get('المستوى_اللغوي')}</p>
                <h4>📝 التقرير والتوصيات:</h4>
                <p><b>التقرير:</b> {d.get('التقرير')}</p>
                <p><b>التوصيات:</b> {d.get('التوصيات')}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("لا يوجد ملفات في الأرشيف حالياً.")

elif menu == "🧠 المساعد الذكي (Gemini)":
    st.title("🧠 المستشار الأرطوفوني الذكي")
    if not api_key:
        st.warning("⚠️ يرجى إدخال مفتاح API في القائمة الجانبية.")
    else:
        saved_files = [f for f in os.listdir(RECORDS_DIR) if f.endswith('.json')]
        if saved_files:
            selected_child = st.selectbox("اختر ملف الطفل:", saved_files)
            if selected_child and st.button("✨ طلب الاستشارة"):
                try:
                    with open(os.path.join(RECORDS_DIR, selected_child), "r", encoding="utf-8") as f:
                        child_data = json.load(f)
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=f"قدم استشارة بناءً على هذه البيانات: {json.dumps(child_data, ensure_ascii=False)}"
                    )
                    st.markdown(f"<div class='ai-response-box'>{response.text}</div>", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"حدث خطأ أثناء الاتصال بالخدمة: {e}")

elif menu == "⚙️ إعدادات العيادة":
    st.title("⚙️ إعدادات العيادة")
    st.text_input("اسم العيادة:", value="مركز خطوة للتأهيل")
    if st.button("حفظ"):
        st.success("تم الحفظ!")
