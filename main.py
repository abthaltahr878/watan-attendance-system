import sys
import sqlite3
import shutil
import os
from datetime import datetime
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFrame, QGridLayout, 
                             QStatusBar, QMessageBox, QDialog, QGraphicsOpacityEffect, QApplication)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QIcon, QFont
from styles import STYLE_SHEET

# --- السطر المضاف للاستيراد ---
from database import init_clean_db 

# استيراد النوافذ الأخرى
from employees import EmployeesWindow
from attendance import AttendanceWindow
from reports import ReportsWindow
from settings import SettingsWindow
from login import LoginWindow

# 1. دالة تحديد مسار الملفات الداخلية (أيقونات، صور)
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# 2. دالة تحديد مسار قاعدة البيانات الخارجية (بجانب الـ EXE دائماً)
def get_db_path():
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(os.path.dirname(sys.executable), "attendance.db")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "attendance.db")

# --- الدالة الجديدة لمعالجة الفترات المرنة والدوام الليلي ---
def is_time_between(target, start, end):
    """دالة ذكية لمعرفة هل الوقت بين فترتين حتى لو عبر منتصف الليل"""
    if start <= end:
        return start <= target <= end
    else: # في حال كان الدوام ليلي (مثلاً من 20:00 إلى 01:00)
        return target >= start or target <= end

def check_attendance_period(check_time_str, settings):
    """
    تحديد هل البصمة تابعة للفترة الأولى أم الثانية بناءً على الإعدادات
    """
    try:
        fmt = "%H:%M"
        check_time = datetime.strptime(check_time_str, fmt).time()
        
        in1 = datetime.strptime(settings['in_limit_1'], fmt).time()
        out1 = datetime.strptime(settings['out_limit_1'], fmt).time()
        in2 = datetime.strptime(settings['in_limit_2'], fmt).time()
        out2 = datetime.strptime(settings['out_limit_2'], fmt).time()

        if is_time_between(check_time, in1, out1):
            return "الفترة الأولى"
        if is_time_between(check_time, in2, out2):
            return "الفترة الثانية"
            
        return "خارج الفترات"
    except:
        return "خطأ في التنسيق"

class ModernMain(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("نظام البصمة الذكية - مؤسسة وطن")
        self.resize(1150, 800)
        
        icon_file = resource_path("icon.ico")
        if os.path.exists(icon_file):
            self.setWindowIcon(QIcon(icon_file))
            
        self.setStyleSheet(STYLE_SHEET)
        self.setStatusBar(QStatusBar(self))
        
        central = QWidget()
        self.setCentralWidget(central)
        
        # --- العلامة المائية ---
        self.watermark = QLabel(central)
        logo_file = resource_path("logo.jpg") 
        if os.path.exists(logo_file):
            pixmap = QPixmap(logo_file)
            self.watermark.setPixmap(pixmap.scaled(700, 700, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        self.watermark.setAlignment(Qt.AlignCenter)
        
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.10) 
        self.watermark.setGraphicsEffect(opacity_effect)
        self.watermark.setGeometry(0, 0, 1150, 800)
        self.watermark.setAttribute(Qt.WA_TransparentForMouseEvents) 
        self.watermark.lower() 

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # 1. الترويسة (Header)
        header = QHBoxLayout()
        self.lbl_logo = QLabel()
        if os.path.exists(logo_file):
            self.lbl_logo.setPixmap(QPixmap(logo_file).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        header.addWidget(self.lbl_logo)
        
        title_container = QVBoxLayout()
        self.lbl_welcome = QLabel()
        self.lbl_welcome.setStyleSheet("color: #636e72; font-size: 16px; font-weight: bold;")
        title_container.addWidget(self.lbl_welcome)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time_display)
        self.timer.start(1000)
        self.update_time_display()

        lbl_inst = QLabel("🏢 مؤسسة وطن التنموية")
        lbl_inst.setStyleSheet("color: #2d3436; font-size: 30px; font-weight: bold;")
        title_container.addWidget(lbl_inst)
        header.addLayout(title_container)
        header.addStretch()
        
        # أزرار التحكم في الترويسة
        header_buttons = QHBoxLayout()
        
        self.btn_about = QPushButton("ℹ️ حول النظام")
        self.btn_about.setFixedSize(140, 45)
        self.btn_about.clicked.connect(self.show_about_dialog)
        
        self.btn_bak = QPushButton("💾 نسخة احتياطية")
        self.btn_bak.setFixedSize(140, 45)
        self.btn_bak.clicked.connect(self.backup_db)
        
        self.btn_sync = QPushButton("🔄 تحديث")
        self.btn_sync.setFixedSize(100, 45)
        self.btn_sync.clicked.connect(self.update_stats)
        
        header_buttons.addWidget(self.btn_about)
        header_buttons.addWidget(self.btn_bak)
        header_buttons.addWidget(self.btn_sync)
        header.addLayout(header_buttons)
        
        main_layout.addLayout(header)

        # 2. بطاقات الإحصائيات
        stats_layout = QHBoxLayout()
        self.card_total = self.create_stat_card("إجمالي الموظفين", "0", "#0984e3")
        self.card_today = self.create_stat_card("حاضرون اليوم", "0", "#00b894")
        self.card_month = self.create_stat_card("سجلات النظام", "0", "#6c5ce7")
        stats_layout.addWidget(self.card_total)
        stats_layout.addWidget(self.card_today)
        stats_layout.addWidget(self.card_month)
        main_layout.addLayout(stats_layout)

        main_layout.addSpacing(20)

        # 3. شبكة الأزرار
        grid = QGridLayout()
        grid.setSpacing(25)
        menu_items = [
            ("👥 إدارة الموظفين", "إضافة وتعديل بيانات الموظفين", self.open_emp),
            ("📡 سحب البصمات", "الاتصال بالجهاز وجلب السجلات", self.open_att),
            ("📊 التقارير الذكية", "استخراج تقارير Excel و PDF", self.open_rep),
            ("⚙ إعدادات النظام", "ضبط IP الجهاز وكلمات المرور", self.open_set)
        ]
        for i, (title, desc, func) in enumerate(menu_items):
            btn = self.create_menu_button(title, desc, func)
            grid.addWidget(btn, i // 2, i % 2)

        main_layout.addLayout(grid)
        main_layout.addStretch()
        
        QTimer.singleShot(1000, self.update_stats)

    def show_about_dialog(self):
        today = datetime.now().strftime('%Y-%m-%d')
        msg = QMessageBox(self)
        msg.setWindowTitle("حول النظام")
        msg.setIcon(QMessageBox.Information)
        msg.setText(f"<b>نظام البصمة - مؤسسة وطن</b><br><br>"
                    f"تم تطوير هذا النظام خصيصاً لمؤسسة وطن بواسطة المهندسات:<br>"
                    f"✨ <b>ابتهال بركات </b><br>"
                    f"✨ <b>براءة النهمي</b><br>"
                    f"✨ <b>هناء سعيد</b><br><br>"
                    f"تاريخ الإصدار: {today}<br>"
                    f"جميع الحقوق محفوظة © 2026")
        msg.exec_()

    def resizeEvent(self, event):
        self.watermark.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def update_time_display(self):
        now = datetime.now()
        self.lbl_welcome.setText(f"📅 {now.strftime('%Y-%m-%d | %I:%M:%S %p')}")

    def create_stat_card(self, title, value, color):
        card = QFrame()
        card.setFixedHeight(120)
        card.setStyleSheet(f"background-color: white; border-radius: 15px; border-right: 8px solid {color};")
        l = QVBoxLayout(card)
        t = QLabel(title)
        t.setStyleSheet("color: #636e72; font-size: 15px; font-weight: bold; background: transparent;")
        v = QLabel(value)
        v.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: bold; background: transparent;")
        l.addWidget(t)
        l.addWidget(v)
        card.val_lbl = v
        return card

    def create_menu_button(self, title, desc, func):
        btn = QPushButton()
        btn.setObjectName("MenuCard") 
        btn.setFixedSize(480, 140)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(func)
        layout = QVBoxLayout(btn)
        t = QLabel(title)
        t.setStyleSheet("font-size: 22px; font-weight: bold; color: #2d3436; background: transparent; border:none;")
        d = QLabel(desc)
        d.setStyleSheet("font-size: 14px; color: #636e72; background: transparent; border:none;")
        layout.addWidget(t)
        layout.addWidget(d)
        layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return btn

    def update_stats(self):
        try:
            db_path = get_db_path() 
            if not os.path.exists(db_path): return
            
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM employees")
            self.card_total.val_lbl.setText(str(cur.fetchone()[0]))
            
            today = datetime.now().strftime('%Y-%m-%d')
            cur.execute("SELECT COUNT(DISTINCT employee_id) FROM attendance WHERE date=?", (today,))
            self.card_today.val_lbl.setText(str(cur.fetchone()[0]))
            
            cur.execute("SELECT COUNT(*) FROM attendance")
            self.card_month.val_lbl.setText(str(cur.fetchone()[0]))
            conn.close()
        except: pass

    def backup_db(self):
        try:
            if not os.path.exists("backups"): os.makedirs("backups")
            dest = f"backups/backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db"
            shutil.copy2(get_db_path(), dest)
            QMessageBox.information(self, "مؤسسة وطن", f"تم حفظ نسخة احتياطية في:\n{dest}")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"فشل النسخ الاحتياطي: {str(e)}")

    def open_emp(self): 
        self.w = EmployeesWindow()
        self.w.show()
        
    def open_att(self): 
        self.w = AttendanceWindow()
        self.w.show()
        
    def open_rep(self): 
        self.w = ReportsWindow()
        if hasattr(self.w, 'load_employees'): 
            self.w.load_employees()
        self.w.show()
        
    def open_set(self): 
        self.w = SettingsWindow()
        self.w.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # التأكد من وجود مجلد النسخ الاحتياطي لكي لا يفشل الزر عند استدعائه
    if not os.path.exists("backups"):
        try:
            os.makedirs("backups")
        except:
            pass

    # 1. تهيئة قاعدة البيانات (إنشاء الملف والجداول إذا كانت محذوفة)
    try:
        init_clean_db()
    except Exception as e:
        # إظهار رسالة خطأ واضحة للمستخدم بدلاً من Print
        QMessageBox.critical(None, "خطأ في قاعدة البيانات", f"فشل تشغيل ملف البيانات:\n{str(e)}")

    # 2. تشغيل شاشة تسجيل الدخول
    login = LoginWindow()
    if login.exec_() == QDialog.Accepted:
        # إذا كانت كلمة المرور صحيحة، يفتح النظام الأساسي
        m = ModernMain()
        m.show()
        m.update_stats() # تحديث الأرقام فور فتح الواجهة
        sys.exit(app.exec_())