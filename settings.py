import json
import os
import sys  # تم إضافة الاستيراد لضمان الوصول لمسار الـ EXE
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTime
from styles import STYLE_SHEET

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("إعدادات نظام وطن - إدارة الفترات")
        self.resize(500, 700) 
        self.setStyleSheet(STYLE_SHEET)
        self.setLayoutDirection(Qt.RightToLeft)
        
        # --- التعديل البرمجي لضمان الحفظ الدائم بعد التحزيم ---
        if hasattr(sys, '_MEIPASS'):
            # إذا كان البرنامج يعمل كملف EXE محزم
            base_path = os.path.dirname(sys.executable)
        else:
            # إذا كان يعمل ككود بايثون عادي أثناء التطوير
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        self.settings_file = os.path.join(base_path, "settings_data.json")
        # ---------------------------------------------------
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # --- قسم إعدادات جهاز البصمة ---
        connection_group = QGroupBox("📡 إعدادات الاتصال بالجهاز")
        conn_layout = QFormLayout()
        
        self.ip = QLineEdit()
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        
        conn_layout.addRow("عنوان الـ IP:", self.ip)
        conn_layout.addRow("اسم المستخدم:", self.username)
        conn_layout.addRow("كلمة المرور:", self.password)
        connection_group.setLayout(conn_layout)
        layout.addWidget(connection_group)

        # --- إعدادات الفترة الأولى ---
        time_group1 = QGroupBox("🕒 إعدادات الفترة الأولى")
        time_layout1 = QGridLayout()
        self.in_limit_1 = QTimeEdit()
        self.out_limit_1 = QTimeEdit()
        self.in_limit_1.setDisplayFormat("HH:mm")
        self.out_limit_1.setDisplayFormat("HH:mm")
        
        time_layout1.addWidget(QLabel("بداية الحضور:"), 0, 0)
        time_layout1.addWidget(self.in_limit_1, 0, 1)
        time_layout1.addWidget(QLabel("نهاية الانصراف:"), 1, 0)
        time_layout1.addWidget(self.out_limit_1, 1, 1)
        time_group1.setLayout(time_layout1)
        layout.addWidget(time_group1)

        # --- إعدادات الفترة الثانية ---
        time_group2 = QGroupBox("🌙 إعدادات الفترة الثانية")
        time_layout2 = QGridLayout()
        self.in_limit_2 = QTimeEdit()
        self.out_limit_2 = QTimeEdit()
        self.in_limit_2.setDisplayFormat("HH:mm")
        self.out_limit_2.setDisplayFormat("HH:mm")
        
        time_layout2.addWidget(QLabel("بداية الحضور:"), 0, 0)
        time_layout2.addWidget(self.in_limit_2, 0, 1)
        time_layout2.addWidget(QLabel("نهاية الانصراف:"), 1, 0)
        time_layout2.addWidget(self.out_limit_2, 1, 1)
        time_group2.setLayout(time_layout2)
        layout.addWidget(time_group2)

        # --- أزرار التحكم ---
        self.load_settings()

        btn_save = QPushButton("💾 حفظ كافة الإعدادات")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.setFixedHeight(50) 
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self.save_settings)
        layout.addWidget(btn_save)
        
        btn_back = QPushButton("⬅ العودة للرئيسية")
        btn_back.clicked.connect(self.close)
        layout.addWidget(btn_back)

    def load_settings(self):
        """تحميل الإعدادات مع معالجة الأخطاء"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding='utf-8') as f:
                    data = json.load(f)
                    self.ip.setText(str(data.get("ip", "192.168.1.205")))
                    self.username.setText(str(data.get("username", "123")))
                    self.password.setText(str(data.get("password", "123")))
                    
                    self.in_limit_1.setTime(QTime.fromString(data.get("in_limit_1", "09:00"), "HH:mm"))
                    self.out_limit_1.setTime(QTime.fromString(data.get("out_limit_1", "14:00"), "HH:mm"))
                    self.in_limit_2.setTime(QTime.fromString(data.get("in_limit_2", "20:00"), "HH:mm"))
                    self.out_limit_2.setTime(QTime.fromString(data.get("out_limit_2", "01:00"), "HH:mm"))
            else:
                self.set_defaults()
        except Exception:
            self.set_defaults()

    def set_defaults(self):
        """القيم المطلوبة 123 كافتراضي"""
        self.ip.setText("192.168.1.205")
        self.username.setText("123")
        self.password.setText("123")
        self.in_limit_1.setTime(QTime(9, 0))
        self.out_limit_1.setTime(QTime(14, 0))
        self.in_limit_2.setTime(QTime(20, 0))
        self.out_limit_2.setTime(QTime(1, 0))

    def save_settings(self):
        """حفظ البيانات بشكل نهائي وآمن بجانب ملف EXE"""
        save_data = {
            "ip": self.ip.text().strip(),
            "username": self.username.text().strip(),
            "password": self.password.text().strip(),
            "in_limit_1": self.in_limit_1.time().toString("HH:mm"),
            "out_limit_1": self.out_limit_1.time().toString("HH:mm"),
            "in_limit_2": self.in_limit_2.time().toString("HH:mm"),
            "out_limit_2": self.out_limit_2.time().toString("HH:mm")
        }
        
        try:
            with open(self.settings_file, "w", encoding='utf-8') as f:
                json.dump(save_data, f, indent=4, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
                
            QMessageBox.information(self, "نجاح", "تم الحفظ بنجاح! سيتم استخدام البيانات الجديدة عند الاتصال.")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل الحفظ، تأكد من تشغيل البرنامج كمسؤول (Run as Admin): {str(e)}")

    @staticmethod
    def is_time_between(target, start, end):
        """الدالة المساعدة لمطابقة الوقت"""
        if start <= end:
            return start <= target <= end
        else:
            return target >= start or target <= end