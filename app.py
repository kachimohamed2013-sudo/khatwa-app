import streamlit as st
import json
import os
import hashlib
import secrets
import shutil
import csv
import io
import re
from pathlib import Path
from datetime import datetime, date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

try:
    from google import genai
except Exception:
    genai = None


# =========================================================
# 1) إعدادات عامة
# =========================================================
APP_NAME = "منصة خطوة"
APP_SUBTITLE = "النظام الذكي الشامل للعيادات الأرطوفونية"
APP_VERSION = "3.1"
DATA_DIR = Path("clinic_storage")
BACKUP_DIR = DATA_DIR / "backups"
MEDIA_DIR = DATA_DIR / "media"
EXPORT_DIR = DATA_DIR / "exports"
AUDIT_DIR = DATA_DIR / "audit"
USERS_FILE = DATA_DIR / "users_db.json"
DATA_FILE = DATA_DIR / "clinic_data.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

for folder in (DATA_DIR, BACKUP_DIR, MEDIA_DIR, EXPORT_DIR, AUDIT_DIR):
    folder.mkdir(parents=True, exist_ok=True)

st.set_page_config(
    page_title=f"{APP_NAME} | {APP_SUBTITLE}",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Tajawal', sans-serif !important;
        direction: rtl;
    }

    .stApp { background: #f0f4f8; }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a2942 0%, #0f1e35 100%);
    }
    section[data-testid="stSidebar"] * { color: #e8edf5 !important; }
    section[data-testid="stSidebar"] .stRadio label { color: #cbd5e1 !important; }

    .hero {
        background: linear-gradient(135deg, #1d4ed8 0%, #0f766e 60%, #065f46 100%);
        color: white;
        padding: 28px 32px;
        border-radius: 20px;
        margin-bottom: 24px;
        box-shadow: 0 16px 32px rgba(15, 23, 42, .15);
    }

    .metric-card {
        background: #fff;
        border-radius: 16px;
        padding: 20px;
        min-height: 120px;
        box-shadow: 0 4px 16px rgba(15, 23, 42, .07);
        border-right: 5px solid #2563eb;
        margin-bottom: 16px;
        transition: transform .15s ease;
    }
    .metric-card:hover { transform: translateY(-2px); }
    .metric-title { color: #64748b; font-size: .95rem; font-weight: 700; margin-bottom: 8px; }
    .metric-value { color: #0f172a; font-size: 1.85rem; font-weight: 900; }

    .info-box {
        padding: 14px 18px;
        border-radius: 12px;
        background: #f0f9ff;
        border-right: 5px solid #0ea5e9;
        margin: 10px 0;
    }
    .danger-box {
        padding: 14px 18px;
        border-radius: 12px;
        background: #fff1f2;
        border-right: 5px solid #e11d48;
        margin: 10px 0;
    }
    .success-box {
        padding: 14px 18px;
        border-radius: 12px;
        background: #ecfdf5;
        border-right: 5px solid #059669;
        margin: 10px 0;
    }
    .warning-box {
        padding: 14px 18px;
        border-radius: 12px;
        background: #fffbeb;
        border-right: 5px solid #f59e0b;
        margin: 10px 0;
    }

    .patient-card {
        background: #fff;
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 2px 10px rgba(15,23,42,.06);
        border-right: 4px solid #6366f1;
    }

    .session-card {
        background: linear-gradient(135deg, #fafafa, #f8fafc);
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,.04);
        border-top: 3px solid #0ea5e9;
    }

    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: .78rem;
        font-weight: 700;
    }
    .badge-active { background: #dcfce7; color: #166534; }
    .badge-follow { background: #fef9c3; color: #854d0e; }
    .badge-closed { background: #f1f5f9; color: #475569; }

    .stButton > button,
    .stDownloadButton > button,
    .stFormSubmitButton > button {
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-family: 'Tajawal', sans-serif !important;
    }

    h1, h2, h3 { color: #0f172a; font-weight: 900; }
    hr { border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0; }

    div[data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 900 !important; }

    .progress-bar-bg {
        background: #e2e8f0;
        border-radius: 8px;
        height: 10px;
        width: 100%;
    }
    .progress-bar-fill {
        height: 10px;
        border-radius: 8px;
        background: linear-gradient(90deg, #2563eb, #0ea5e9);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 2) أدوات الأمان والتخزين
# =========================================================
def hash_password(password: str, salt: str | None = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 210_000
    ).hex()
    return f"pbkdf2_sha256$210000${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        if stored.startswith("pbkdf2_sha256$"):
            _, iterations, salt, digest = stored.split("$", 3)
            candidate = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
            ).hex()
            return secrets.compare_digest(candidate, digest)
        legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return secrets.compare_digest(legacy, stored)
    except Exception:
        return False


def safe_load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def atomic_write_json(path: Path, data) -> bool:
    temp = path.with_suffix(path.suffix + ".tmp")
    try:
        with temp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp.replace(path)
        return True
    except Exception:
        temp.unlink(missing_ok=True)
        return False


def create_backup() -> Path | None:
    if not DATA_FILE.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / f"clinic_data_backup_{stamp}.json"
    try:
        shutil.copy2(DATA_FILE, backup)
        # keep only last 30 backups
        backups = sorted(BACKUP_DIR.glob("*.json"), reverse=True)
        for old in backups[30:]:
            old.unlink(missing_ok=True)
        return backup
    except Exception:
        return None


def save_all_data():
    if DATA_FILE.exists():
        create_backup()
    ok = atomic_write_json(DATA_FILE, st.session_state["all_data"])
    if not ok:
        st.error("تعذر حفظ بيانات العيادة على القرص.")


def save_users():
    if not atomic_write_json(USERS_FILE, st.session_state["users_db"]):
        st.error("تعذر حفظ حسابات المستخدمين.")


def uid(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%y%m%d%H%M%S')}-{secrets.token_hex(2).upper()}"


def normalize_username(value: str) -> str:
    return value.strip().lower()


def write_audit(action: str, details: str = ""):
    """سجل أحداث المدقق الأمني."""
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "user": st.session_state.get("authenticated_user", "?"),
        "action": action,
        "details": details,
    }
    log_file = AUDIT_DIR / f"audit_{date.today().isoformat()}.json"
    entries = safe_load_json(log_file, [])
    entries.append(entry)
    atomic_write_json(log_file, entries)


def validate_phone(phone: str) -> bool:
    return bool(re.match(r"^[0-9\+\-\s]{7,15}$", phone.strip()))


def calculate_age(dob_str) -> int | None:
    try:
        dob = datetime.strptime(str(dob_str), "%Y-%m-%d").date()
        today = date.today()
        years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return max(0, years)
    except Exception:
        return None


def age_label(dob_str) -> str:
    a = calculate_age(dob_str)
    if a is None:
        return "—"
    if a < 1:
        return "أقل من سنة"
    return f"{a} سنة"


# =========================================================
# 3) الهياكل الافتراضية
# =========================================================
DEFAULT_SETTINGS = {
    "clinic_name": APP_NAME,
    "clinic_phone": "",
    "clinic_address": "",
    "currency": "د.ج",
    "gemini_model": "gemini-2.5-flash",
    "session_price": 2000,
    "working_hours": "8:00 - 17:00",
    "max_daily_appointments": 8,
    "reminder_days": 1,
}

DEFAULT_USERS = {
    "malia benflis": {
        "password": hashlib.sha256("0660451073".encode("utf-8")).hexdigest(),
        "role": "admin",
        "full_name": "الأخصائية مالية بن فليس",
        "phone": "0660451073",
        "created_at": str(date.today()),
        "active": True,
    }
}

DIAGNOSES = [
    "تأخر نمو لغوي",
    "اضطراب اللغة",
    "اضطرابات النطق",
    "التلعثم/التأتأة",
    "اضطراب التواصل الاجتماعي",
    "طيف التوحد (TSA)",
    "إعاقة سمعية",
    "صعوبات تعلم",
    "متلازمة داون",
    "اضطراب الرنة الصوتية",
    "شق حنكي بعد جراحة",
    "تأخر لغوي ثانوي لإهمال",
    "أخرى",
]

SESSION_TYPES = ["تقييمية", "علاجية", "إرشاد أسري", "متابعة", "إعادة تقييم", "ختامية"]
APPOINTMENT_TYPES = ["جلسة علاجية", "تقييم أولي", "مقابلة أهل", "إرشاد أسري", "متابعة", "استشارة"]

THERAPY_GOALS_BANK = {
    "تأخر نمو لغوي": [
        "زيادة الحصيلة المفردية إلى 50+ كلمة",
        "تكوين جمل من كلمتين",
        "الاستجابة للأوامر البسيطة",
        "المشاركة في اللعب التخيلي",
    ],
    "اضطرابات النطق": [
        "إتقان صوت (ر) في موضع البداية",
        "إتقان صوت (س/ش) في جميع المواضع",
        "خفض نسبة الأخطاء الصوتية إلى أقل من 20%",
        "التمييز السمعي بين الأصوات المتشابهة",
    ],
    "التلعثم/التأتأة": [
        "تطبيق تقنية التحدث البطيء",
        "تخفيف التوتر العضلي في الكلام",
        "تحسين الطلاقة في المحادثة التلقائية",
        "تعزيز الثقة بالتواصل اللفظي",
    ],
    "طيف التوحد (TSA)": [
        "التواصل البصري لمدة 3-5 ثوان",
        "تبادل الأدوار في نشاط هادف",
        "استخدام لوحة التواصل بالصور (PECS)",
        "تطوير مهارة طلب الاحتياجات",
    ],
}


def default_user_data():
    return {
        "patients": [],
        "sessions": [],
        "evaluations": [],
        "finances": [],
        "appointments": [],
        "notes": [],
        "therapy_plans": [],
        "waitlist": [],
        "messages": [],
        "supplies": [],
        "supply_movements": [],
        "reminders": [],
    }


# =========================================================
# 4) تهيئة الحالة
# =========================================================
if "users_db" not in st.session_state:
    st.session_state["users_db"] = safe_load_json(USERS_FILE, DEFAULT_USERS)

if "all_data" not in st.session_state:
    st.session_state["all_data"] = safe_load_json(DATA_FILE, {})

if "settings" not in st.session_state:
    st.session_state["settings"] = safe_load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    for k, v in DEFAULT_SETTINGS.items():
        st.session_state["settings"].setdefault(k, v)

if "authenticated_user" not in st.session_state:
    st.session_state["authenticated_user"] = None

if "active_patient_id" not in st.session_state:
    st.session_state["active_patient_id"] = None

if "login_attempts" not in st.session_state:
    st.session_state["login_attempts"] = 0

if "lockout_until" not in st.session_state:
    st.session_state["lockout_until"] = None


# =========================================================
# 5) تسجيل الدخول
# =========================================================
if st.session_state["authenticated_user"] is None:
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        s = st.session_state["settings"]
        st.markdown(
            f"""
            <div class="hero" style="text-align:center;">
                <div style="font-size:3.5rem;">🏥</div>
                <h1 style="color:white;margin-bottom:6px;font-size:2rem;">{s.get("clinic_name", APP_NAME)}</h1>
                <div style="font-size:1rem;opacity:.9;">{APP_SUBTITLE}</div>
                <div style="font-size:.85rem;opacity:.7;margin-top:8px;">النسخة {APP_VERSION}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # فحص الإغلاق المؤقت
        locked = False
        if st.session_state["lockout_until"]:
            if datetime.now() < st.session_state["lockout_until"]:
                remaining = (st.session_state["lockout_until"] - datetime.now()).seconds
                st.error(f"🔒 تم تعليق تسجيل الدخول لمدة {remaining} ثانية بسبب محاولات فاشلة متكررة.")
                locked = True
            else:
                st.session_state["login_attempts"] = 0
                st.session_state["lockout_until"] = None

        if not locked:
            with st.form("login_form"):
                username = st.text_input("👤 اسم المستخدم").strip()
                password = st.text_input("🔑 كلمة المرور", type="password")
                submit = st.form_submit_button("تسجيل الدخول 🔒", use_container_width=True)

            if submit:
                key = normalize_username(username)
                user = st.session_state["users_db"].get(key)
                if user and user.get("active", True) and verify_password(password, user.get("password", "")):
                    if not user["password"].startswith("pbkdf2_sha256$"):
                        user["password"] = hash_password(password)
                        save_users()
                    st.session_state["authenticated_user"] = key
                    st.session_state["login_attempts"] = 0
                    write_audit("LOGIN_SUCCESS")
                    st.rerun()
                else:
                    st.session_state["login_attempts"] += 1
                    attempts = st.session_state["login_attempts"]
                    write_audit("LOGIN_FAIL", f"username={username} attempt={attempts}")
                    if attempts >= 5:
                        st.session_state["lockout_until"] = datetime.now() + timedelta(minutes=5)
                        st.error("تم تعليق حسابك 5 دقائق بسبب كثرة المحاولات الفاشلة.")
                    else:
                        st.error(f"❌ بيانات الدخول غير صحيحة. ({attempts}/5)")

    st.stop()


# =========================================================
# 6) تجهيز مساحة المستخدم
# =========================================================
current_user = st.session_state["authenticated_user"]
user_info = st.session_state["users_db"][current_user]
user_role = user_info.get("role", "therapist")

if current_user not in st.session_state["all_data"]:
    st.session_state["all_data"][current_user] = default_user_data()

db = st.session_state["all_data"][current_user]

for key, value in default_user_data().items():
    db.setdefault(key, value)


# =========================================================
# 7) دوال المساعدة للبيانات
# =========================================================
def patient_by_id(patient_id):
    return next((p for p in db["patients"] if p["id"] == patient_id), None)


def patient_name(patient_id):
    p = patient_by_id(patient_id)
    return p["name"] if p else "غير معروف"


def patient_sessions(patient_id):
    return [s for s in db["sessions"] if s.get("patient_id") == patient_id]


def patient_evaluations(patient_id):
    return [e for e in db["evaluations"] if e.get("patient_id") == patient_id]


def patient_appointments(patient_id):
    return [a for a in db["appointments"] if a.get("patient_id") == patient_id]


def patient_finances(patient_id):
    return [f for f in db["finances"] if f.get("patient_id") == patient_id]


def patient_plan(patient_id):
    plans = [p for p in db["therapy_plans"] if p.get("patient_id") == patient_id]
    return plans[-1] if plans else None


def supply_by_id(supply_id):
    return next((item for item in db["supplies"] if item.get("id") == supply_id), None)


def reminder_by_id(reminder_id):
    return next((item for item in db["reminders"] if item.get("id") == reminder_id), None)


def reminder_patient_label(reminder):
    patient_id = reminder.get("patient_id")
    return patient_name(patient_id) if patient_id else "عام"


def reminder_is_overdue(reminder):
    if reminder.get("status") in ["منجز", "ملغى"]:
        return False
    try:
        return datetime.strptime(reminder.get("due_date", ""), "%Y-%m-%d").date() < date.today()
    except Exception:
        return False


def add_supply_movement(supply_id, movement_type, quantity, note=""):
    db.setdefault("supply_movements", []).append({
        "id": uid("MOV"),
        "supply_id": supply_id,
        "supply_name": supply_by_id(supply_id).get("name", "") if supply_by_id(supply_id) else "",
        "type": movement_type,
        "quantity": float(quantity),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "note": note,
        "created_by": current_user,
    })


def create_next_recurring_reminder(reminder):
    repeat = reminder.get("repeat", "لا يتكرر")
    increments = {
        "يومياً": timedelta(days=1),
        "أسبوعياً": timedelta(days=7),
    }
    if repeat in increments:
        next_date = datetime.strptime(reminder.get("due_date", ""), "%Y-%m-%d").date() + increments[repeat]
    elif repeat == "شهرياً":
        current_date = datetime.strptime(reminder.get("due_date", ""), "%Y-%m-%d").date()
        if current_date.month == 12:
            next_year, next_month = current_date.year + 1, 1
        else:
            next_year, next_month = current_date.year, current_date.month + 1
        if next_month == 12:
            following = date(next_year + 1, 1, 1)
        else:
            following = date(next_year, next_month + 1, 1)
        last_day = (following - timedelta(days=1)).day
        next_date = date(next_year, next_month, min(current_date.day, last_day))
    else:
        return False

    series_id = reminder.get("series_id", reminder.get("id"))
    already_exists = any(
        item.get("series_id") == series_id and item.get("due_date") == str(next_date)
        for item in db["reminders"]
    )
    if already_exists:
        return False

    next_reminder = dict(reminder)
    next_reminder.update({
        "id": uid("REM"),
        "series_id": series_id,
        "previous_id": reminder.get("id"),
        "due_date": str(next_date),
        "status": "مفتوح",
        "completed_at": "",
        "created_at": datetime.now().isoformat(timespec="minutes"),
    })
    db["reminders"].append(next_reminder)
    return True


def export_current_user_data():
    return json.dumps(db, ensure_ascii=False, indent=2).encode("utf-8")


def delete_patient(patient_id):
    db["patients"] = [p for p in db["patients"] if p["id"] != patient_id]
    db["sessions"] = [s for s in db["sessions"] if s.get("patient_id") != patient_id]
    db["evaluations"] = [e for e in db["evaluations"] if e.get("patient_id") != patient_id]
    db["appointments"] = [a for a in db["appointments"] if a.get("patient_id") != patient_id]
    db["finances"] = [f for f in db["finances"] if f.get("patient_id") != patient_id]
    db["therapy_plans"] = [p for p in db["therapy_plans"] if p.get("patient_id") != patient_id]
    save_all_data()
    write_audit("DELETE_PATIENT", f"id={patient_id}")


def patients_dict():
    return {p["id"]: p["name"] for p in db["patients"]}


def today_appointments():
    today_str = str(date.today())
    return [a for a in db["appointments"] if a.get("date") == today_str and a.get("status") not in ["ملغى", "لم يحضر"]]


def pending_finances(patient_id):
    paid = sum(float(f.get("amount", 0)) for f in patient_finances(patient_id) if f.get("type") == "مداخيل")
    sessions_n = len(patient_sessions(patient_id))
    price = float(st.session_state["settings"].get("session_price", 2000))
    owed = sessions_n * price - paid
    return max(0.0, owed)


# =========================================================
# 8) القائمة الجانبية
# =========================================================
s_settings = st.session_state["settings"]
st.sidebar.markdown(
    f"""
    <div style="text-align:center;padding:12px 0 8px;">
        <div style="font-size:2.4rem;">🏥</div>
        <h2 style="color:white!important;margin:4px 0;font-size:1.2rem;">{s_settings.get("clinic_name", APP_NAME)}</h2>
        <small style="color:#94a3b8!important;">{user_info.get("full_name", current_user)}</small>
        <br><span style="background:#1e3a5f;color:#7dd3fc!important;font-size:.75rem;padding:2px 8px;border-radius:12px;">{user_role}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# إشعار مواعيد اليوم
today_apts = today_appointments()
if today_apts:
    st.sidebar.markdown(
        f'<div style="background:#0c4a6e;border-radius:10px;padding:8px 12px;margin:8px 6px;">'
        f'<span style="color:#7dd3fc!important;font-size:.85rem;">📅 {len(today_apts)} موعد اليوم</span></div>',
        unsafe_allow_html=True,
    )

open_reminders_count = sum(
    1 for item in db["reminders"]
    if item.get("status", "مفتوح") not in ["منجز", "ملغى"]
)
if open_reminders_count:
    st.sidebar.markdown(
        f'<div style="background:#713f12;border-radius:10px;padding:8px 12px;margin:8px 6px;">'
        f'<span style="color:#fde68a!important;font-size:.85rem;">🔔 {open_reminders_count} تذكير مفتوح</span></div>',
        unsafe_allow_html=True,
    )

st.sidebar.write("---")

menu_items = [
    "📊 لوحة القيادة",
    "👥 إدارة الأطفال",
    "📁 ملف الطفل الموحد",
    "📋 التقييمات والمقاييس",
    "🎯 خطط العلاج",
    "📝 الجلسات والمتابعة",
    "📅 المواعيد",
    "🧰 لوازم الحصص والتذكيرات",
    "💰 الإدارة المالية",
    "🤖 المساعد الذكي",
    "📚 مكتبة العيادة",
    "📄 التقارير والتصدير",
    "⚙️ الإعدادات والأمان",
]
if user_role == "admin":
    menu_items.append("👑 إدارة المستخدمين")

menu = st.sidebar.radio("📌 القائمة الرئيسية", menu_items, label_visibility="collapsed")

if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
    write_audit("LOGOUT")
    st.session_state["authenticated_user"] = None
    st.rerun()

st.sidebar.write("---")
st.sidebar.caption(f"النسخة {APP_VERSION} • {date.today().isoformat()}")
st.sidebar.caption("🔐 البيانات محفوظة محلياً في clinic_storage")


# =========================================================
# 9) لوحة القيادة
# =========================================================
if menu == "📊 لوحة القيادة":
    st.markdown(
        f"""
        <div class="hero">
            <h1 style="color:white;margin-bottom:4px;">📊 لوحة القيادة</h1>
            <div style="opacity:.9;">مرحباً {user_info.get("full_name", current_user)} —
            {date.today().strftime("%A، %d/%m/%Y")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # إحصائيات سريعة
    patients_count = len(db["patients"])
    sessions_count = len(db["sessions"])
    eval_count = len(db["evaluations"])
    active_patients = sum(1 for p in db["patients"] if p.get("status", "نشط") == "نشط")
    total_in = sum(float(f.get("amount", 0)) for f in db["finances"] if f.get("type") == "مداخيل")
    total_out = sum(float(f.get("amount", 0)) for f in db["finances"] if f.get("type") == "مصاريف")
    currency = s_settings.get("currency", "د.ج")

    # مواعيد اليوم
    today_apts_detail = today_appointments()
    plans_count = len(db["therapy_plans"])

    cols = st.columns(6)
    metrics = [
        ("👥 الأطفال", patients_count, "#2563eb"),
        ("✅ نشطون", active_patients, "#059669"),
        ("📝 الجلسات", sessions_count, "#f59e0b"),
        ("📋 التقييمات", eval_count, "#7c3aed"),
        ("🎯 الخطط", plans_count, "#0891b2"),
        ("💰 الصافي", f"{total_in-total_out:,.0f}\n{currency}", "#0f766e"),
    ]
    for col, (title, value, accent) in zip(cols, metrics):
        col.markdown(
            f'<div class="metric-card" style="border-right-color:{accent};">'
            f'<div class="metric-title">{title}</div>'
            f'<div class="metric-value" style="font-size:1.5rem;">{value}</div></div>',
            unsafe_allow_html=True,
        )

    # --- مواعيد اليوم ---
    if today_apts_detail:
        st.subheader("⏰ مواعيد اليوم")
        apt_cols = st.columns(min(len(today_apts_detail), 4))
        for i, apt in enumerate(sorted(today_apts_detail, key=lambda x: x.get("time", ""))[:4]):
            with apt_cols[i % 4]:
                st.markdown(
                    f'<div class="session-card">'
                    f'<strong>{apt.get("time", "—")}</strong><br>'
                    f'{apt.get("patient_name", "—")}<br>'
                    f'<small style="color:#64748b;">{apt.get("type", "")}</small></div>',
                    unsafe_allow_html=True,
                )

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("📈 تطور الجلسات (آخر 60 يوماً)")
        if db["sessions"]:
            df = pd.DataFrame(db["sessions"])
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"])
            cutoff = pd.Timestamp(date.today() - timedelta(days=60))
            df = df[df["date"] >= cutoff]
            if not df.empty:
                daily = df.groupby(df["date"].dt.date).size().reset_index(name="جلسات")
                fig = px.area(daily, x="date", y="جلسات", template="plotly_white")
                fig.update_traces(fill="tozeroy", line_color="#2563eb", fillcolor="rgba(37,99,235,.12)")
                fig.update_layout(xaxis_title="", yaxis_title="عدد الجلسات", margin=dict(t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("لا توجد جلسات في الفترة الأخيرة.")
        else:
            st.info("لا توجد جلسات مسجلة.")

    with col_b:
        st.subheader("💰 المداخيل والمصاريف (هذا الشهر)")
        month_start = date.today().replace(day=1)
        fin_month = [
            f for f in db["finances"]
            if f.get("date", "") >= str(month_start)
        ]
        if fin_month:
            fin_df = pd.DataFrame(fin_month)
            fin_df["amount"] = pd.to_numeric(fin_df["amount"], errors="coerce").fillna(0)
            summary = fin_df.groupby("type", as_index=False)["amount"].sum()
            colors = {"مداخيل": "#059669", "مصاريف": "#e11d48"}
            fig2 = px.bar(
                summary, x="type", y="amount", text_auto=True,
                template="plotly_white",
                color="type",
                color_discrete_map=colors,
            )
            fig2.update_layout(xaxis_title="", yaxis_title=f"المبلغ ({currency})", showlegend=False, margin=dict(t=10))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("لا توجد عمليات مالية هذا الشهر.")

    # --- توزيع التشخيصات ---
    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("🔬 توزيع الحالات")
        if db["patients"]:
            diag_df = pd.DataFrame(db["patients"])
            diag_count = diag_df["diagnosis"].value_counts().reset_index()
            diag_count.columns = ["التشخيص", "العدد"]
            fig3 = px.pie(diag_count, names="التشخيص", values="العدد", template="plotly_white", hole=.35)
            fig3.update_layout(margin=dict(t=10, b=10))
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("لا توجد حالات مسجلة.")

    with col_d:
        st.subheader("📅 أقرب المواعيد")
        future = []
        for item in db["appointments"]:
            try:
                d = datetime.strptime(item["date"], "%Y-%m-%d").date()
                if d >= date.today():
                    future.append(item)
            except Exception:
                continue
        future = sorted(future, key=lambda x: (x.get("date", ""), x.get("time", "")))[:8]
        if future:
            for apt in future:
                status_color = {"مؤكد": "#059669", "معلق": "#f59e0b"}.get(apt.get("status"), "#64748b")
                st.markdown(
                    f'<div class="session-card">'
                    f'<span style="color:{status_color};font-weight:700;">●</span> '
                    f'<strong>{apt.get("date")} {apt.get("time","")}</strong> — '
                    f'{apt.get("patient_name", "—")} '
                    f'<small style="color:#64748b;">({apt.get("type","")})</small></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("لا توجد مواعيد قادمة.")

    # --- أطفال بمبالغ معلقة ---
    st.subheader("⚠️ أطفال بمبالغ غير مسددة")
    pending = []
    for p in db["patients"]:
        owed = pending_finances(p["id"])
        if owed > 0:
            pending.append({"الاسم": p["name"], "المعلق": f"{owed:,.0f} {currency}", "id": p["id"]})
    if pending:
        st.dataframe(pd.DataFrame(pending).drop(columns=["id"]), use_container_width=True, hide_index=True)
    else:
        st.success("✅ لا توجد مبالغ معلقة.")


# =========================================================
# 10) إدارة الأطفال
# =========================================================
elif menu == "👥 إدارة الأطفال":
    st.title("👥 إدارة الأطفال والسجل الطبي")

    t_add, t_manage, t_waitlist = st.tabs(["➕ إضافة طفل", "🔍 البحث والتعديل", "⏳ قائمة الانتظار"])

    with t_add:
        with st.form("patient_registration", clear_on_submit=True):
            st.subheader("🆔 البيانات الأساسية")
            c1, c2, c3 = st.columns(3)
            p_name = c1.text_input("الاسم الكامل *")
            p_dob = c2.date_input("تاريخ الميلاد", min_value=date(1950, 1, 1), max_value=date.today(), value=date(2018, 1, 1))
            p_gender = c3.selectbox("الجنس", ["ذكر", "أنثى"])

            c4, c5, c6 = st.columns(3)
            p_parent = c4.text_input("اسم ولي الأمر")
            p_phone = c5.text_input("رقم الهاتف *")
            p_second_phone = c6.text_input("هاتف إضافي")

            c7, c8 = st.columns(2)
            p_city = c7.text_input("المدينة/الولاية")
            p_school = c8.text_input("المدرسة/الروضة (اختياري)")

            st.subheader("🏥 البيانات الطبية")
            p_diagnosis = st.selectbox("التصنيف الأساسي *", DIAGNOSES)
            p_secondary = st.multiselect("تشخيصات مصاحبة", DIAGNOSES)

            c9, c10 = st.columns(2)
            p_referred_by = c9.selectbox("مصدر الإحالة", ["أهل مباشرة", "طبيب", "مدرسة", "أخصائي آخر", "أخرى"])
            p_status = c10.selectbox("حالة الملف", ["نشط", "متابعة", "مغلق"])

            p_history = st.text_area("التاريخ النمائي والطبي", height=100)
            p_previous_therapy = st.text_area("تجارب علاجية سابقة")
            p_notes = st.text_area("ملاحظات أولية")

            if st.form_submit_button("💾 إنشاء ملف الطفل", use_container_width=True):
                errors = []
                if not p_name.strip():
                    errors.append("الاسم الكامل مطلوب.")
                if not p_phone.strip():
                    errors.append("رقم الهاتف مطلوب.")
                elif not validate_phone(p_phone):
                    errors.append("رقم الهاتف غير صحيح.")
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    patient_id = uid("PAT")
                    new_patient = {
                        "id": patient_id,
                        "name": p_name.strip(),
                        "dob": str(p_dob),
                        "gender": p_gender,
                        "parent": p_parent.strip(),
                        "phone": p_phone.strip(),
                        "second_phone": p_second_phone.strip(),
                        "city": p_city.strip(),
                        "school": p_school.strip(),
                        "diagnosis": p_diagnosis,
                        "secondary_diagnoses": p_secondary,
                        "referred_by": p_referred_by,
                        "history": p_history.strip(),
                        "previous_therapy": p_previous_therapy.strip(),
                        "notes": p_notes.strip(),
                        "status": p_status,
                        "created_at": str(date.today()),
                        "created_by": current_user,
                        "last_updated": str(date.today()),
                    }
                    db["patients"].append(new_patient)
                    save_all_data()
                    write_audit("ADD_PATIENT", f"id={patient_id} name={p_name}")
                    st.success(f"✅ تم إنشاء ملف {p_name.strip()} برقم {patient_id}")

    with t_manage:
        if not db["patients"]:
            st.info("لم يتم تسجيل أي طفل بعد.")
        else:
            col_search, col_filter, col_sort = st.columns(3)
            search = col_search.text_input("🔎 ابحث بالاسم أو الهاتف أو الملف")
            filter_status = col_filter.selectbox("تصفية بالحالة", ["الكل", "نشط", "متابعة", "مغلق"])
            filter_diag = col_sort.selectbox("تصفية بالتشخيص", ["الكل"] + DIAGNOSES)

            patients_df = pd.DataFrame(db["patients"])

            if search:
                mask = (
                    patients_df["name"].astype(str).str.contains(search, case=False, na=False)
                    | patients_df["phone"].astype(str).str.contains(search, case=False, na=False)
                    | patients_df["id"].astype(str).str.contains(search, case=False, na=False)
                )
                patients_df = patients_df[mask]

            if filter_status != "الكل":
                patients_df = patients_df[patients_df["status"] == filter_status]

            if filter_diag != "الكل":
                patients_df = patients_df[patients_df["diagnosis"] == filter_diag]

            # إضافة عمر محسوب
            patients_df["العمر"] = patients_df["dob"].apply(age_label)

            visible = ["id", "name", "العمر", "gender", "diagnosis", "phone", "status", "created_at"]
            available = [c for c in visible if c in patients_df.columns]
            st.dataframe(
                patients_df[available].rename(columns={
                    "id": "رقم الملف", "name": "الاسم", "gender": "الجنس",
                    "diagnosis": "التشخيص", "phone": "الهاتف",
                    "status": "الحالة", "created_at": "تاريخ التسجيل",
                }),
                use_container_width=True, hide_index=True,
            )
            st.caption(f"إجمالي: {len(patients_df)} طفل")

            if len(patients_df) > 0:
                selected = st.selectbox(
                    "اختر ملفاً لإدارته",
                    patients_df["id"].tolist(),
                    format_func=lambda x: f"{x} — {patient_name(x)}",
                )
                p = patient_by_id(selected)
                if p:
                    col_e, col_d = st.columns(2)
                    with col_e:
                        st.markdown("### ✏️ تعديل بيانات الطفل")
                        with st.form("edit_patient"):
                            new_name = st.text_input("الاسم", value=p.get("name", ""))
                            try:
                                cur_dob = datetime.strptime(p.get("dob", "2018-01-01"), "%Y-%m-%d").date()
                            except Exception:
                                cur_dob = date(2018, 1, 1)
                            new_dob = st.date_input("تاريخ الميلاد", value=cur_dob)
                            new_gender = st.selectbox("الجنس", ["ذكر", "أنثى"], index=0 if p.get("gender") == "ذكر" else 1)
                            new_parent = st.text_input("ولي الأمر", value=p.get("parent", ""))
                            new_phone = st.text_input("الهاتف", value=p.get("phone", ""))
                            new_city = st.text_input("المدينة", value=p.get("city", ""))
                            new_diagnosis = st.selectbox("التصنيص", DIAGNOSES, index=DIAGNOSES.index(p.get("diagnosis", DIAGNOSES[0])) if p.get("diagnosis") in DIAGNOSES else 0)
                            new_history = st.text_area("التاريخ", value=p.get("history", ""))
                            new_notes = st.text_area("الملاحظات", value=p.get("notes", ""))
                            statuses = ["نشط", "متابعة", "مغلق"]
                            new_status = st.selectbox("الحالة", statuses, index=statuses.index(p.get("status", "نشط")) if p.get("status") in statuses else 0)

                            if st.form_submit_button("💾 حفظ التعديلات"):
                                p.update({
                                    "name": new_name.strip(),
                                    "dob": str(new_dob),
                                    "gender": new_gender,
                                    "parent": new_parent.strip(),
                                    "phone": new_phone.strip(),
                                    "city": new_city.strip(),
                                    "diagnosis": new_diagnosis,
                                    "history": new_history.strip(),
                                    "notes": new_notes.strip(),
                                    "status": new_status,
                                    "last_updated": str(date.today()),
                                })
                                for record in db["sessions"] + db["evaluations"] + db["appointments"]:
                                    if record.get("patient_id") == selected:
                                        record["patient_name"] = p["name"]
                                save_all_data()
                                write_audit("EDIT_PATIENT", f"id={selected}")
                                st.success("تم تحديث الملف بنجاح.")
                                st.rerun()

                    with col_d:
                        st.markdown("### 🗑️ حذف الملف")
                        st.markdown(
                            '<div class="warning-box">الحذف نهائي ويزيل جميع السجلات المرتبطة بهذا الطفل.</div>',
                            unsafe_allow_html=True,
                        )
                        if st.checkbox("أفهم أن الحذف نهائي لا رجعة فيه"):
                            if st.button("🗑️ حذف ملف الطفل", type="secondary"):
                                delete_patient(selected)
                                st.success("تم حذف الملف.")
                                st.rerun()

    with t_waitlist:
        st.subheader("⏳ قائمة الانتظار")
        with st.form("waitlist_form", clear_on_submit=True):
            wc1, wc2, wc3 = st.columns(3)
            w_name = wc1.text_input("اسم الطفل *")
            w_age = wc2.text_input("العمر التقريبي")
            w_phone = wc3.text_input("هاتف الأهل *")
            w_concern = st.text_area("الشكوى الرئيسية")
            w_date = st.date_input("تاريخ الطلب", value=date.today())
            if st.form_submit_button("➕ إضافة لقائمة الانتظار", use_container_width=True):
                if w_name.strip() and w_phone.strip():
                    db["waitlist"].append({
                        "id": uid("WL"),
                        "name": w_name.strip(),
                        "age": w_age.strip(),
                        "phone": w_phone.strip(),
                        "concern": w_concern.strip(),
                        "request_date": str(w_date),
                        "status": "منتظر",
                    })
                    save_all_data()
                    st.success(f"✅ تمت إضافة {w_name.strip()} لقائمة الانتظار.")
                else:
                    st.error("الاسم والهاتف مطلوبان.")

        if db["waitlist"]:
            wl_df = pd.DataFrame(db["waitlist"])
            st.dataframe(
                wl_df[["name", "age", "phone", "concern", "request_date", "status"]].rename(columns={
                    "name": "الاسم", "age": "العمر", "phone": "الهاتف",
                    "concern": "الشكوى", "request_date": "تاريخ الطلب", "status": "الحالة",
                }),
                use_container_width=True, hide_index=True,
            )
            # تحويل من قائمة الانتظار إلى طفل
            wl_ids = [w["id"] for w in db["waitlist"] if w.get("status") == "منتظر"]
            if wl_ids:
                chosen_wl = st.selectbox("تحويل حالة إلى طفل مسجل:", wl_ids, format_func=lambda x: next((w["name"] for w in db["waitlist"] if w["id"] == x), x))
                if st.button("✅ تحويل وتسجيل كطفل"):
                    wl_item = next((w for w in db["waitlist"] if w["id"] == chosen_wl), None)
                    if wl_item:
                        patient_id = uid("PAT")
                        db["patients"].append({
                            "id": patient_id, "name": wl_item["name"],
                            "dob": str(date.today()), "gender": "غير محدد",
                            "parent": "", "phone": wl_item["phone"],
                            "second_phone": "", "city": "", "school": "",
                            "diagnosis": "أخرى", "secondary_diagnoses": [],
                            "referred_by": "قائمة الانتظار",
                            "history": wl_item.get("concern", ""),
                            "previous_therapy": "", "notes": "",
                            "status": "نشط", "created_at": str(date.today()),
                            "created_by": current_user, "last_updated": str(date.today()),
                        })
                        wl_item["status"] = "تم التحويل"
                        save_all_data()
                        st.success(f"✅ تم تسجيل {wl_item['name']} كطفل برقم {patient_id}")
                        st.rerun()
        else:
            st.info("قائمة الانتظار فارغة.")


# =========================================================
# 11) ملف الطفل الموحد
# =========================================================
elif menu == "📁 ملف الطفل الموحد":
    st.title("📁 ملف الطفل الموحد")

    if not db["patients"]:
        st.warning("أضف طفلاً أولاً من قائمة إدارة الأطفال.")
    else:
        patients = patients_dict()
        pid = st.selectbox(
            "اختر الطفل",
            list(patients),
            format_func=lambda x: f"{patients[x]} — {x}",
            index=list(patients).index(st.session_state["active_patient_id"])
            if st.session_state["active_patient_id"] in patients else 0,
        )
        st.session_state["active_patient_id"] = pid
        p = patient_by_id(pid)
        if not p:
            st.error("لم يُعثر على هذا الملف.")
            st.stop()

        # بطاقة هوية الطفل
        age = age_label(p.get("dob", ""))
        badge_class = {"نشط": "badge-active", "متابعة": "badge-follow", "مغلق": "badge-closed"}.get(p.get("status", "نشط"), "badge-active")
        s_count = len(patient_sessions(pid))
        e_count = len(patient_evaluations(pid))
        owed = pending_finances(pid)
        currency = s_settings.get("currency", "د.ج")

        st.markdown(
            f"""
            <div class="patient-card">
                <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:8px;">
                    <div>
                        <span style="font-size:1.5rem;font-weight:900;">👤 {p.get("name","")}</span>
                        <span class="badge {badge_class}" style="margin-right:10px;">{p.get("status","نشط")}</span>
                    </div>
                    <div style="text-align:left;color:#64748b;font-size:.9rem;">
                        📋 {p.get("id","")}
                    </div>
                </div>
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px;margin-top:12px;color:#374151;">
                    <div>🎂 العمر: <strong>{age}</strong></div>
                    <div>⚧ الجنس: <strong>{p.get("gender","—")}</strong></div>
                    <div>📞 الهاتف: <strong>{p.get("phone","—")}</strong></div>
                    <div>👨‍👩‍👦 ولي الأمر: <strong>{p.get("parent","—") or "—"}</strong></div>
                    <div>🏥 التشخيص: <strong>{p.get("diagnosis","—")}</strong></div>
                    <div>📍 المدينة: <strong>{p.get("city","—") or "—"}</strong></div>
                    <div>📝 جلسات: <strong>{s_count}</strong></div>
                    <div>📋 تقييمات: <strong>{e_count}</strong></div>
                    {f'<div style="color:#dc2626;">💰 معلق: <strong>{owed:,.0f} {currency}</strong></div>' if owed > 0 else '<div style="color:#059669;">💰 مسدد ✅</div>'}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_info, tab_sessions, tab_evals, tab_plan, tab_fin, tab_apts = st.tabs([
            "📄 المعلومات", "📝 الجلسات", "📋 التقييمات", "🎯 خطة العلاج", "💰 المالية", "📅 المواعيد"
        ])

        with tab_info:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**التاريخ النمائي والطبي:**")
                st.write(p.get("history", "—") or "—")
                st.markdown("**تجارب علاجية سابقة:**")
                st.write(p.get("previous_therapy", "—") or "—")
            with col2:
                st.markdown("**ملاحظات:**")
                st.write(p.get("notes", "—") or "—")
                if p.get("secondary_diagnoses"):
                    st.markdown("**تشخيصات مصاحبة:**")
                    for d in p["secondary_diagnoses"]:
                        st.write(f"• {d}")

        with tab_sessions:
            sessions = sorted(patient_sessions(pid), key=lambda x: x.get("date", ""), reverse=True)
            if sessions:
                for s in sessions[:10]:
                    prog = s.get("progress", 0)
                    st.markdown(
                        f'<div class="session-card">'
                        f'<strong>{s.get("date","—")} • {s.get("type","—")} • {s.get("duration",0)} دقيقة</strong><br>'
                        f'<small>الأهداف: {s.get("goals","—")}</small><br>'
                        f'<small>الأنشطة: {s.get("activities","—")}</small><br>'
                        f'<div class="progress-bar-bg" style="margin-top:6px;">'
                        f'<div class="progress-bar-fill" style="width:{prog}%;"></div></div>'
                        f'<small style="color:#64748b;">الإنجاز: {prog}%</small>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                if len(sessions) > 10:
                    st.caption(f"وهناك {len(sessions)-10} جلسة أخرى.")
            else:
                st.info("لا توجد جلسات مسجلة لهذا الطفل.")

        with tab_evals:
            evals = sorted(patient_evaluations(pid), key=lambda x: x.get("date", ""), reverse=True)
            if evals:
                for e in evals:
                    with st.expander(f"{e.get('date','—')} — {e.get('type','—')}"):
                        st.json(e.get("scores", {}))
                        if e.get("notes"):
                            st.write("الملاحظات:", e["notes"])
            else:
                st.info("لا توجد تقييمات لهذا الطفل.")

        with tab_plan:
            plan = patient_plan(pid)
            if plan:
                st.markdown(f"**الخطة الحالية — بدأت:** {plan.get('start_date','—')}")
                st.markdown(f"**الهدف الرئيسي:** {plan.get('main_goal','—')}")
                st.markdown("**الأهداف الفرعية:**")
                for goal in plan.get("sub_goals", []):
                    achieved = goal.get("achieved", False)
                    icon = "✅" if achieved else "⭕"
                    st.write(f"{icon} {goal.get('text','')}")
            else:
                st.info("لا توجد خطة علاجية محددة. أضفها من قسم خطط العلاج.")

        with tab_fin:
            finances = patient_finances(pid)
            if finances:
                fin_df = pd.DataFrame(finances)
                fin_df["amount"] = pd.to_numeric(fin_df.get("amount", [0]), errors="coerce").fillna(0)
                total_paid = fin_df[fin_df["type"] == "مداخيل"]["amount"].sum()
                total_due = len(patient_sessions(pid)) * float(s_settings.get("session_price", 2000))
                c1, c2, c3 = st.columns(3)
                c1.metric("المدفوع", f"{total_paid:,.0f} {currency}")
                c2.metric("المستحق", f"{total_due:,.0f} {currency}")
                c3.metric("المعلق", f"{max(0, total_due - total_paid):,.0f} {currency}")
                st.dataframe(fin_df[["date", "type", "desc", "amount", "method"]].rename(columns={
                    "date": "التاريخ", "type": "النوع", "desc": "البيان", "amount": "المبلغ", "method": "طريقة الدفع"
                }), use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد عمليات مالية لهذا الطفل.")

        with tab_apts:
            apts = sorted(patient_appointments(pid), key=lambda x: (x.get("date", ""), x.get("time", "")), reverse=True)
            if apts:
                apts_df = pd.DataFrame(apts)
                st.dataframe(apts_df[["date", "time", "type", "duration", "status"]].rename(columns={
                    "date": "التاريخ", "time": "الوقت", "type": "النوع",
                    "duration": "المدة (د)", "status": "الحالة",
                }), use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد مواعيد لهذا الطفل.")


# =========================================================
# 12) التقييمات والمقاييس
# =========================================================
elif menu == "📋 التقييمات والمقاييس":
    st.title("📋 التقييمات والمقاييس")

    if not db["patients"]:
        st.warning("أضف طفلاً أولاً.")
    else:
        patients = patients_dict()
        selected_id = st.selectbox("👤 الطفل", list(patients), format_func=lambda x: f"{patients[x]} — {x}")

        t_new, t_history, t_compare = st.tabs(["➕ تقييم جديد", "📚 السجل", "📊 المقارنة"])

        with t_new:
            test_type = st.selectbox("نوع التقييم", [
                "التقييم اللغوي الأولي",
                "فحص النطق والأصوات",
                "التواصل الاجتماعي",
                "تقييم الطلاقة (التلعثم)",
                "مقياس مخصص",
            ])

            with st.form("evaluation_form"):
                scores = {}

                if test_type == "التقييم اللغوي الأولي":
                    st.caption("⚠️ أداة داخلية للتوثيق وليست بديلاً عن الاختبارات المقننة المنشورة.")
                    c1, c2 = st.columns(2)
                    with c1:
                        comp = st.slider("الفهم اللغوي", 0, 10, 5)
                        expr = st.slider("التعبير اللغوي", 0, 10, 5)
                        prag = st.slider("البراغماتية", 0, 10, 5)
                    with c2:
                        vocab = st.slider("المفردات", 0, 10, 5)
                        morph = st.slider("التراكيب النحوية", 0, 10, 5)
                        narrative = st.slider("السرد", 0, 10, 5)
                    scores = {"الفهم": comp, "التعبير": expr, "البراغماتية": prag, "المفردات": vocab, "التراكيب": morph, "السرد": narrative}

                elif test_type == "فحص النطق والأصوات":
                    c1, c2 = st.columns(2)
                    errors = c1.multiselect("نوع الخطأ", ["حذف", "إبدال", "تحريف", "إضافة"])
                    phonemes = c1.text_input("الأصوات المتأثرة", placeholder="مثال: ر، س، ش")
                    position = c2.multiselect("موضع الخطأ", ["بداية الكلمة", "وسط الكلمة", "نهاية الكلمة"])
                    intelligibility = c2.slider("درجة المفهومية (%)", 0, 100, 70)
                    scores = {"الأخطاء": errors, "الأصوات": phonemes, "الموضع": position, "المفهومية": intelligibility}

                elif test_type == "التواصل الاجتماعي":
                    c1, c2 = st.columns(2)
                    eye_contact = c1.slider("التواصل البصري", 0, 4, 2)
                    turn_taking = c1.slider("تبادل الأدوار", 0, 4, 2)
                    initiation = c2.slider("المبادرة للتواصل", 0, 4, 2)
                    response = c2.slider("الاستجابة", 0, 4, 2)
                    joint_attention = c1.slider("الانتباه المشترك", 0, 4, 2)
                    play = c2.slider("اللعب التخيلي", 0, 4, 2)
                    scores = {"التواصل البصري": eye_contact, "تبادل الأدوار": turn_taking, "المبادرة": initiation, "الاستجابة": response, "الانتباه المشترك": joint_attention, "اللعب التخيلي": play}

                elif test_type == "تقييم الطلاقة (التلعثم)":
                    c1, c2 = st.columns(2)
                    frequency = c1.slider("تكرار عدم الطلاقة (%)", 0, 100, 10)
                    duration = c1.slider("متوسط مدة الانتكاسة (ث)", 0, 10, 2)
                    physical = c2.slider("التوترات الجسدية", 0, 4, 1)
                    avoidance = c2.slider("سلوكيات التجنب", 0, 4, 1)
                    attitude = c2.slider("الاتجاه نحو الكلام", 0, 4, 2)
                    scores = {"التكرار%": frequency, "مدة الانتكاسة": duration, "التوترات": physical, "التجنب": avoidance, "الاتجاه": attitude}
                else:
                    raw = st.text_area("بنود التقييم والقيم")
                    scores = {"بيانات مخصصة": raw}

                notes = st.text_area("ملاحظات الأخصائي", height=100)
                recommendations = st.text_area("التوصيات")

                if st.form_submit_button("💾 حفظ التقييم", use_container_width=True):
                    db["evaluations"].append({
                        "eval_id": uid("EV"),
                        "patient_id": selected_id,
                        "patient_name": patients[selected_id],
                        "type": test_type,
                        "date": str(date.today()),
                        "scores": scores,
                        "notes": notes.strip(),
                        "recommendations": recommendations.strip(),
                        "created_by": current_user,
                    })
                    save_all_data()
                    write_audit("ADD_EVAL", f"patient={selected_id} type={test_type}")
                    st.success("✅ تم حفظ التقييم.")

        with t_history:
            history = sorted([e for e in db["evaluations"] if e.get("patient_id") == selected_id], key=lambda x: x.get("date", ""), reverse=True)
            if history:
                for e in history:
                    with st.expander(f"📋 {e.get('date','—')} — {e.get('type','—')}"):
                        st.json(e.get("scores", {}))
                        if e.get("notes"):
                            st.write("**ملاحظات:**", e["notes"])
                        if e.get("recommendations"):
                            st.write("**التوصيات:**", e["recommendations"])
            else:
                st.info("لا توجد تقييمات لهذا الطفل.")

        with t_compare:
            history_num = [e for e in db["evaluations"] if e.get("patient_id") == selected_id and isinstance(e.get("scores"), dict) and any(isinstance(v, (int, float)) for v in e.get("scores", {}).values())]
            if len(history_num) >= 2:
                e1 = history_num[-1]
                e2 = history_num[0]
                common = [k for k in e1["scores"] if k in e2["scores"] and isinstance(e1["scores"][k], (int, float))]
                if common:
                    fig = go.Figure()
                    fig.add_trace(go.Scatterpolar(r=[e1["scores"][k] for k in common], theta=common, fill="toself", name=f"أول تقييم ({e1['date']})"))
                    fig.add_trace(go.Scatterpolar(r=[e2["scores"][k] for k in common], theta=common, fill="toself", name=f"آخر تقييم ({e2['date']})"))
                    fig.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("لا توجد بيانات رقمية مشتركة للمقارنة.")
            else:
                st.info("يحتاج إلى تقييمين رقميين على الأقل للمقارنة.")


# =========================================================
# 13) خطط العلاج
# =========================================================
elif menu == "🎯 خطط العلاج":
    st.title("🎯 خطط العلاج")

    if not db["patients"]:
        st.warning("أضف طفلاً أولاً.")
    else:
        patients = patients_dict()
        pid = st.selectbox("الطفل", list(patients), format_func=lambda x: f"{patients[x]} — {x}")
        p = patient_by_id(pid)
        existing_plan = patient_plan(pid)

        t_create, t_view, t_progress = st.tabs(["📝 إنشاء/تعديل خطة", "📄 عرض الخطة", "📊 متابعة الأهداف"])

        with t_create:
            diag = p.get("diagnosis", "أخرى") if p else "أخرى"
            suggested = THERAPY_GOALS_BANK.get(diag, [])

            with st.form("therapy_plan_form"):
                main_goal = st.text_input("الهدف الرئيسي للخطة العلاجية", value=existing_plan.get("main_goal", "") if existing_plan else "")
                start_date = st.date_input("تاريخ البدء", value=date.today())
                end_date = st.date_input("تاريخ النهاية المتوقعة", value=date.today() + timedelta(weeks=12))
                frequency = st.selectbox("تكرار الجلسات", ["مرة أسبوعياً", "مرتان أسبوعياً", "3 مرات أسبوعياً", "كل أسبوعين", "شهرياً"])

                if suggested:
                    st.markdown(f"**🎯 أهداف مقترحة لـ {diag}:**")
                    selected_suggested = st.multiselect("اختر من الأهداف المقترحة (اختياري):", suggested)
                else:
                    selected_suggested = []

                st.markdown("**أهداف فرعية (أضف حتى 10):**")
                sub_goals = []
                for i in range(6):
                    g = st.text_input(f"الهدف {i+1}", key=f"goal_{i}")
                    if g.strip():
                        sub_goals.append({"text": g.strip(), "achieved": False})

                for sg in selected_suggested:
                    if not any(g["text"] == sg for g in sub_goals):
                        sub_goals.append({"text": sg, "achieved": False})

                home_program = st.text_area("برنامج المنزل")
                notes = st.text_area("ملاحظات الخطة")

                if st.form_submit_button("💾 حفظ الخطة العلاجية", use_container_width=True):
                    if not main_goal.strip():
                        st.error("أدخل الهدف الرئيسي.")
                    elif not sub_goals:
                        st.error("أضف هدفاً فرعياً واحداً على الأقل.")
                    else:
                        plan_data = {
                            "plan_id": uid("PLAN"),
                            "patient_id": pid,
                            "patient_name": patients[pid],
                            "main_goal": main_goal.strip(),
                            "start_date": str(start_date),
                            "end_date": str(end_date),
                            "frequency": frequency,
                            "sub_goals": sub_goals,
                            "home_program": home_program.strip(),
                            "notes": notes.strip(),
                            "created_at": str(date.today()),
                            "created_by": current_user,
                        }
                        # استبدال الخطة السابقة إن وجدت
                        db["therapy_plans"] = [p2 for p2 in db["therapy_plans"] if p2.get("patient_id") != pid]
                        db["therapy_plans"].append(plan_data)
                        save_all_data()
                        write_audit("CREATE_PLAN", f"patient={pid}")
                        st.success("✅ تم حفظ الخطة العلاجية.")
                        st.rerun()

        with t_view:
            plan = patient_plan(pid)
            if plan:
                st.markdown(
                    f"""
                    <div class="patient-card">
                        <h3>🎯 الخطة العلاجية — {plan.get("patient_name","")}</h3>
                        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:12px 0;">
                            <div>📅 البداية: <strong>{plan.get("start_date","—")}</strong></div>
                            <div>📅 النهاية: <strong>{plan.get("end_date","—")}</strong></div>
                            <div>🔄 التكرار: <strong>{plan.get("frequency","—")}</strong></div>
                        </div>
                        <div>🎯 الهدف الرئيسي: <strong>{plan.get("main_goal","—")}</strong></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if plan.get("home_program"):
                    st.markdown("**🏠 برنامج المنزل:**")
                    st.write(plan["home_program"])
            else:
                st.info("لا توجد خطة علاجية لهذا الطفل. أنشئها من تبويب إنشاء الخطة.")

        with t_progress:
            plan = patient_plan(pid)
            if plan and plan.get("sub_goals"):
                st.subheader("تحديث تقدم الأهداف")
                updated = False
                for i, goal in enumerate(plan["sub_goals"]):
                    col1, col2 = st.columns([3, 1])
                    col1.write(f"{'✅' if goal.get('achieved') else '⭕'} {goal['text']}")
                    new_val = col2.checkbox("منجز", value=goal.get("achieved", False), key=f"goal_check_{i}")
                    if new_val != goal.get("achieved", False):
                        goal["achieved"] = new_val
                        updated = True

                if updated:
                    save_all_data()
                    st.success("تم تحديث تقدم الأهداف.")

                achieved_n = sum(1 for g in plan["sub_goals"] if g.get("achieved"))
                total_n = len(plan["sub_goals"])
                pct = int(achieved_n / total_n * 100) if total_n > 0 else 0
                st.markdown(
                    f'<div style="margin-top:12px;"><strong>التقدم الكلي: {pct}% ({achieved_n}/{total_n})</strong>'
                    f'<div class="progress-bar-bg" style="margin-top:6px;"><div class="progress-bar-fill" style="width:{pct}%;"></div></div></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.info("أنشئ خطة علاجية أولاً.")


# =========================================================
# 14) الجلسات والمتابعة
# =========================================================
elif menu == "📝 الجلسات والمتابعة":
    st.title("📝 الجلسات والمتابعة العلاجية")

    if not db["patients"]:
        st.info("أضف طفلاً أولاً.")
    else:
        patients = patients_dict()
        t_new, t_all, t_stats = st.tabs(["➕ جلسة جديدة", "🗂️ كل الجلسات", "📊 إحصائيات"])

        with t_new:
            with st.form("session_form"):
                c1, c2 = st.columns(2)
                s_pat = c1.selectbox("الطفل", list(patients), format_func=lambda x: patients[x])
                s_date = c2.date_input("التاريخ", value=date.today())

                c3, c4, c5 = st.columns(3)
                s_type = c3.selectbox("نوع الجلسة", SESSION_TYPES)
                s_duration = c4.number_input("المدة (دقائق)", min_value=1, max_value=300, value=45)
                s_session_num = c5.number_input("رقم الجلسة", min_value=1, value=len(patient_sessions(s_pat)) + 1)

                s_goals = st.text_area("أهداف هذه الجلسة", height=80)

                # اقتراح أهداف من الخطة
                plan = patient_plan(s_pat)
                if plan:
                    unachieved = [g["text"] for g in plan.get("sub_goals", []) if not g.get("achieved")]
                    if unachieved:
                        with st.expander("💡 اقتراحات من الخطة العلاجية"):
                            for g in unachieved:
                                st.write(f"• {g}")

                s_activities = st.text_area("الأنشطة والتمارين المنفذة", height=80)
                available_supply_names = [item.get("name", "") for item in db["supplies"] if item.get("name")]
                selected_supply_names = st.multiselect(
                    "لوازم الحصة المستخدمة",
                    available_supply_names,
                    help="تتم قراءة هذه القائمة من قسم لوازم الحصص والتذكيرات.",
                )
                other_materials = st.text_input("لوازم أو أدوات أخرى")
                deduct_session_materials = st.checkbox(
                    "خصم قطعة واحدة من مخزون اللوازم المحددة عند حفظ الجلسة",
                    value=False,
                )
                s_progress = st.slider("مستوى الإنجاز (%)", 0, 100, 50)
                s_response = st.selectbox("استجابة الطفل", ["ممتازة", "جيدة", "متوسطة", "ضعيفة", "رفض التعاون"])
                s_homework = st.text_area("برنامج المنزل لهذه الجلسة", height=60)
                s_notes = st.text_area("ملاحظات", height=60)

                c_pay, c_price = st.columns(2)
                paid_session = c_pay.checkbox("تم دفع رسوم هذه الجلسة")
                session_price = c_price.number_input("المبلغ", min_value=0.0, value=float(s_settings.get("session_price", 2000)), step=100.0) if paid_session else 0.0

                if st.form_submit_button("💾 حفظ الجلسة", use_container_width=True):
                    session_id = uid("SS")
                    db["sessions"].append({
                        "session_id": session_id,
                        "patient_id": s_pat,
                        "patient_name": patients[s_pat],
                        "date": str(s_date),
                        "type": s_type,
                        "session_num": s_session_num,
                        "duration": s_duration,
                        "goals": s_goals.strip(),
                        "activities": s_activities.strip(),
                        "materials": ", ".join(selected_supply_names + ([other_materials.strip()] if other_materials.strip() else [])),
                        "progress": s_progress,
                        "response": s_response,
                        "homework": s_homework.strip(),
                        "notes": s_notes.strip(),
                        "created_by": current_user,
                    })
                    if deduct_session_materials:
                        for supply_name in selected_supply_names:
                            supply = next(
                                (item for item in db["supplies"] if item.get("name") == supply_name),
                                None,
                            )
                            if supply and float(supply.get("quantity", 0)) > 0:
                                supply["quantity"] = max(0.0, float(supply.get("quantity", 0)) - 1)
                                supply["updated_at"] = str(date.today())
                                add_supply_movement(
                                    supply["id"],
                                    "استهلاك في جلسة",
                                    1,
                                    f"جلسة {session_id} — {patients[s_pat]}",
                                )
                    if paid_session and session_price > 0:
                        db["finances"].append({
                            "transaction_id": uid("FIN"),
                            "date": str(s_date),
                            "type": "مداخيل",
                            "desc": f"رسوم جلسة — {patients[s_pat]}",
                            "amount": float(session_price),
                            "method": "نقداً",
                            "patient_id": s_pat,
                        })
                    save_all_data()
                    write_audit("ADD_SESSION", f"patient={s_pat}")
                    st.success("✅ تم توثيق الجلسة.")

        with t_all:
            if db["sessions"]:
                c_filter = st.columns(3)
                filter_pat = c_filter[0].selectbox("تصفية بالطفل", ["الكل"] + list(patients.values()))
                filter_type = c_filter[1].selectbox("تصفية بالنوع", ["الكل"] + SESSION_TYPES)

                sessions_df = pd.DataFrame(db["sessions"]).sort_values("date", ascending=False)
                if filter_pat != "الكل":
                    sessions_df = sessions_df[sessions_df["patient_name"] == filter_pat]
                if filter_type != "الكل":
                    sessions_df = sessions_df[sessions_df["type"] == filter_type]

                show_cols = ["patient_name", "date", "type", "duration", "progress", "response"]
                available = [c for c in show_cols if c in sessions_df.columns]
                st.dataframe(
                    sessions_df[available].rename(columns={
                        "patient_name": "الطفل", "date": "التاريخ", "type": "النوع",
                        "duration": "المدة", "progress": "الإنجاز%", "response": "الاستجابة",
                    }),
                    use_container_width=True, hide_index=True,
                )
                st.caption(f"إجمالي: {len(sessions_df)} جلسة")
            else:
                st.info("لا توجد جلسات مسجلة.")

        with t_stats:
            if db["sessions"]:
                df = pd.DataFrame(db["sessions"])
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df["progress"] = pd.to_numeric(df.get("progress"), errors="coerce").fillna(0)

                c1, c2 = st.columns(2)
                with c1:
                    avg_prog = df["progress"].mean()
                    st.metric("متوسط الإنجاز", f"{avg_prog:.1f}%")
                    type_dist = df["type"].value_counts().reset_index()
                    type_dist.columns = ["النوع", "العدد"]
                    fig = px.bar(type_dist, x="النوع", y="العدد", template="plotly_white", title="توزيع أنواع الجلسات")
                    st.plotly_chart(fig, use_container_width=True)
                with c2:
                    if "response" in df.columns:
                        resp_dist = df["response"].value_counts().reset_index()
                        resp_dist.columns = ["الاستجابة", "العدد"]
                        fig2 = px.pie(resp_dist, names="الاستجابة", values="العدد", title="توزيع استجابة الطفل")
                        st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("لا توجد بيانات كافية.")


# =========================================================
# 15) المواعيد
# =========================================================
elif menu == "📅 المواعيد":
    st.title("📅 إدارة المواعيد")

    if not db["patients"]:
        st.info("أضف أطفالاً أولاً.")
    else:
        patients = patients_dict()
        t_add, t_view, t_calendar = st.tabs(["➕ إضافة موعد", "📋 عرض المواعيد", "📆 نظرة أسبوعية"])

        with t_add:
            with st.form("appointment_form"):
                a, b, c = st.columns(3)
                a_pat = a.selectbox("الطفل", list(patients), format_func=lambda x: patients[x])
                a_date = b.date_input("التاريخ", value=date.today())
                a_time = c.time_input("الوقت")

                d, e, f_col = st.columns(3)
                a_type = d.selectbox("نوع الموعد", APPOINTMENT_TYPES)
                a_duration = e.number_input("المدة (دقائق)", 15, 240, 45, step=15)
                a_status = f_col.selectbox("الحالة", ["مؤكد", "معلق", "مؤجل"])

                a_notes = st.text_area("ملاحظات")
                a_reminder = st.checkbox("إضافة تذكير", value=True)

                if st.form_submit_button("➕ إضافة الموعد", use_container_width=True):
                    collision = any(
                        ap.get("date") == str(a_date)
                        and ap.get("time") == str(a_time)
                        and ap.get("status") not in ["ملغى", "لم يحضر"]
                        for ap in db["appointments"]
                    )
                    if collision:
                        st.error("⚠️ يوجد موعد آخر في نفس التاريخ والوقت.")
                    else:
                        db["appointments"].append({
                            "appointment_id": uid("AP"),
                            "patient_id": a_pat,
                            "patient_name": patients[a_pat],
                            "date": str(a_date),
                            "time": str(a_time),
                            "type": a_type,
                            "duration": a_duration,
                            "notes": a_notes.strip(),
                            "status": a_status,
                            "reminder": a_reminder,
                            "created_by": current_user,
                        })
                        if a_reminder:
                            reminder_days = int(s_settings.get("reminder_days", 1))
                            reminder_due_date = a_date - timedelta(days=max(0, reminder_days))
                            db["reminders"].append({
                                "id": uid("REM"),
                                "title": f"تذكير بموعد الطفل — {patients[a_pat]}",
                                "kind": "موعد",
                                "priority": "مهمة",
                                "due_date": str(reminder_due_date),
                                "due_time": str(a_time)[:5],
                                "repeat": "لا يتكرر",
                                "patient_id": a_pat,
                                "patient_name": patients[a_pat],
                                "notes": f"الموعد بتاريخ {a_date} الساعة {str(a_time)[:5]}",
                                "status": "مفتوح",
                                "source_appointment_id": db["appointments"][-1]["appointment_id"],
                                "created_at": datetime.now().isoformat(timespec="minutes"),
                                "created_by": current_user,
                            })
                        save_all_data()
                        write_audit("ADD_APPOINTMENT", f"patient={a_pat} date={a_date}")
                        st.success("✅ تمت إضافة الموعد.")

        with t_view:
            if db["appointments"]:
                c_filter1, c_filter2 = st.columns(2)
                f_status = c_filter1.selectbox("تصفية بالحالة", ["الكل", "مؤكد", "معلق", "منجز", "ملغى", "لم يحضر"])
                f_date_range = c_filter2.selectbox("الفترة", ["الكل", "اليوم", "هذا الأسبوع", "هذا الشهر"])

                df = pd.DataFrame(db["appointments"])
                df["date_parsed"] = pd.to_datetime(df["date"], errors="coerce")

                if f_status != "الكل":
                    df = df[df["status"] == f_status]
                if f_date_range == "اليوم":
                    df = df[df["date"] == str(date.today())]
                elif f_date_range == "هذا الأسبوع":
                    week_start = date.today() - timedelta(days=date.today().weekday())
                    df = df[df["date_parsed"] >= pd.Timestamp(week_start)]
                elif f_date_range == "هذا الشهر":
                    month_start = date.today().replace(day=1)
                    df = df[df["date_parsed"] >= pd.Timestamp(month_start)]

                df = df.sort_values(["date", "time"], ascending=[False, True])
                show = ["appointment_id", "date", "time", "patient_name", "type", "duration", "status"]
                available = [c for c in show if c in df.columns]
                st.dataframe(df[available].rename(columns={
                    "appointment_id": "الرقم", "date": "التاريخ", "time": "الوقت",
                    "patient_name": "الطفل", "type": "النوع", "duration": "المدة",
                    "status": "الحالة",
                }), use_container_width=True, hide_index=True)

                ids = df["appointment_id"].tolist()
                if ids:
                    chosen = st.selectbox("تحديث حالة موعد:", ids)
                    new_status = st.selectbox("الحالة الجديدة:", ["مؤكد", "منجز", "ملغى", "لم يحضر", "معلق", "مؤجل"])
                    if st.button("💾 حفظ الحالة"):
                        item = next((x for x in db["appointments"] if x["appointment_id"] == chosen), None)
                        if item:
                            item["status"] = new_status
                            save_all_data()
                            st.success("تم تحديث الحالة.")
                            st.rerun()
            else:
                st.info("لا توجد مواعيد مسجلة.")

        with t_calendar:
            st.subheader("📆 مواعيد الأسبوع الحالي")
            week_start = date.today() - timedelta(days=date.today().weekday())
            week_days = [week_start + timedelta(days=i) for i in range(7)]
            day_names = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]

            week_apts = {str(d): [] for d in week_days}
            for apt in db["appointments"]:
                if apt.get("date") in week_apts:
                    week_apts[apt["date"]].append(apt)

            cols = st.columns(7)
            for i, (col, day) in enumerate(zip(cols, week_days)):
                with col:
                    is_today = day == date.today()
                    style = "background:#1d4ed8;color:white;" if is_today else "background:#f1f5f9;"
                    col.markdown(
                        f'<div style="{style}border-radius:8px;padding:6px;text-align:center;margin-bottom:6px;">'
                        f'<strong>{day_names[i]}</strong><br><small>{day.strftime("%d/%m")}</small></div>',
                        unsafe_allow_html=True,
                    )
                    for apt in sorted(week_apts[str(day)], key=lambda x: x.get("time", "")):
                        status_color = {"مؤكد": "#059669", "معلق": "#f59e0b", "ملغى": "#dc2626"}.get(apt.get("status"), "#64748b")
                        col.markdown(
                            f'<div style="background:white;border-right:3px solid {status_color};border-radius:6px;padding:4px 6px;margin-bottom:4px;font-size:.8rem;">'
                            f'{apt.get("time","")}<br><strong>{apt.get("patient_name","")}</strong></div>',
                            unsafe_allow_html=True,
                        )


# =========================================================
# 16) لوازم الحصص والتذكيرات
# =========================================================
elif menu == "🧰 لوازم الحصص والتذكيرات":
    st.title("🧰 لوازم الحصص والتذكيرات")
    st.caption("نظّم أدوات الحصص، راقب الكميات، ولا تفوّت موعداً أو مهمة مهمة.")

    supplies = db["supplies"]
    reminders = db["reminders"]
    open_reminders = [r for r in reminders if r.get("status", "مفتوح") not in ["منجز", "ملغى"]]
    overdue_reminders = [r for r in open_reminders if reminder_is_overdue(r)]
    low_stock = [
        item for item in supplies
        if float(item.get("quantity", 0)) <= float(item.get("min_quantity", 0))
    ]

    summary_cols = st.columns(4)
    summary_cols[0].metric("📦 أصناف اللوازم", len(supplies))
    summary_cols[1].metric("⚠️ مخزون منخفض", len(low_stock))
    summary_cols[2].metric("🔔 تذكيرات مفتوحة", len(open_reminders))
    summary_cols[3].metric("🚨 تذكيرات متأخرة", len(overdue_reminders))

    tab_supplies, tab_supply_history, tab_reminders, tab_overview = st.tabs([
        "📦 إدارة اللوازم", "📜 حركة المخزون", "🔔 إدارة التذكيرات", "📊 المتابعة السريعة"
    ])

    with tab_supplies:
        st.subheader("📦 مخزون لوازم الحصص")
        with st.form("add_supply_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            supply_name = c1.text_input("اسم الأداة أو الوسيلة *")
            supply_category = c2.selectbox("الفئة", [
                "بطاقات وصور", "ألعاب تعليمية", "أدوات فنية",
                "أدوات نطق", "قرطاسية", "نظافة وسلامة", "أخرى"
            ])
            supply_unit = c3.text_input("وحدة القياس", value="قطعة")
            c4, c5, c6 = st.columns(3)
            supply_quantity = c4.number_input("الكمية الحالية", min_value=0.0, step=1.0)
            supply_min = c5.number_input("حد التنبيه", min_value=0.0, step=1.0, value=1.0)
            supply_location = c6.text_input("مكان التخزين")
            supply_notes = st.text_area("ملاحظات")
            if st.form_submit_button("➕ إضافة إلى المخزون", use_container_width=True):
                if not supply_name.strip():
                    st.error("اسم الأداة أو الوسيلة مطلوب.")
                else:
                    supply_id = uid("SUP")
                    supplies.append({
                        "id": supply_id,
                        "name": supply_name.strip(),
                        "category": supply_category,
                        "unit": supply_unit.strip() or "قطعة",
                        "quantity": float(supply_quantity),
                        "min_quantity": float(supply_min),
                        "location": supply_location.strip(),
                        "notes": supply_notes.strip(),
                        "created_at": str(date.today()),
                        "updated_at": str(date.today()),
                        "created_by": current_user,
                    })
                    add_supply_movement(supply_id, "إضافة أولية", supply_quantity, "إضافة صنف جديد")
                    save_all_data()
                    write_audit("ADD_SUPPLY", f"name={supply_name.strip()}")
                    st.success("✅ تمت إضافة الأداة إلى المخزون.")
                    st.rerun()

        if supplies:
            st.markdown("#### الأصناف المسجلة")
            supply_rows = []
            for item in supplies:
                quantity = float(item.get("quantity", 0))
                minimum = float(item.get("min_quantity", 0))
                supply_rows.append({
                    "id": item.get("id", ""),
                    "الأداة/الوسيلة": item.get("name", ""),
                    "الفئة": item.get("category", ""),
                    "الكمية": f"{quantity:g} {item.get('unit', 'قطعة')}",
                    "الحد الأدنى": f"{minimum:g}",
                    "الحالة": "⚠️ يحتاج إعادة توفير" if quantity <= minimum else "✅ متوفر",
                    "مكان التخزين": item.get("location", "") or "—",
                })
            st.dataframe(
                pd.DataFrame(supply_rows).drop(columns=["id"]),
                use_container_width=True,
                hide_index=True,
            )

            supply_ids = [item["id"] for item in supplies]
            selected_supply_id = st.selectbox(
                "اختر صنفاً للتعديل أو تسجيل الاستهلاك",
                supply_ids,
                format_func=lambda x: f"{supply_by_id(x).get('name', x)} — {supply_by_id(x).get('category', '')}",
            )
            selected_supply = supply_by_id(selected_supply_id)
            if selected_supply:
                edit_col, use_col = st.columns([1.4, 1])
                with edit_col:
                    with st.form("edit_supply_form"):
                        edited_supply_name = st.text_input("اسم الأداة/الوسيلة", value=selected_supply.get("name", ""))
                        edited_category = st.selectbox(
                            "الفئة",
                            ["بطاقات وصور", "ألعاب تعليمية", "أدوات فنية", "أدوات نطق", "قرطاسية", "نظافة وسلامة", "أخرى"],
                            index=["بطاقات وصور", "ألعاب تعليمية", "أدوات فنية", "أدوات نطق", "قرطاسية", "نظافة وسلامة", "أخرى"].index(selected_supply.get("category", "أخرى"))
                            if selected_supply.get("category", "أخرى") in ["بطاقات وصور", "ألعاب تعليمية", "أدوات فنية", "أدوات نطق", "قرطاسية", "نظافة وسلامة", "أخرى"] else 6,
                        )
                        e1, e2 = st.columns(2)
                        edited_quantity = e1.number_input("الكمية", min_value=0.0, value=float(selected_supply.get("quantity", 0)), step=1.0)
                        edited_min = e2.number_input("حد التنبيه", min_value=0.0, value=float(selected_supply.get("min_quantity", 0)), step=1.0)
                        edited_unit = st.text_input("وحدة القياس", value=selected_supply.get("unit", "قطعة"))
                        edited_location = st.text_input("مكان التخزين", value=selected_supply.get("location", ""))
                        edited_notes = st.text_area("ملاحظات", value=selected_supply.get("notes", ""))
                        if st.form_submit_button("💾 حفظ بيانات الصنف", use_container_width=True):
                            if not edited_supply_name.strip():
                                st.error("اسم الأداة أو الوسيلة مطلوب.")
                            else:
                                old_quantity = float(selected_supply.get("quantity", 0))
                                new_quantity = float(edited_quantity)
                                selected_supply.update({
                                    "name": edited_supply_name.strip(),
                                    "category": edited_category,
                                    "quantity": new_quantity,
                                    "min_quantity": float(edited_min),
                                    "unit": edited_unit.strip() or "قطعة",
                                    "location": edited_location.strip(),
                                    "notes": edited_notes.strip(),
                                    "updated_at": str(date.today()),
                                })
                                if new_quantity != old_quantity:
                                    movement_type = "إضافة يدوية" if new_quantity > old_quantity else "تسوية كمية"
                                    add_supply_movement(
                                        selected_supply_id,
                                        movement_type,
                                        abs(new_quantity - old_quantity),
                                        "تعديل مباشر من بيانات الصنف",
                                    )
                                save_all_data()
                                write_audit("UPDATE_SUPPLY", f"id={selected_supply_id}")
                                st.success("✅ تم تحديث بيانات الصنف.")
                                st.rerun()

                with use_col:
                    st.markdown("#### إعادة توفير")
                    restock_quantity = st.number_input(
                        "الكمية المضافة",
                        min_value=0.0,
                        value=0.0,
                        step=1.0,
                        key=f"restock_{selected_supply_id}",
                    )
                    if st.button("📈 إضافة إلى المخزون", use_container_width=True):
                        if restock_quantity <= 0:
                            st.error("أدخل كمية أكبر من صفر.")
                        else:
                            selected_supply["quantity"] = float(selected_supply.get("quantity", 0)) + float(restock_quantity)
                            selected_supply["updated_at"] = str(date.today())
                            add_supply_movement(
                                selected_supply_id,
                                "إعادة توفير",
                                restock_quantity,
                                "إضافة كمية من شاشة المخزون",
                            )
                            save_all_data()
                            write_audit("RESTOCK_SUPPLY", f"id={selected_supply_id} quantity={restock_quantity}")
                            st.success("✅ تمت إضافة الكمية إلى المخزون.")
                            st.rerun()

                    st.markdown("#### تسجيل الاستهلاك")
                    consumed_quantity = st.number_input(
                        "الكمية المستخدمة",
                        min_value=0.0,
                        max_value=float(selected_supply.get("quantity", 0)),
                        value=1.0 if float(selected_supply.get("quantity", 0)) >= 1 else 0.0,
                        step=1.0,
                        key=f"consume_{selected_supply_id}",
                    )
                    if st.button("📉 خصم من المخزون", use_container_width=True):
                        if consumed_quantity <= 0:
                            st.error("أدخل كمية أكبر من صفر.")
                        else:
                            selected_supply["quantity"] = max(
                                0.0, float(selected_supply.get("quantity", 0)) - float(consumed_quantity)
                            )
                            selected_supply["updated_at"] = str(date.today())
                            add_supply_movement(
                                selected_supply_id,
                                "استهلاك يدوي",
                                consumed_quantity,
                                "خصم من شاشة المخزون",
                            )
                            save_all_data()
                            write_audit("CONSUME_SUPPLY", f"id={selected_supply_id} quantity={consumed_quantity}")
                            st.success("✅ تم خصم الكمية من المخزون.")
                            st.rerun()

                    st.markdown('<div class="warning-box">الحذف يزيل الصنف من سجل المخزون نهائياً.</div>', unsafe_allow_html=True)
                    confirm_supply_delete = st.checkbox("أؤكد حذف هذا الصنف", key=f"confirm_supply_delete_{selected_supply_id}")
                    if st.button("🗑️ حذف الصنف", type="secondary", use_container_width=True):
                        if not confirm_supply_delete:
                            st.error("فعّل التأكيد قبل الحذف.")
                        else:
                            db["supplies"] = [item for item in supplies if item.get("id") != selected_supply_id]
                            save_all_data()
                            write_audit("DELETE_SUPPLY", f"id={selected_supply_id}")
                            st.success("تم حذف الصنف.")
                            st.rerun()
        else:
            st.info("لم تتم إضافة لوازم بعد. ابدأ بإضافة الأدوات المستخدمة في الحصص.")

    with tab_supply_history:
        st.subheader("📜 سجل حركة المخزون")
        movements = db.get("supply_movements", [])
        if movements:
            movement_df = pd.DataFrame(movements).sort_values("date", ascending=False)
            movement_df["quantity"] = pd.to_numeric(movement_df["quantity"], errors="coerce").fillna(0)
            movement_df["quantity"] = movement_df.apply(
                lambda row: f"{'+' if 'إضافة' in str(row['type']) or 'إعادة' in str(row['type']) else '-'}{row['quantity']:g}",
                axis=1,
            )
            st.dataframe(
                movement_df[["date", "supply_name", "type", "quantity", "note"]].rename(columns={
                    "date": "التاريخ",
                    "supply_name": "الأداة/الوسيلة",
                    "type": "نوع الحركة",
                    "quantity": "الكمية",
                    "note": "الملاحظة",
                }),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("لا توجد حركات مسجلة للمخزون بعد.")

    with tab_reminders:
        st.subheader("🔔 التذكيرات والمهام")
        patients_for_reminders = patients_dict()
        with st.form("add_reminder_form", clear_on_submit=True):
            r1, r2, r3 = st.columns(3)
            reminder_title = r1.text_input("عنوان التذكير *", placeholder="مثال: الاتصال بولي الأمر")
            reminder_kind = r2.selectbox("النوع", ["موعد", "مهمة إدارية", "متابعة طفل", "تجهيز حصة", "إعادة توفير لوازم", "أخرى"])
            reminder_priority = r3.selectbox("الأولوية", ["عادية", "مهمة", "عاجلة"])
            r4, r5, r6 = st.columns(3)
            reminder_date = r4.date_input("تاريخ الاستحقاق", value=date.today())
            reminder_time = r5.time_input("الوقت", value=datetime.now().replace(second=0, microsecond=0).time())
            reminder_repeat = r6.selectbox("التكرار", ["لا يتكرر", "يومياً", "أسبوعياً", "شهرياً"])
            reminder_patient = st.selectbox(
                "ربط بطفل (اختياري)",
                ["بدون ربط"] + list(patients_for_reminders),
                format_func=lambda x: "بدون ربط" if x == "بدون ربط" else patients_for_reminders[x],
            )
            reminder_notes = st.text_area("تفاصيل التذكير")
            if st.form_submit_button("➕ إضافة التذكير", use_container_width=True):
                if not reminder_title.strip():
                    st.error("عنوان التذكير مطلوب.")
                else:
                    patient_id = None if reminder_patient == "بدون ربط" else reminder_patient
                    reminder_id = uid("REM")
                    reminders.append({
                        "id": reminder_id,
                        "series_id": reminder_id,
                        "title": reminder_title.strip(),
                        "kind": reminder_kind,
                        "priority": reminder_priority,
                        "due_date": str(reminder_date),
                        "due_time": str(reminder_time)[:5],
                        "repeat": reminder_repeat,
                        "patient_id": patient_id,
                        "patient_name": patient_name(patient_id) if patient_id else "",
                        "notes": reminder_notes.strip(),
                        "status": "مفتوح",
                        "created_at": datetime.now().isoformat(timespec="minutes"),
                        "created_by": current_user,
                    })
                    save_all_data()
                    write_audit("ADD_REMINDER", f"title={reminder_title.strip()}")
                    st.success("✅ تمت إضافة التذكير.")
                    st.rerun()

        if reminders:
            f1, f2 = st.columns(2)
            reminder_status_filter = f1.selectbox("تصفية الحالة", ["الكل", "مفتوح", "قيد التنفيذ", "منجز", "ملغى"])
            reminder_period_filter = f2.selectbox("تصفية الفترة", ["الكل", "متأخر", "اليوم", "هذا الأسبوع"])
            shown_reminders = list(reminders)
            if reminder_status_filter != "الكل":
                shown_reminders = [r for r in shown_reminders if r.get("status", "مفتوح") == reminder_status_filter]
            if reminder_period_filter == "متأخر":
                shown_reminders = [r for r in shown_reminders if reminder_is_overdue(r)]
            elif reminder_period_filter == "اليوم":
                shown_reminders = [r for r in shown_reminders if r.get("due_date") == str(date.today())]
            elif reminder_period_filter == "هذا الأسبوع":
                week_start = date.today() - timedelta(days=date.today().weekday())
                week_end = week_start + timedelta(days=6)
                shown_reminders = [
                    r for r in shown_reminders
                    if str(week_start) <= r.get("due_date", "") <= str(week_end)
                ]

            if shown_reminders:
                reminder_rows = []
                for item in sorted(shown_reminders, key=lambda r: (r.get("due_date", ""), r.get("due_time", ""))):
                    status = item.get("status", "مفتوح")
                    reminder_rows.append({
                        "id": item.get("id", ""),
                        "العنوان": item.get("title", ""),
                        "النوع": item.get("kind", ""),
                        "الاستحقاق": f"{item.get('due_date', '')} {item.get('due_time', '')}",
                        "الطفل": reminder_patient_label(item),
                        "الأولوية": item.get("priority", ""),
                        "الحالة": "🚨 متأخر" if reminder_is_overdue(item) else status,
                    })
                st.dataframe(
                    pd.DataFrame(reminder_rows).drop(columns=["id"]),
                    use_container_width=True,
                    hide_index=True,
                )

                reminder_ids = [item["id"] for item in shown_reminders]
                selected_reminder_id = st.selectbox(
                    "اختر تذكيراً لتحديثه",
                    reminder_ids,
                    format_func=lambda x: f"{reminder_by_id(x).get('due_date', '')} — {reminder_by_id(x).get('title', x)}",
                )
                selected_reminder = reminder_by_id(selected_reminder_id)
                if selected_reminder:
                    update_col, delete_col = st.columns([1.5, 1])
                    with update_col:
                        new_reminder_status = st.selectbox(
                            "الحالة الجديدة",
                            ["مفتوح", "قيد التنفيذ", "منجز", "ملغى"],
                            index=["مفتوح", "قيد التنفيذ", "منجز", "ملغى"].index(selected_reminder.get("status", "مفتوح"))
                            if selected_reminder.get("status", "مفتوح") in ["مفتوح", "قيد التنفيذ", "منجز", "ملغى"] else 0,
                        )
                        if st.button("💾 تحديث حالة التذكير", use_container_width=True):
                            selected_reminder["status"] = new_reminder_status
                            selected_reminder["completed_at"] = datetime.now().isoformat(timespec="minutes") if new_reminder_status == "منجز" else ""
                            next_created = False
                            if new_reminder_status == "منجز":
                                try:
                                    next_created = create_next_recurring_reminder(selected_reminder)
                                except (TypeError, ValueError):
                                    next_created = False
                            save_all_data()
                            write_audit("UPDATE_REMINDER", f"id={selected_reminder_id} status={new_reminder_status}")
                            if next_created:
                                st.success("✅ تم إنجاز التذكير وإنشاء موعده التالي تلقائياً.")
                            else:
                                st.success("✅ تم تحديث حالة التذكير.")
                            st.rerun()
                        if selected_reminder.get("notes"):
                            st.info(selected_reminder["notes"])
                    with delete_col:
                        st.markdown('<div class="warning-box">حذف التذكير نهائي.</div>', unsafe_allow_html=True)
                        confirm_reminder_delete = st.checkbox("أؤكد الحذف", key=f"confirm_reminder_delete_{selected_reminder_id}")
                        if st.button("🗑️ حذف التذكير", type="secondary", use_container_width=True):
                            if not confirm_reminder_delete:
                                st.error("فعّل التأكيد قبل الحذف.")
                            else:
                                db["reminders"] = [item for item in reminders if item.get("id") != selected_reminder_id]
                                save_all_data()
                                write_audit("DELETE_REMINDER", f"id={selected_reminder_id}")
                                st.success("تم حذف التذكير.")
                                st.rerun()
            else:
                st.info("لا توجد تذكيرات توافق التصفية الحالية.")
        else:
            st.info("لا توجد تذكيرات بعد. أضف تذكيراً لمهمة أو موعد أو متابعة.")

    with tab_overview:
        st.subheader("📊 المتابعة السريعة")
        overview_col1, overview_col2 = st.columns(2)
        with overview_col1:
            st.markdown("#### 🚨 المتأخرة")
            if overdue_reminders:
                for item in sorted(overdue_reminders, key=lambda r: r.get("due_date", "")):
                    st.markdown(
                        f'<div class="danger-box"><strong>{item.get("title", "")}</strong><br>'
                        f'{item.get("due_date", "—")} • {reminder_patient_label(item)}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.success("✅ لا توجد تذكيرات متأخرة.")
        with overview_col2:
            st.markdown("#### ⚠️ لوازم تحتاج إعادة توفير")
            if low_stock:
                for item in low_stock:
                    st.markdown(
                        f'<div class="warning-box"><strong>{item.get("name", "")}</strong><br>'
                        f'المتاح: {float(item.get("quantity", 0)):g} {item.get("unit", "قطعة")} '
                        f'— الحد الأدنى: {float(item.get("min_quantity", 0)):g}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.success("✅ مستويات المخزون جيدة.")


# =========================================================
# 17) الإدارة المالية
# =========================================================
elif menu == "💰 الإدارة المالية":
    st.title("💰 الإدارة المالية والفوترة")
    currency = s_settings.get("currency", "د.ج")

    t_add, t_records, t_reports = st.tabs(["➕ تسجيل عملية", "📜 السجلات", "📊 التقارير المالية"])

    with t_add:
        left, right = st.columns([1.1, 1])
        with left:
            with st.form("finance_form"):
                f_type = st.radio("نوع العملية", ["مداخيل", "مصاريف"], horizontal=True)
                c1, c2 = st.columns(2)
                f_date = c1.date_input("التاريخ", value=date.today())
                f_method = c2.selectbox("طريقة الدفع", ["نقداً", "تحويل بنكي", "بطاقة", "CCP", "أخرى"])
                f_desc = st.text_input("البيان *")
                f_amount = st.number_input("المبلغ *", min_value=0.0, step=100.0)
                f_category = st.selectbox("الفئة", [
                    "رسوم جلسة", "رسوم تقييم", "مصاريف إيجار", "مصاريف معدات", "مصاريف مستلزمات", "راتب", "أخرى"
                ])
                f_patient = st.selectbox(
                    "الطفل (اختياري)",
                    ["بدون ربط"] + [p["id"] for p in db["patients"]],
                    format_func=lambda x: "بدون ربط" if x == "بدون ربط" else patient_name(x),
                )
                f_invoice = st.checkbox("إنشاء فاتورة")

                if st.form_submit_button("💾 تسجيل العملية", use_container_width=True):
                    if not f_desc.strip() or f_amount <= 0:
                        st.error("أدخل البيان والمبلغ.")
                    else:
                        db["finances"].append({
                            "transaction_id": uid("FIN"),
                            "date": str(f_date),
                            "type": f_type,
                            "desc": f_desc.strip(),
                            "amount": float(f_amount),
                            "method": f_method,
                            "category": f_category,
                            "patient_id": None if f_patient == "بدون ربط" else f_patient,
                        })
                        save_all_data()
                        write_audit("ADD_FINANCE", f"type={f_type} amount={f_amount}")
                        st.success("✅ تم تسجيل العملية.")

        with right:
            total_in = sum(float(x.get("amount", 0)) for x in db["finances"] if x.get("type") == "مداخيل")
            total_out = sum(float(x.get("amount", 0)) for x in db["finances"] if x.get("type") == "مصاريف")
            net = total_in - total_out

            st.markdown(f'<div class="metric-card" style="border-right-color:#059669;"><div class="metric-title">💚 إجمالي المداخيل</div><div class="metric-value">{total_in:,.0f} {currency}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-card" style="border-right-color:#e11d48;"><div class="metric-title">🔴 إجمالي المصاريف</div><div class="metric-value">{total_out:,.0f} {currency}</div></div>', unsafe_allow_html=True)
            net_color = "#059669" if net >= 0 else "#e11d48"
            st.markdown(f'<div class="metric-card" style="border-right-color:{net_color};"><div class="metric-title">💰 الصافي</div><div class="metric-value" style="color:{net_color};">{net:,.0f} {currency}</div></div>', unsafe_allow_html=True)

    with t_records:
        if db["finances"]:
            c1, c2, c3 = st.columns(3)
            ft_type = c1.selectbox("النوع", ["الكل", "مداخيل", "مصاريف"])
            ft_month = c2.selectbox("الشهر", ["الكل"] + [f"{y}-{m:02d}" for y in range(date.today().year, date.today().year-2, -1) for m in range(12, 0, -1)])
            ft_cat = c3.selectbox("الفئة", ["الكل", "رسوم جلسة", "رسوم تقييم", "مصاريف إيجار", "مصاريف معدات", "مصاريف مستلزمات", "راتب", "أخرى"])

            df = pd.DataFrame(db["finances"]).sort_values("date", ascending=False)
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

            if ft_type != "الكل":
                df = df[df["type"] == ft_type]
            if ft_month != "الكل":
                df = df[df["date"].str.startswith(ft_month)]
            if ft_cat != "الكل" and "category" in df.columns:
                df = df[df["category"] == ft_cat]

            show_cols = ["transaction_id", "date", "type", "desc", "amount", "method"]
            if "category" in df.columns:
                show_cols.insert(3, "category")
            available = [c for c in show_cols if c in df.columns]
            st.dataframe(df[available].rename(columns={
                "transaction_id": "الرقم", "date": "التاريخ", "type": "النوع",
                "desc": "البيان", "amount": "المبلغ", "method": "الدفع", "category": "الفئة",
            }), use_container_width=True, hide_index=True)
            st.metric("مجموع العمليات المعروضة", f"{df['amount'].sum():,.0f} {currency}")
        else:
            st.info("لا توجد عمليات مالية.")

    with t_reports:
        if db["finances"]:
            df = pd.DataFrame(db["finances"])
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
            df["date_parsed"] = pd.to_datetime(df["date"], errors="coerce")
            df["month"] = df["date_parsed"].dt.to_period("M").astype(str)

            c1, c2 = st.columns(2)
            with c1:
                monthly = df.groupby(["month", "type"])["amount"].sum().reset_index()
                fig = px.line(monthly, x="month", y="amount", color="type", markers=True, template="plotly_white", title="المداخيل والمصاريف الشهرية")
                fig.update_layout(xaxis_title="الشهر", yaxis_title=f"المبلغ ({currency})")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                if "category" in df.columns:
                    cat_sum = df[df["type"] == "مصاريف"].groupby("category")["amount"].sum().reset_index()
                    if not cat_sum.empty:
                        fig2 = px.pie(cat_sum, names="category", values="amount", title="توزيع المصاريف بالفئة")
                        st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("لا توجد بيانات مالية كافية.")


# =========================================================
# 17) المساعد الذكي Gemini
# =========================================================
elif menu == "🤖 المساعد الذكي":
    st.title("🤖 المساعد الذكي — Gemini")
    st.markdown(
        '<div class="warning-box">⚠️ المخرجات مساعدة تنظيمية ولا تُغني عن التقييم السريري والاختبارات المقننة والحكم المهني.</div>',
        unsafe_allow_html=True,
    )

    env_key = os.getenv("GEMINI_API_KEY", "")
    api_key = st.text_input("🔑 Gemini API Key", value=env_key, type="password", help="يفضل وضع المفتاح في متغير البيئة GEMINI_API_KEY")

    col1, col2 = st.columns(2)
    model = col1.text_input("النموذج", value=s_settings.get("gemini_model", "gemini-2.5-flash"))
    task = col2.selectbox("المهمة", [
        "تحليل حالة وبناء خطة أولية",
        "اقتراح أنشطة وتمارين لغوية",
        "صياغة تقرير مهني للأهل",
        "تلخيص سجل الطفل",
        "اقتراح أهداف جلسة قادمة",
        "كتابة برنامج منزلي مفصل",
        "ترجمة تقرير للأهل بلغة مبسطة",
    ])

    # تحميل بيانات طفل موجود
    if db["patients"]:
        use_patient = st.checkbox("استخدم بيانات طفل موجود")
        if use_patient:
            patients = patients_dict()
            sel_pid = st.selectbox("الطفل", list(patients), format_func=lambda x: f"{patients[x]} — {x}")
            p = patient_by_id(sel_pid)
            if p:
                auto_context = f"""
الطفل: {p.get("name", "")}
العمر: {age_label(p.get("dob", ""))}
الجنس: {p.get("gender", "")}
التشخيص: {p.get("diagnosis", "")}
التاريخ: {p.get("history", "")}
عدد الجلسات: {len(patient_sessions(sel_pid))}
آخر ملاحظات: {p.get("notes", "")}
"""
                context = st.text_area("تفاصيل الحالة (تم ملؤها تلقائياً)", value=auto_context.strip(), height=200)
            else:
                context = st.text_area("تفاصيل الحالة", height=200)
        else:
            context = st.text_area("تفاصيل الحالة", height=200, placeholder="العمر، المشكلة، نتائج التقييم، الملاحظات...")
    else:
        context = st.text_area("تفاصيل الحالة", height=200, placeholder="العمر، المشكلة، نتائج التقييم...")

    language = st.selectbox("لغة المخرجات", ["العربية", "الفرنسية", "الإنجليزية"])

    if st.button("🧠 تشغيل المساعد", use_container_width=True):
        if not api_key:
            st.error("أدخل مفتاح Gemini.")
        elif genai is None:
            st.error("حزمة google-genai غير مثبتة.")
        elif not context.strip():
            st.warning("أدخل تفاصيل الحالة.")
        else:
            lang_instruction = {"العربية": "باللغة العربية الفصحى الواضحة", "الفرنسية": "en français", "الإنجليزية": "in English"}.get(language, "")
            prompt = f"""
أنت أخصائي متخصص في الأرطوفونيا (علاج النطق واللغة).
المهمة: {task}
يُرجى الإجابة {lang_instruction} مع تنظيم المحتوى في أقسام واضحة:

1. تحليل المعطيات المتاحة
2. الاستنتاجات والفرضيات المحتملة
3. مقترحات عملية مفصلة
4. ما يحتاج إلى تحقق سريري أو اختبارات مقننة

⚠️ لا تقدم تشخيصاً نهائياً من النص وحده — هذا مساعد منظّم فقط.

تفاصيل الحالة:
{context}
"""
            with st.spinner("جاري المعالجة..."):
                try:
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(model=model.strip() or "gemini-2.5-flash", contents=prompt)
                    result = response.text or "لم يعد النموذج نصاً."
                    st.success("✅ تم إنشاء المحتوى.")
                    st.markdown(result)
                    st.download_button("⬇️ تحميل النتيجة", data=result.encode("utf-8"), file_name=f"ai_result_{date.today().isoformat()}.txt", mime="text/plain")
                    write_audit("AI_QUERY", f"task={task}")
                except Exception as exc:
                    st.error(f"خطأ في الاتصال بـ Gemini: {exc}")


# =========================================================
# 18) مكتبة العيادة
# =========================================================
elif menu == "📚 مكتبة العيادة":
    st.title("📚 مكتبة العيادة والأدوات")

    tab_cards, tab_activities, tab_files, tab_notes = st.tabs(["🧩 بطاقات مفردات", "🎮 أنشطة", "📎 الملفات", "📝 ملاحظات"])

    with tab_cards:
        card_groups = {
            "🍎 الفواكه": ["تفاح", "موز", "برتقال", "عنب", "بطيخ", "مانغو", "خوخ", "إجاص"],
            "🥦 الخضار": ["جزر", "طماطم", "بطاطس", "بصل", "ثوم", "خيار", "فلفل", "باذنجان"],
            "🦁 الحيوانات": ["أسد", "قطة", "كلب", "فيل", "حصان", "قرد", "أرنب", "ثعلب"],
            "🚗 وسائل النقل": ["سيارة", "حافلة", "قطار", "طائرة", "سفينة", "دراجة", "شاحنة", "مروحية"],
            "👕 الملابس": ["قميص", "بنطال", "فستان", "حذاء", "قبعة", "معطف", "جوارب", "وشاح"],
            "🏠 الأثاث": ["كرسي", "طاولة", "سرير", "خزانة", "باب", "نافذة", "صوفا", "مرآة"],
            "🎨 الألوان": ["أحمر", "أزرق", "أخضر", "أصفر", "أبيض", "أسود", "برتقالي", "بنفسجي"],
            "🔢 الأرقام": ["واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية"],
        }
        selected_group = st.selectbox("اختر مجموعة", list(card_groups.keys()))
        items = card_groups[selected_group]
        cols = st.columns(4)
        for i, item in enumerate(items):
            cols[i % 4].markdown(
                f'<div style="background:white;border-radius:12px;padding:16px;text-align:center;margin:6px;box-shadow:0 2px 8px rgba(0,0,0,.06);font-size:1.1rem;font-weight:700;">{item}</div>',
                unsafe_allow_html=True,
            )

    with tab_activities:
        activities = {
            "🗣️ تقليد الحركات الفموية": "أمام مرآة: فتح الفم، إخراج اللسان، رفع اللسان، تحريكه يميناً ويساراً. 5 تكرارات لكل حركة.",
            "🎵 أغاني ولغة": "استخدم أغاني الأطفال المعروفة مع التركيز على المفردات الجديدة وتكرارها بشكل ممتع.",
            "📖 قراءة مشتركة": "اقرأ قصة قصيرة مع الطفل، اسأل عن الشخصيات، الحدث، ثم اطلب إعادة السرد.",
            "🎲 تمرين التسمية": "اعرض صوراً لأشياء يومية واطلب تسميتها. ابدأ بالمفردات المعروفة ثم المجهولة.",
            "🗺️ وصف الصور": "قدّم صورة مشهد يومي (ملعب، مطبخ) واطلب وصف ما يراه في جمل.",
            "🔊 تمارين النطق": "تدريب تسلسلي للأصوات: الصوت منفرداً → في مقطع → في كلمة → في جملة.",
        }
        for title, desc in activities.items():
            with st.expander(title):
                st.write(desc)
                if st.button(f"💾 حفظ كملاحظة", key=f"save_{title}"):
                    db["notes"].append({"id": uid("NOTE"), "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "text": f"{title}: {desc}"})
                    save_all_data()
                    st.success("تم الحفظ.")

    with tab_files:
        st.info("📂 تخزين محلي في مجلد clinic_storage/media")
        upload = st.file_uploader("اختر ملفاً", type=["pdf", "docx", "xlsx", "csv", "png", "jpg", "jpeg", "mp4", "mp3"])
        if upload is not None:
            dest = MEDIA_DIR / upload.name
            with dest.open("wb") as f:
                f.write(upload.getbuffer())
            st.success(f"✅ تم حفظ الملف: {upload.name}")

        files = sorted([
            {"الملف": p.name, "الحجم (KB)": round(p.stat().st_size/1024, 1), "تاريخ الرفع": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d")}
            for p in MEDIA_DIR.iterdir() if p.is_file()
        ], key=lambda x: x["تاريخ الرفع"], reverse=True)
        if files:
            st.dataframe(pd.DataFrame(files), use_container_width=True, hide_index=True)
        else:
            st.info("لا توجد ملفات مرفوعة بعد.")

    with tab_notes:
        note_text = st.text_area("ملاحظة سريعة جديدة", height=100)
        note_tag = st.selectbox("التصنيف", ["عام", "سريري", "إداري", "مهم"])
        if st.button("💾 حفظ الملاحظة"):
            if note_text.strip():
                db["notes"].append({
                    "id": uid("NOTE"),
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "text": note_text.strip(),
                    "tag": note_tag,
                })
                save_all_data()
                st.success("تم الحفظ.")

        filter_tag = st.selectbox("تصفية", ["الكل", "عام", "سريري", "إداري", "مهم"])
        notes_to_show = db["notes"] if filter_tag == "الكل" else [n for n in db["notes"] if n.get("tag") == filter_tag]
        tag_colors = {"عام": "#0ea5e9", "سريري": "#7c3aed", "إداري": "#f59e0b", "مهم": "#e11d48"}
        for note in reversed(notes_to_show[-30:]):
            color = tag_colors.get(note.get("tag", "عام"), "#94a3b8")
            st.markdown(
                f'<div style="background:white;border-right:4px solid {color};border-radius:10px;padding:10px 14px;margin-bottom:8px;">'
                f'<small style="color:#94a3b8;">{note["date"]} • {note.get("tag","")}</small><br>'
                f'{note["text"]}</div>',
                unsafe_allow_html=True,
            )


# =========================================================
# 19) التقارير والتصدير
# =========================================================
elif menu == "📄 التقارير والتصدير":
    st.title("📄 التقارير والتصدير")

    t_data, t_patient, t_financial, t_backups = st.tabs(["💾 تصدير البيانات", "👤 تقرير الطفل", "💰 التقرير المالي", "🗄️ النسخ الاحتياطية"])

    with t_data:
        st.subheader("تصدير بيانات الحساب")
        c1, c2 = st.columns(2)
        c1.download_button("⬇️ تصدير JSON", data=export_current_user_data(), file_name=f"clinic_{current_user}_{date.today().isoformat()}.json", mime="application/json", use_container_width=True)
        if db["patients"]:
            c2.download_button("⬇️ تصدير الأطفال CSV", data=pd.DataFrame(db["patients"]).to_csv(index=False).encode("utf-8-sig"), file_name=f"patients_{date.today().isoformat()}.csv", mime="text/csv", use_container_width=True)
        if db["sessions"]:
            c1.download_button("⬇️ تصدير الجلسات CSV", data=pd.DataFrame(db["sessions"]).to_csv(index=False).encode("utf-8-sig"), file_name=f"sessions_{date.today().isoformat()}.csv", mime="text/csv", use_container_width=True)
        if db["finances"]:
            c2.download_button("⬇️ تصدير المالية CSV", data=pd.DataFrame(db["finances"]).to_csv(index=False).encode("utf-8-sig"), file_name=f"finances_{date.today().isoformat()}.csv", mime="text/csv", use_container_width=True)

    with t_patient:
        if not db["patients"]:
            st.info("أضف طفلاً أولاً.")
        else:
            p_id = st.selectbox("اختر طفلاً", [p["id"] for p in db["patients"]], format_func=lambda x: f"{patient_name(x)} — {x}")
            p = patient_by_id(p_id)
            sessions = patient_sessions(p_id)
            evaluations = patient_evaluations(p_id)
            appointments = patient_appointments(p_id)
            plan = patient_plan(p_id)
            currency = s_settings.get("currency", "د.ج")

            # معاينة التقرير
            st.markdown(f"""
            ---
            **تقرير ملف الطفل**
            - **الاسم:** {p.get("name", "")}
            - **رقم الملف:** {p.get("id", "")}
            - **العمر:** {age_label(p.get("dob",""))} | **الجنس:** {p.get("gender","")}
            - **ولي الأمر:** {p.get("parent","") or "—"}
            - **الهاتف:** {p.get("phone","")}
            - **التشخيص:** {p.get("diagnosis","")}
            - **الحالة:** {p.get("status","")}
            - **تاريخ التسجيل:** {p.get("created_at","")}
            ---
            **الإحصائيات:**
            - جلسات: {len(sessions)} | تقييمات: {len(evaluations)} | مواعيد: {len(appointments)}
            ---
            **التاريخ الطبي:** {p.get("history","—") or "—"}

            **الملاحظات:** {p.get("notes","—") or "—"}
            """)

            if plan:
                st.markdown(f"**الخطة العلاجية:** {plan.get('main_goal','—')}")
                achieved_n = sum(1 for g in plan.get("sub_goals",[]) if g.get("achieved"))
                st.markdown(f"**تقدم الأهداف:** {achieved_n}/{len(plan.get('sub_goals',[]))} أهداف منجزة")

            # تصدير CSV
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["حقل", "القيمة"])
            for field, val in [("الاسم", p.get("name","")), ("رقم الملف", p.get("id","")), ("العمر", age_label(p.get("dob",""))), ("التشخيص", p.get("diagnosis","")), ("عدد الجلسات", len(sessions)), ("عدد التقييمات", len(evaluations))]:
                w.writerow([field, val])
            st.download_button("⬇️ تحميل التقرير CSV", data=buf.getvalue().encode("utf-8-sig"), file_name=f"patient_report_{p_id}.csv", mime="text/csv")

    with t_financial:
        if not db["finances"]:
            st.info("لا توجد بيانات مالية.")
        else:
            col1, col2 = st.columns(2)
            year = col1.selectbox("السنة", sorted(set(f.get("date","")[:4] for f in db["finances"] if f.get("date")), reverse=True))
            month_filter = col2.selectbox("الشهر", ["الكل"] + [f"{m:02d}" for m in range(1, 13)])

            filtered = [f for f in db["finances"] if f.get("date","").startswith(year)]
            if month_filter != "الكل":
                filtered = [f for f in filtered if f.get("date","")[5:7] == month_filter]

            currency = s_settings.get("currency","د.ج")
            total_in = sum(float(f.get("amount",0)) for f in filtered if f.get("type") == "مداخيل")
            total_out = sum(float(f.get("amount",0)) for f in filtered if f.get("type") == "مصاريف")

            c1, c2, c3 = st.columns(3)
            c1.metric("المداخيل", f"{total_in:,.0f} {currency}")
            c2.metric("المصاريف", f"{total_out:,.0f} {currency}")
            c3.metric("الصافي", f"{total_in-total_out:,.0f} {currency}")

            if filtered:
                df_fin = pd.DataFrame(filtered)
                df_fin["amount"] = pd.to_numeric(df_fin["amount"], errors="coerce").fillna(0)
                st.download_button(
                    "⬇️ تحميل التقرير المالي",
                    data=df_fin.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"financial_report_{year}_{month_filter}.csv",
                    mime="text/csv",
                )

    with t_backups:
        col1, col2 = st.columns(2)
        if col1.button("💾 إنشاء نسخة احتياطية الآن", use_container_width=True):
            backup = create_backup()
            if backup:
                st.success(f"✅ تم إنشاء: {backup.name}")
            else:
                st.warning("لا توجد بيانات للنسخ الاحتياطي.")

        # استعادة من نسخة
        restore_file = st.file_uploader("استعادة من نسخة احتياطية (JSON)", type=["json"])
        if restore_file and col2.button("🔄 استعادة البيانات"):
            try:
                restored = json.loads(restore_file.read().decode("utf-8"))
                create_backup()  # نسخ احتياطي قبل الاستعادة
                st.session_state["all_data"] = restored
                save_all_data()
                write_audit("RESTORE_BACKUP")
                st.success("✅ تم استعادة البيانات. أعد تحميل الصفحة.")
            except Exception as e:
                st.error(f"فشل في الاستعادة: {e}")

        backup_files = sorted(BACKUP_DIR.glob("*.json"), reverse=True)
        if backup_files:
            st.subheader("النسخ الاحتياطية المتاحة")
            df_back = pd.DataFrame([
                {"الملف": p.name, "الحجم (KB)": round(p.stat().st_size/1024, 1), "التاريخ": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}
                for p in backup_files
            ])
            st.dataframe(df_back, use_container_width=True, hide_index=True)

            selected_b = st.selectbox("تحميل نسخة:", backup_files, format_func=lambda p: p.name)
            st.download_button("⬇️ تحميل النسخة", data=selected_b.read_bytes(), file_name=selected_b.name, mime="application/json")
        else:
            st.info("لا توجد نسخ احتياطية بعد.")


# =========================================================
# 20) الإعدادات والأمان
# =========================================================
elif menu == "⚙️ الإعدادات والأمان":
    st.title("⚙️ الإعدادات والأمان")

    tab_clinic, tab_password, tab_appearance, tab_audit = st.tabs(["🏥 إعدادات العيادة", "🔑 كلمة المرور", "🎨 التخصيص", "🔍 سجل المدقق"])

    with tab_clinic:
        with st.form("clinic_settings_form"):
            c1, c2 = st.columns(2)
            clinic_name = c1.text_input("اسم العيادة", value=s_settings.get("clinic_name", APP_NAME))
            clinic_phone = c2.text_input("هاتف العيادة", value=s_settings.get("clinic_phone", ""))
            clinic_address = st.text_area("العنوان", value=s_settings.get("clinic_address", ""))
            c3, c4 = st.columns(2)
            currency = c3.text_input("العملة", value=s_settings.get("currency", "د.ج"))
            session_price = c4.number_input("سعر الجلسة الافتراضي", min_value=0.0, value=float(s_settings.get("session_price", 2000)), step=100.0)
            c5, c6 = st.columns(2)
            working_hours = c5.text_input("ساعات العمل", value=s_settings.get("working_hours", "8:00 - 17:00"))
            max_apts = c6.number_input("أقصى مواعيد يومية", min_value=1, max_value=30, value=int(s_settings.get("max_daily_appointments", 8)))
            gemini_model = st.text_input("نموذج Gemini", value=s_settings.get("gemini_model", "gemini-2.5-flash"))
            reminder_days_setting = st.number_input(
                "التذكير بالموعد قبل (بالأيام)",
                min_value=0,
                max_value=30,
                value=int(s_settings.get("reminder_days", 1)),
            )

            if st.form_submit_button("💾 حفظ الإعدادات", use_container_width=True):
                s_settings.update({
                    "clinic_name": clinic_name.strip() or APP_NAME,
                    "clinic_phone": clinic_phone.strip(),
                    "clinic_address": clinic_address.strip(),
                    "currency": currency.strip() or "د.ج",
                    "session_price": float(session_price),
                    "working_hours": working_hours.strip(),
                    "max_daily_appointments": int(max_apts),
                    "gemini_model": gemini_model.strip(),
                    "reminder_days": int(reminder_days_setting),
                })
                atomic_write_json(SETTINGS_FILE, s_settings)
                st.success("✅ تم حفظ الإعدادات.")
                write_audit("SETTINGS_UPDATED")

    with tab_password:
        with st.form("change_password_form"):
            old_p = st.text_input("كلمة المرور الحالية", type="password")
            new_p = st.text_input("كلمة المرور الجديدة", type="password")
            confirm_p = st.text_input("تأكيد كلمة المرور", type="password")

            if st.form_submit_button("🔒 تغيير كلمة المرور", use_container_width=True):
                if not verify_password(old_p, user_info.get("password", "")):
                    st.error("كلمة المرور الحالية غير صحيحة.")
                elif len(new_p) < 8:
                    st.error("يجب أن تكون كلمة المرور الجديدة 8 أحرف على الأقل.")
                elif new_p != confirm_p:
                    st.error("تأكيد كلمة المرور غير مطابق.")
                else:
                    user_info["password"] = hash_password(new_p)
                    save_users()
                    write_audit("PASSWORD_CHANGED")
                    st.success("✅ تم تغيير كلمة المرور.")

    with tab_appearance:
        st.info("🎨 خيارات التخصيص البصري")
        st.write("العيادة الحالية:", s_settings.get("clinic_name", APP_NAME))
        st.write("العملة:", s_settings.get("currency", "د.ج"))
        st.write("سعر الجلسة:", f"{s_settings.get('session_price', 2000)} {s_settings.get('currency','د.ج')}")
        st.write("ساعات العمل:", s_settings.get("working_hours", "8:00 - 17:00"))

    with tab_audit:
        st.subheader("🔍 سجل أحداث الأمان")
        today_log = AUDIT_DIR / f"audit_{date.today().isoformat()}.json"
        if today_log.exists():
            logs = safe_load_json(today_log, [])
            if logs:
                log_df = pd.DataFrame(reversed(logs))
                st.dataframe(log_df[["ts", "user", "action", "details"]].rename(columns={
                    "ts": "الوقت", "user": "المستخدم", "action": "الحدث", "details": "التفاصيل"
                }), use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد أحداث اليوم.")
        else:
            st.info("لا توجد سجلات للتدقيق اليوم.")

        log_files = sorted(AUDIT_DIR.glob("audit_*.json"), reverse=True)
        if len(log_files) > 1:
            old_logs = st.selectbox("عرض سجل يوم سابق:", [f.name for f in log_files[1:6]])
            if old_logs:
                old_data = safe_load_json(AUDIT_DIR / old_logs, [])
                if old_data:
                    st.dataframe(pd.DataFrame(reversed(old_data)), use_container_width=True, hide_index=True)


# =========================================================
# 21) إدارة المستخدمين — للمدير فقط
# =========================================================
elif menu == "👑 إدارة المستخدمين" and user_role == "admin":
    st.title("👑 إدارة المستخدمين والصلاحيات")

    t_new, t_list, t_manage = st.tabs(["➕ مستخدم جديد", "📋 قائمة المستخدمين", "🛡️ إدارة الصلاحيات"])

    with t_new:
        with st.form("new_user_form"):
            u1, u2 = st.columns(2)
            new_username = u1.text_input("اسم المستخدم *")
            new_full_name = u2.text_input("الاسم الكامل *")
            new_password = u1.text_input("كلمة المرور *", type="password")
            new_role = u2.selectbox("الصلاحية", ["therapist", "admin", "receptionist"])
            new_phone = u1.text_input("الهاتف")
            new_email = u2.text_input("البريد الإلكتروني")

            if st.form_submit_button("✅ إنشاء الحساب", use_container_width=True):
                key = normalize_username(new_username)
                errors = []
                if not key:
                    errors.append("اسم المستخدم مطلوب.")
                if not new_password:
                    errors.append("كلمة المرور مطلوبة.")
                elif len(new_password) < 8:
                    errors.append("كلمة المرور يجب أن تكون 8 أحرف على الأقل.")
                if key in st.session_state["users_db"]:
                    errors.append("اسم المستخدم موجود مسبقاً.")
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    st.session_state["users_db"][key] = {
                        "password": hash_password(new_password),
                        "role": new_role,
                        "full_name": new_full_name.strip() or key,
                        "phone": new_phone.strip(),
                        "email": new_email.strip(),
                        "created_at": str(date.today()),
                        "created_by": current_user,
                        "active": True,
                    }
                    save_users()
                    write_audit("CREATE_USER", f"username={key} role={new_role}")
                    st.success(f"✅ تم إنشاء حساب {new_full_name}")
                    st.rerun()

    with t_list:
        rows = []
        for uname, u in st.session_state["users_db"].items():
            rows.append({
                "اسم المستخدم": uname,
                "الاسم": u.get("full_name", ""),
                "الصلاحية": u.get("role", ""),
                "الهاتف": u.get("phone", ""),
                "نشط": "✅" if u.get("active", True) else "❌",
                "تاريخ الإنشاء": u.get("created_at", ""),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with t_manage:
        other_users = [u for u in st.session_state["users_db"] if u != current_user]
        if other_users:
            target = st.selectbox("الحساب", other_users, format_func=lambda u: f"{u} ({st.session_state['users_db'][u].get('full_name','')})")
            target_user = st.session_state["users_db"][target]

            st.markdown("### ✏️ تعديل بيانات الحساب")
            with st.form("edit_user_form"):
                e1, e2 = st.columns(2)
                edited_username = e1.text_input("اسم المستخدم (للدخول) *", value=target)
                edited_full_name = e2.text_input("الاسم الظاهر *", value=target_user.get("full_name", ""))
                e3, e4 = st.columns(2)
                edited_phone = e3.text_input("الهاتف", value=target_user.get("phone", ""))
                edited_email = e4.text_input("البريد الإلكتروني", value=target_user.get("email", ""))
                e5, e6 = st.columns(2)
                new_state = e5.selectbox("حالة الحساب", ["نشط", "معطل"], index=0 if target_user.get("active", True) else 1)
                roles = ["therapist", "admin", "receptionist"]
                current_role_index = roles.index(target_user.get("role", "therapist")) if target_user.get("role") in roles else 0
                new_role_target = e6.selectbox("الصلاحية", roles, index=current_role_index)

                if st.form_submit_button("💾 حفظ بيانات الحساب", use_container_width=True):
                    renamed_key = normalize_username(edited_username)
                    errors = []
                    if not renamed_key:
                        errors.append("اسم المستخدم مطلوب.")
                    elif renamed_key != target and renamed_key in st.session_state["users_db"]:
                        errors.append("اسم المستخدم الجديد مستخدم مسبقاً.")
                    if not edited_full_name.strip():
                        errors.append("الاسم الظاهر مطلوب.")
                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        target_user.update({
                            "full_name": edited_full_name.strip(),
                            "phone": edited_phone.strip(),
                            "email": edited_email.strip(),
                            "active": new_state == "نشط",
                            "role": new_role_target,
                            "updated_at": str(date.today()),
                        })
                        if renamed_key != target:
                            st.session_state["users_db"][renamed_key] = st.session_state["users_db"].pop(target)
                            if target in st.session_state["all_data"]:
                                st.session_state["all_data"][renamed_key] = st.session_state["all_data"].pop(target)
                            write_audit("RENAME_USER", f"from={target} to={renamed_key}")
                            save_all_data()
                        save_users()
                        write_audit("UPDATE_USER", f"target={renamed_key} active={new_state} role={new_role_target}")
                        st.success("✅ تم تحديث الحساب وحفظ بياناته.")
                        st.rerun()

            st.markdown("### 🔑 إعادة تعيين كلمة المرور")
            with st.form("reset_user_password_form"):
                new_pwd_reset = st.text_input("كلمة المرور الجديدة", type="password")
                confirm_pwd_reset = st.text_input("تأكيد كلمة المرور الجديدة", type="password")
                if st.form_submit_button("🔑 إعادة تعيين كلمة المرور"):
                    if len(new_pwd_reset) < 8:
                        st.error("كلمة المرور يجب أن تكون 8 أحرف على الأقل.")
                    elif new_pwd_reset != confirm_pwd_reset:
                        st.error("تأكيد كلمة المرور غير مطابق.")
                    else:
                        target_user["password"] = hash_password(new_pwd_reset)
                        save_users()
                        write_audit("RESET_PASSWORD", f"target={target}")
                        st.success("✅ تم إعادة تعيين كلمة المرور.")

            st.markdown("### 🗑️ حذف الحساب")
            st.markdown(
                '<div class="danger-box">سيؤدي حذف الحساب إلى إزالة بيانات دخوله وبيانات العيادة المرتبطة به نهائياً، ولا يمكن التراجع عنه.</div>',
                unsafe_allow_html=True,
            )
            confirm_user_delete = st.checkbox("أفهم أن حذف الحساب وبياناته نهائي", key=f"confirm_user_delete_{target}")
            if st.button("🗑️ حذف الحساب نهائياً", type="secondary"):
                admin_count = sum(1 for item in st.session_state["users_db"].values() if item.get("role") == "admin")
                if not confirm_user_delete:
                    st.error("فعّل التأكيد قبل حذف الحساب.")
                elif target_user.get("role") == "admin" and admin_count <= 1:
                    st.error("لا يمكن حذف آخر حساب مدير في النظام.")
                else:
                    write_audit("DELETE_USER", f"target={target}")
                    del st.session_state["users_db"][target]
                    st.session_state["all_data"].pop(target, None)
                    save_users()
                    save_all_data()
                    st.success("✅ تم حذف الحساب وبياناته.")
                    st.rerun()
        else:
            st.info("لا توجد حسابات أخرى.")


# =========================================================
# 22) حماية من الوصول غير المصرح
# =========================================================
else:
    if menu not in ["📊 لوحة القيادة"]:
        st.error("هذه الصفحة غير متاحة لصلاحيتك الحالية.")


# =========================================================
# ذيل الصفحة
# =========================================================
st.sidebar.write("---")
st.sidebar.caption(f"⚠️ احتفظ بنسخة احتياطية خارجية بشكل دوري.")
