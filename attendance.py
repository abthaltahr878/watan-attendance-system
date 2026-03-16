import sqlite3
import os
import sys
import json
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import *
from zk import ZK 

def get_db_path():
    """تحديد مسار قاعدة البيانات بدقة لتعمل في EXE"""
    if hasattr(sys, '_MEIPASS'):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    db_path = os.path.join(base_dir, "attendance.db")
    return os.path.normpath(db_path)

def connect_db():
    """فتح اتصال مع القاعدة مع التأكد من وجود الجداول"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

class AttendanceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مزامنة البصمات - مؤسسة وطن التنموية")
        self.resize(1200, 800)
        self.setLayoutDirection(Qt.RightToLeft)
        
        # 1. تحميل الإعدادات أولاً
        self.config = self.load_settings_from_db()
        
        # 2. بناء الواجهة
        self.init_ui()
        
        # 3. محاولة عرض البيانات المخزنة مسبقاً
        self.load_data()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget { background-color: #f4f7f6; font-family: 'Segoe UI', Arial; }
            QFrame#Header { background-color: white; border-radius: 12px; padding: 15px; border: 1px solid #dcdde1; }
            QPushButton { border-radius: 8px; font-weight: bold; font-size: 13px; padding: 10px 15px; color: white; min-width: 100px; }
            QPushButton#SyncBtn { background-color: #27ae60; }
            QPushButton#SyncBtn:hover { background-color: #2ecc71; }
            QPushButton#RefreshBtn { background-color: #3498db; }
            QPushButton#ClearBtn { background-color: #c0392b; }
            QPushButton#BackBtn { background-color: #7f8c8d; }
            QTableWidget { background-color: white; border-radius: 10px; border: 1px solid #dcdde1; gridline-color: #f1f2f6; }
            QHeaderView::section { background-color: #2c3e50; color: white; font-weight: bold; padding: 10px; border: none; }
            
            QMessageBox { background-color: #ffffff; }
            QMessageBox QPushButton { background-color: #34495e; color: white; min-width: 90px; padding: 8px; border-radius: 5px; }
        """)
        
        main_layout = QVBoxLayout(self)
        header = QFrame(); header.setObjectName("Header")
        h_lay = QHBoxLayout(header)
        
        self.btn_back = QPushButton("🔙 العودة"); self.btn_back.setObjectName("BackBtn")
        self.btn_back.clicked.connect(self.close)
        
        self.status_lbl = QLabel("حالة الجهاز: مستعد للربط")
        self.status_lbl.setStyleSheet("font-size: 16px; color: #2c3e50; font-weight: bold;")
        
        # زر التحديث - تم ربطه بدالة التحديث المباشر
        self.btn_refresh = QPushButton("🔄 تحديث العرض"); self.btn_refresh.setObjectName("RefreshBtn")
        self.btn_refresh.clicked.connect(self.refresh_view) 
        
        self.btn_sync = QPushButton("📥 سحب البصمات"); self.btn_sync.setObjectName("SyncBtn")
        self.btn_sync.clicked.connect(self.sync_from_device)

        self.btn_clear = QPushButton("🧹 مسح الجهاز"); self.btn_clear.setObjectName("ClearBtn")
        self.btn_clear.clicked.connect(self.clear_device_logs)
        
        h_lay.addWidget(self.btn_back); h_lay.addStretch(); h_lay.addWidget(self.status_lbl); h_lay.addStretch()
        h_lay.addWidget(self.btn_refresh); h_lay.addWidget(self.btn_sync); h_lay.addWidget(self.btn_clear) 
        main_layout.addWidget(header)

        self.table = QTableWidget(); self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID البصمة", "اسم الموظف", "التاريخ", "دخول ف1", "خروج ف1", "دخول ف2", "خروج ف2"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        main_layout.addWidget(self.table)

    def load_settings_from_db(self):
        """تحميل الإعدادات من ملف JSON"""
        if hasattr(sys, '_MEIPASS'): base_path = os.path.dirname(sys.executable)
        else: base_path = os.path.dirname(os.path.abspath(__file__))
        settings_file = os.path.join(base_path, "settings_data.json")
        conf = {"ip": "192.168.1.205", "in_limit_1": "06:00", "out_limit_1": "13:59", "in_limit_2": "14:00", "out_limit_2": "23:59"}
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r", encoding='utf-8') as f:
                    data = json.load(f)
                    conf.update(data)
            except: pass
        return conf

    def refresh_view(self):
        """تحديث الإعدادات وإعادة تحميل الجدول"""
        self.config = self.load_settings_from_db()
        self.load_data()
        self.status_lbl.setText("✅ تم تحديث العرض")
        self.status_lbl.setStyleSheet("color: #3498db; font-weight: bold;")

    def load_data(self):
        """قراءة البيانات وعرضها في الجدول المكون من 7 أعمدة"""
        try:
            db = connect_db()
            cursor = db.cursor()
            # التأكد من جلب الفترتين (check_in, check_out, check_in_2, check_out_2)
            query = """
                SELECT a.employee_id, COALESCE(e.name, 'موظف غير معرف'), a.date, 
                       a.check_in, a.check_out, a.check_in_2, a.check_out_2 
                FROM attendance a 
                LEFT JOIN employees e ON a.employee_id = e.finger_id 
                ORDER BY a.date DESC LIMIT 1000
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            
            self.table.setRowCount(0) 
            for i, row in enumerate(rows):
                self.table.insertRow(i)
                for j in range(7):
                    val = str(row[j]) if row[j] not in [None, "", "--"] else "--"
                    item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter)
                    # تلوين الخانات الفارغة بلون رمادي خفيف
                    if val == "--": item.setForeground(QColor("#95a5a6"))
                    self.table.setItem(i, j, item)
            db.close()
        except Exception as e:
            print(f"Error loading data: {e}")

    def is_time_between(self, target_str, start_str, end_str):
        fmt = '%H:%M'
        try:
            target = datetime.strptime(target_str, fmt).time()
            start = datetime.strptime(start_str, fmt).time()
            end = datetime.strptime(end_str, fmt).time()
            if start <= end: return start <= target <= end
            return target >= start or target <= end
        except: return False

    def sync_from_device(self):
        """سحب البيانات من الجهاز وتخزينها"""
        self.config = self.load_settings_from_db()
        zk = ZK(self.config['ip'], port=4370, timeout=10)
        conn = None
        try:
            self.status_lbl.setText("⏳ جاري محاولة الإتصال بالجهاز...")
            self.status_lbl.setStyleSheet("color: #e67e22; font-weight: bold;")
            QApplication.processEvents()

            conn = zk.connect()
            conn.disable_device()
            records = conn.get_attendance()

            db = connect_db()
            cursor = db.cursor()

            for record in records:
                u_id = str(record.user_id)
                d_str = record.timestamp.strftime('%Y-%m-%d')
                t_str = record.timestamp.strftime('%H:%M')

                # 1. فحص: هل البصمة للفترة الأولى أو الثانية؟
                is_p1 = self.is_time_between(t_str, self.config['in_limit_1'], self.config['out_limit_1'])
                is_p2 = self.is_time_between(t_str, self.config['in_limit_2'], self.config['out_limit_2'])

                # لو خارج الفترتين نتجاهلها
                if not is_p1 and not is_p2:
                    continue

                cursor.execute(
                    "SELECT id, check_in, check_out, check_in_2, check_out_2 "
                    "FROM attendance WHERE employee_id=? AND date=?",
                    (u_id, d_str)
                )
                existing = cursor.fetchone()

                if not existing:
                    # سجل جديد لليوم
                    if is_p1:
                        cursor.execute("""
                            INSERT INTO attendance (employee_id, date, check_in, check_out, check_in_2, check_out_2)
                            VALUES (?, ?, ?, '--', '--', '--')
                        """, (u_id, d_str, t_str))
                    elif is_p2:
                        cursor.execute("""
                            INSERT INTO attendance (employee_id, date, check_in, check_out, check_in_2, check_out_2)
                            VALUES (?, ?, '--', '--', ?, '--')
                        """, (u_id, d_str, t_str))
                else:
                    rec_id, c1_in, c1_out, c2_in, c2_out = existing

                    # توحيد القيم الفارغة إلى "--"
                    c1_in = c1_in or '--'
                    c1_out = c1_out or '--'
                    c2_in = c2_in or '--'
                    c2_out = c2_out or '--'

                    # الفترة الأولى
                    if is_p1:
                        if c1_in == '--':
                            # أول بصمة للفترة الأولى = دخول
                            cursor.execute(
                                "UPDATE attendance SET check_in=? WHERE id=?",
                                (t_str, rec_id)
                            )
                        elif c1_out == '--':
                            # ثاني بصمة = خروج (مع معالجة لو طلعت أبكر)
                            if t_str < c1_in:
                                new_in = t_str
                                new_out = c1_in
                                cursor.execute(
                                    "UPDATE attendance SET check_in=?, check_out=? WHERE id=?",
                                    (new_in, new_out, rec_id)
                                )
                            else:
                                cursor.execute(
                                    "UPDATE attendance SET check_out=? WHERE id=?",
                                    (t_str, rec_id)
                                )
                        else:
                            # عندك دخول وخروج، بصمة جديدة ممكن تحدّث الخروج لو أحدث
                            if t_str > c1_out:
                                cursor.execute(
                                    "UPDATE attendance SET check_out=? WHERE id=?",
                                    (t_str, rec_id)
                                )

                    # الفترة الثانية
                    if is_p2:
                        if c2_in == '--':
                            cursor.execute(
                                "UPDATE attendance SET check_in_2=? WHERE id=?",
                                (t_str, rec_id)
                            )
                        elif c2_out == '--':
                            if t_str < c2_in:
                                new_in2 = t_str
                                new_out2 = c2_in
                                cursor.execute(
                                    "UPDATE attendance SET check_in_2=?, check_out_2=? WHERE id=?",
                                    (new_in2, new_out2, rec_id)
                                )
                            else:
                                cursor.execute(
                                    "UPDATE attendance SET check_out_2=? WHERE id=?",
                                    (t_str, rec_id)
                                )
                        else:
                            if t_str > c2_out:
                                cursor.execute(
                                    "UPDATE attendance SET check_out_2=? WHERE id=?",
                                    (t_str, rec_id)
                                )

            db.commit()
            db.close()
            self.status_lbl.setText("✅ تم التحديث بنجاح")
            self.status_lbl.setStyleSheet("color: #27ae60; font-weight: bold;")
            QMessageBox.information(self, "نجاح", f"تم سحب {len(records)} بصمة بنجاح.")
            self.load_data()

        except Exception as e:
            self.status_lbl.setText("❌ فشل الإتصال بالجهاز")
            self.status_lbl.setStyleSheet("color: #c0392b; font-weight: bold;")
            QMessageBox.critical(
                self,
                "خطأ في الإتصال",
                f"لا يمكن الوصول للجهاز IP: {self.config['ip']}\n{str(e)}"
            )
        finally:
            if conn:
                conn.enable_device()
                conn.disconnect()


    def clear_device_logs(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("تأكيد الحذف")
        msg_box.setText("هل أنت متأكد من مسح السجلات؟")
        msg_box.setIcon(QMessageBox.Warning)
        yes = msg_box.addButton("نعم، امسح", QMessageBox.YesRole)
        no = msg_box.addButton("إلغاء", QMessageBox.NoRole)
        msg_box.exec_()
        if msg_box.clickedButton() == yes:
            try:
                zk = ZK(self.config['ip'], port=4370, timeout=10)
                conn = zk.connect()
                conn.clear_attendance()
                QMessageBox.information(self, "تم", "تم مسح سجلات الجهاز.")
                conn.disconnect()
            except Exception as e: QMessageBox.critical(self, "خطأ", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # ملاحظة: تأكد من أن ملف attendance.db موجود بجانب السكريبت
    window = AttendanceWindow()
    window.show()
    sys.exit(app.exec_())