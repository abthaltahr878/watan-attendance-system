import sqlite3
import os
import sys

def get_db_path():
    """تحديد مسار ثابت ودائم لقاعدة البيانات بجانب ملف التشغيل EXE"""
    if hasattr(sys, '_MEIPASS'):
        # إذا كان البرنامج محزماً، يتم وضع القاعدة بجانب ملف الـ EXE الأصلي وليس المجلد المؤقت
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    db_path = os.path.join(base_dir, "attendance.db")
    return os.path.normpath(db_path)

def connect_db():
    """إنشاء اتصال آمن مع تفعيل القيود وتحسين الأداء"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    # تفعيل القيود لضمان صحة العلاقات بين الجداول
    conn.execute("PRAGMA foreign_keys = ON;")
    # تفعيل وضع WAL لسرعة الاستجابة ومنع التهنيج
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_clean_db():
    """إنشاء الجداول وضمان هيكلية صحيحة 100%"""
    try:
        conn = connect_db()
        cursor = conn.cursor()

        # 1. جدول الموظفين
        # ملاحظة: finger_id هو الرقم الذي سنسجل به الحضور
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            finger_id INTEGER UNIQUE NOT NULL,
            active INTEGER DEFAULT 1
        )""")

        # 2. جدول الحضور
        # الربط مع finger_id لضمان مرونة البيانات
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            check_in TEXT DEFAULT '--',
            check_out TEXT DEFAULT '--',
            check_in_2 TEXT DEFAULT '--',
            check_out_2 TEXT DEFAULT '--',
            UNIQUE(employee_id, date),
            FOREIGN KEY(employee_id) REFERENCES employees(finger_id) ON DELETE CASCADE
        )""")

        # 3. جدول الإجازات الرسمية
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS holidays (
            holiday_date TEXT UNIQUE NOT NULL
        )""")

        # 4. جدول الإعدادات
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")

        conn.commit()
        conn.close()
        print(f"✅ تم تأمين قاعدة البيانات بنجاح في: {get_db_path()}")
        return True
    except Exception as e:
        print(f"❌ خطأ فني في القاعدة: {str(e)}")
        return False

# --- وظائف مساعدة للتعامل مع الإعدادات الجديدة ---

def set_setting(key, value):
    """حفظ إعداد معين في قاعدة البيانات"""
    try:
        conn = connect_db()
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        conn.close()
    except: pass

def get_setting(key, default=None):
    """جلب إعداد معين من قاعدة البيانات"""
    try:
        conn = connect_db()
        res = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        conn.close()
        return res[0] if res else default
    except:
        return default

if __name__ == "__main__":
    init_clean_db()