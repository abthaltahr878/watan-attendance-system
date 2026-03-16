import sqlite3
import json
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def get_db_path():
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(os.path.dirname(sys.executable), "attendance.db")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "attendance.db")

class HolidayManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إدارة الإجازات الرسمية")
        self.setFixedSize(400, 500)
        self.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(self)
        self.calendar = QCalendarWidget()
        layout.addWidget(QLabel("اختر تاريخ الإجازة:"))
        layout.addWidget(self.calendar)
        btn_add = QPushButton("إضافة كإجازة رسمية")
        btn_add.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px;")
        btn_add.clicked.connect(self.add_holiday)
        layout.addWidget(btn_add)
        self.list_holidays = QListWidget()
        layout.addWidget(QLabel("الإجازات المسجلة:"))
        layout.addWidget(self.list_holidays)
        btn_del = QPushButton("حذف الإجازة المختارة")
        btn_del.setStyleSheet("background-color: #c0392b; color: white; padding: 5px;")
        btn_del.clicked.connect(self.delete_holiday)
        layout.addWidget(btn_del)
        self.init_db()
        self.refresh_list()

    def init_db(self):
        try:
            conn = sqlite3.connect(get_db_path())
            conn.execute("CREATE TABLE IF NOT EXISTS holidays (holiday_date DATE UNIQUE)")
            conn.commit()
            conn.close()
        except: pass

    def add_holiday(self):
        date_str = self.calendar.selectedDate().toPyDate().isoformat()
        try:
            conn = sqlite3.connect(get_db_path())
            conn.execute("INSERT INTO holidays (holiday_date) VALUES (?)", (date_str,))
            conn.commit()
            conn.close()
            self.refresh_list()
        except: QMessageBox.warning(self, "تنبيه", "هذا التاريخ مضاف مسبقاً")

    def refresh_list(self):
        self.list_holidays.clear()
        try:
            conn = sqlite3.connect(get_db_path())
            rows = conn.execute("SELECT holiday_date FROM holidays ORDER BY holiday_date DESC").fetchall()
            for r in rows: self.list_holidays.addItem(r[0])
            conn.close()
        except: pass

    def delete_holiday(self):
        item = self.list_holidays.currentItem()
        if item:
            conn = sqlite3.connect(get_db_path())
            conn.execute("DELETE FROM holidays WHERE holiday_date=?", (item.text(),))
            conn.commit()
            conn.close()
            self.refresh_list()

class ReportsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مؤسسة وطن - نظام التقارير والرقابة")
        self.resize(1240, 850)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet("""
            QWidget { background-color: #f8f9fa; font-family: 'Segoe UI', 'Arial'; }
            QGroupBox { font-size: 15px; font-weight: bold; color: #2c3e50; border: 2px solid #3498db; border-radius: 10px; margin-top: 10px; padding: 15px; background: white; }
            QPushButton#ActionBtn { background-color: #27ae60; color: white; border-radius: 6px; font-weight: bold; min-height: 38px; border: none; }
            QPushButton#ExportBtn { background-color: #2980b9; color: white; border-radius: 6px; font-weight: bold; min-height: 38px; border: none; padding: 0 10px; }
            QPushButton#PrintBtn { background-color: #34495e; color: white; border-radius: 6px; font-weight: bold; min-height: 38px; border: none; padding: 0 10px; }
            QTableWidget { background: white; color: black; border: 1px solid #dcdde1; gridline-color: #ecf0f1; }
            QHeaderView::section { background-color: #34495e; color: white; font-weight: bold; padding: 8px; border: none; }
        """)
        self.load_settings()
        self.init_ui()

    def load_settings(self):
        if hasattr(sys, '_MEIPASS'):
            settings_path = os.path.join(os.path.dirname(sys.executable), "settings_data.json")
        else:
            settings_path = resource_path("settings_data.json")
            
        try:
            if os.path.exists(settings_path):
                with open(settings_path, "r", encoding='utf-8') as f:
                    data = json.load(f)
                    self.work_start_1 = data.get("in_limit_1", "08:00")
                    self.work_start_2 = data.get("in_limit_2", "16:00")
            else: self.work_start_1, self.work_start_2 = "08:00", "16:00"
        except: self.work_start_1, self.work_start_2 = "08:00", "16:00"

    def get_holidays_list(self):
        try:
            conn = sqlite3.connect(get_db_path())
            rows = conn.execute("SELECT holiday_date FROM holidays").fetchall()
            conn.close()
            return [str(r[0]) for r in rows]
        except: return []

    def calculate_delay(self, actual, target):
        """ الدالة المعدلة لضمان أدق حساب للتأخير """
        invalid_values = ["--", "None", "", "0", "00:00:00", "None:None", "0:0"]
        if not actual or str(actual).strip() in invalid_values: 
            return 0
        try:
            # تنظيف وسحب الساعات والدقائق فقط
            actual_parts = str(actual).strip().split(':')
            target_parts = str(target).strip().split(':')
            
            if len(actual_parts) < 2 or len(target_parts) < 2:
                return 0

            h_act, m_act = int(actual_parts[0]), int(actual_parts[1])
            h_tgt, m_tgt = int(target_parts[0]), int(target_parts[1])
            
            total_act = h_act * 60 + m_act
            total_tgt = h_tgt * 60 + m_tgt
            
            delay = total_act - total_tgt
            return max(0, delay)
        except: 
            return 0

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.stack = QStackedWidget()
        self.setup_menu_page()
        self.setup_individual_page()
        self.setup_general_page()
        self.stack.addWidget(self.page_menu)
        self.stack.addWidget(self.page_individual)
        self.stack.addWidget(self.page_general)
        self.main_layout.addWidget(self.stack)

    def set_date_range(self, date_widget):
        date_widget.setCalendarPopup(True)
        date_widget.setDisplayFormat("yyyy-MM-dd")
        date_widget.setDate(QDate.currentDate())

    def export_visual_report(self, table, title, target_name, direct_print=False):
        if table.rowCount() == 0:
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات لتصديرها")
            return
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)
        if direct_print:
            print_dialog = QPrintDialog(printer, self)
            if print_dialog.exec_() != QPrintDialog.Accepted: return
        else:
            path, _ = QFileDialog.getSaveFileName(self, "حفظ التقرير", f"{title}.pdf", "PDF Files (*.pdf)")
            if not path: return
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(path)

        logo_img = resource_path("logo.jpg")
        logo_url = QUrl.fromLocalFile(logo_img).toString()
        logo_html = f'<img src="{logo_url}" width="100">' if os.path.exists(logo_img) else ""
        
        table_html = "<table width='100%' style='border-collapse: collapse; text-align: center; font-family: Arial;'>"
        table_html += "<tr style='background-color: #34495e; color: white; font-weight: bold;'>"
        for c in range(table.columnCount()):
            if not table.isColumnHidden(c):
                table_html += f"<th style='padding: 8px; border: 1px solid #333;'>{table.horizontalHeaderItem(c).text()}</th>"
        table_html += "</tr>"

        for r in range(table.rowCount()):
            item_0 = table.item(r, 0)
            item_bg = item_0.background().color() if item_0 else QColor(255, 255, 255)
            bg_hex = item_bg.name() if item_bg.isValid() and item_bg.name() != "#000000" else "#ffffff"
            table_html += f"<tr style='background-color: {bg_hex};'>"
            for c in range(table.columnCount()):
                if not table.isColumnHidden(c):
                    val = table.item(r, c).text() if table.item(r, c) else ""
                    table_html += f"<td style='padding: 6px; border: 1px solid #999; color: black;'>{val}</td>"
            table_html += "</tr>"
        table_html += "</table>"

        full_html = f"""
        <html>
        <body style="direction: rtl; font-family: Arial;">
            <div style="text-align: center;">
                {logo_html}
                <h1 style="color: #2c3e50; margin-bottom: 5px;">مؤسسة وطن التنموية</h1>
                <h2 style="color: #7f8c8d; margin-top: 0;">{title}</h2>
                <p>المعني: <b>{target_name}</b> | تاريخ الطباعة: {datetime.now().strftime('%Y-%m-%d')}</p>
            </div>
            <hr>
            {table_html}
            <br>
            <div style="background: #ecf0f1; padding: 10px; border-radius: 5px;">
                <b>الخلاصة:</b> {self.lbl_ind_stats.text() if "تفصيلي" in title else "تقرير الرقابة العام لجميع الموظفين"}
            </div>
            <br><br>
            <p style="text-align: left; margin-left: 50px;">توقيع مدير الموارد البشرية: ...........................</p>
        </body>
        </html>
        """
        doc = QTextDocument()
        doc.setHtml(full_html)
        doc.print_(printer)
        if not direct_print: QMessageBox.information(self, "تم", "تم تصدير التقرير بنجاح")

    def setup_individual_page(self):
        self.page_individual = QWidget()
        lay = QVBoxLayout(self.page_individual)
        btn_back = QPushButton("🔙 العودة للرئيسية"); btn_back.setFixedWidth(150)
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        lay.addWidget(btn_back, alignment=Qt.AlignRight)
        box = QGroupBox("كشف حضور وانصراف موظف (تفصيلي)")
        f_lay = QGridLayout(box)
        self.ind_emp = QComboBox()
        self.ind_from = QDateEdit(); self.set_date_range(self.ind_from)
        self.ind_to = QDateEdit(); self.set_date_range(self.ind_to)
        self.ind_period = QComboBox()
        self.ind_period.addItems(["الفترتين معاً", "الفترة الأولى فقط", "الفترة الثانية فقط"])
        btn_show = QPushButton("🔍 عرض البيانات"); btn_show.setObjectName("ActionBtn")
        btn_show.clicked.connect(self.load_individual_data)
        btn_excel = QPushButton("📊 Excel"); btn_excel.setObjectName("ExportBtn")
        btn_excel.clicked.connect(lambda: self.export_to_excel(self.table_ind, f"كشف_{self.ind_emp.currentText()}"))
        btn_pdf = QPushButton("📑 PDF"); btn_pdf.setObjectName("ExportBtn")
        btn_pdf.clicked.connect(lambda: self.export_visual_report(self.table_ind, "كشف حضور وانصراف تفصيلي", self.ind_emp.currentText()))
        btn_print = QPushButton("🖨️ طباعة"); btn_print.setObjectName("PrintBtn")
        btn_print.clicked.connect(lambda: self.export_visual_report(self.table_ind, "كشف حضور وانصراف تفصيلي", self.ind_emp.currentText(), True))
        f_lay.addWidget(QLabel("الموظف:"), 0, 0); f_lay.addWidget(self.ind_emp, 0, 1)
        f_lay.addWidget(QLabel("من:"), 0, 2); f_lay.addWidget(self.ind_from, 0, 3)
        f_lay.addWidget(QLabel("إلى:"), 0, 4); f_lay.addWidget(self.ind_to, 0, 5)
        f_lay.addWidget(QLabel("الفترة:"), 1, 0); f_lay.addWidget(self.ind_period, 1, 1)
        f_lay.addWidget(btn_show, 1, 2); f_lay.addWidget(btn_excel, 1, 3); f_lay.addWidget(btn_pdf, 1, 4); f_lay.addWidget(btn_print, 1, 5)
        lay.addWidget(box)
        self.table_ind = QTableWidget(0, 7)
        self.table_ind.setHorizontalHeaderLabels(["التاريخ", "دخول ف1", "تأخير ف1", "دخول ف2", "تأخير ف2", "إجمالي التأخير", "الحالة"])
        self.table_ind.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.table_ind)
        self.lbl_ind_stats = QLabel("✅ الحضور: 0 | ❌ الغياب: 0 | ⏳ التأخير: 0 دقيقة")
        self.lbl_ind_stats.setStyleSheet("font-size: 14px; color: white; background: #34495e; padding: 10px; border-radius: 5px;")
        lay.addWidget(self.lbl_ind_stats)

    def load_individual_data(self):
        eid = self.ind_emp.currentData()
        if eid is None: return
        d1, d2 = self.ind_from.date().toPyDate(), self.ind_to.date().toPyDate()
        period_choice = self.ind_period.currentText()
        holidays = self.get_holidays_list()

        if period_choice == "الفترة الأولى فقط":
            self.table_ind.setColumnHidden(1, False); self.table_ind.setColumnHidden(2, False)
            self.table_ind.setColumnHidden(3, True); self.table_ind.setColumnHidden(4, True)
        elif period_choice == "الفترة الثانية فقط":
            self.table_ind.setColumnHidden(1, True); self.table_ind.setColumnHidden(2, True)
            self.table_ind.setColumnHidden(3, False); self.table_ind.setColumnHidden(4, False)
        else:
            for i in range(5): self.table_ind.setColumnHidden(i, False)

        attendance_data = {}
        try:
            conn = sqlite3.connect(get_db_path())
            query = "SELECT date, check_in, check_in_2 FROM attendance WHERE employee_id=? AND date BETWEEN ? AND ?"
            rows = conn.execute(query, (eid, d1.isoformat(), d2.isoformat())).fetchall()
            for r in rows: attendance_data[r[0]] = {"cin1": r[1], "cin2": r[2]}
            conn.close()
        except: pass

        self.table_ind.setRowCount(0)
        total_delay, present_count, absence_count = 0, 0, 0
        curr = d1
        while curr <= d2:
            date_str = curr.isoformat()
            bg_color = QColor(255, 255, 255)
            row_values = [date_str, "--", "0", "--", "0", "0", ""]

            if date_str in holidays:
                row_values[6] = "إجازة رسمية 🌴"; bg_color = QColor("#dff9fb")
            elif curr.weekday() in [4, 5]: 
                row_values[6] = "عطلة نهاية أسبوع"; bg_color = QColor("#f1f2f6")
            else:
                day_data = attendance_data.get(date_str)
                cin1 = day_data['cin1'] if day_data and day_data['cin1'] not in ["0", "--", None, "00:00:00"] else None
                cin2 = day_data['cin2'] if day_data and day_data['cin2'] not in ["0", "--", None, "00:00:00"] else None
                
                m1 = self.calculate_delay(cin1, self.work_start_1) if cin1 else 0
                m2 = self.calculate_delay(cin2, self.work_start_2) if cin2 else 0

                is_present = False
                day_delay = 0

                if period_choice == "الفترة الأولى فقط":
                    is_present = bool(cin1)
                    day_delay = m1
                    row_values = [date_str, str(cin1 or "--"), str(m1), "--", "0", str(day_delay), "حاضر" if is_present else "غائب ❌"]
                elif period_choice == "الفترة الثانية فقط":
                    is_present = bool(cin2)
                    day_delay = m2
                    row_values = [date_str, "--", "0", str(cin2 or "--"), str(m2), str(day_delay), "حاضر" if is_present else "غائب ❌"]
                else:
                    is_present = bool(cin1 or cin2)
                    day_delay = m1 + m2
                    row_values = [date_str, str(cin1 or "--"), str(m1), str(cin2 or "--"), str(m2), str(day_delay), "حاضر" if is_present else "غائب ❌"]

                if is_present:
                    present_count += 1
                    total_delay += day_delay
                else:
                    absence_count += 1
                    bg_color = QColor("#fab1a0")

            idx = self.table_ind.rowCount(); self.table_ind.insertRow(idx)
            for i, v in enumerate(row_values):
                item = QTableWidgetItem(v); item.setTextAlignment(Qt.AlignCenter); item.setBackground(bg_color); self.table_ind.setItem(idx, i, item)
            curr += timedelta(days=1)
        self.lbl_ind_stats.setText(f"✅ الحضور: {present_count} أيام | ❌ الغياب: {absence_count} أيام | ⏳ إجمالي التأخير: {total_delay} دقيقة")

    def setup_menu_page(self):
        self.page_menu = QWidget()
        lay = QVBoxLayout(self.page_menu)
        title = QLabel("مركز التقارير والرقابة")
        title.setStyleSheet("font-size: 35px; font-weight: bold; color: #2c3e50; margin-top: 50px;")
        title.setAlignment(Qt.AlignCenter); lay.addWidget(title)
        grid = QGridLayout()
        btn_ind = QPushButton("👤\nكشف تفصيلي\nلموظف"); btn_ind.setFixedSize(280, 200)
        btn_ind.setStyleSheet(self.card_style("#3498db")); btn_ind.clicked.connect(self.go_to_individual)
        btn_gen = QPushButton("📊\nتقرير الرقابة\nالعام"); btn_gen.setFixedSize(280, 200)
        btn_gen.setStyleSheet(self.card_style("#e67e22")); btn_gen.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        btn_hols = QPushButton("📅\nإدارة\nالإجازات"); btn_hols.setFixedSize(280, 200)
        btn_hols.setStyleSheet(self.card_style("#9b59b6")); btn_hols.clicked.connect(lambda: HolidayManager(self).exec_())
        grid.addWidget(btn_ind, 0, 0, alignment=Qt.AlignCenter); grid.addWidget(btn_gen, 0, 1, alignment=Qt.AlignCenter); grid.addWidget(btn_hols, 0, 2, alignment=Qt.AlignCenter)
        lay.addLayout(grid)

    def setup_general_page(self):
        self.page_general = QWidget()
        lay = QVBoxLayout(self.page_general)
        btn_back = QPushButton("🔙 رجوع"); btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        lay.addWidget(btn_back, alignment=Qt.AlignRight)
        box = QGroupBox("التقرير العام لجميع الموظفين")
        f_lay = QGridLayout(box)
        self.gen_from, self.gen_to = QDateEdit(), QDateEdit()
        self.set_date_range(self.gen_from); self.set_date_range(self.gen_to)
        self.gen_period = QComboBox(); self.gen_period.addItems(["الفترتين معاً", "الفترة الأولى فقط", "الفترة الثانية فقط"])
        btn_run = QPushButton("📊 توليد التقرير"); btn_run.setObjectName("ActionBtn"); btn_run.clicked.connect(self.load_general_data)
        btn_excel = QPushButton("📊 Excel"); btn_excel.setObjectName("ExportBtn"); btn_excel.clicked.connect(lambda: self.export_to_excel(self.table_gen, "تقرير_الرقابة_العام"))
        btn_pdf = QPushButton("📑 PDF"); btn_pdf.setObjectName("ExportBtn"); btn_pdf.clicked.connect(lambda: self.export_visual_report(self.table_gen, "تقرير الرقابة العام", "كافة الموظفين"))
        btn_print = QPushButton("🖨️ طباعة"); btn_print.setObjectName("PrintBtn"); btn_print.clicked.connect(lambda: self.export_visual_report(self.table_gen, "تقرير الرقابة العام", "كافة الموظفين", True))
        f_lay.addWidget(QLabel("من:"), 0, 0); f_lay.addWidget(self.gen_from, 0, 1); f_lay.addWidget(QLabel("إلى:"), 0, 2); f_lay.addWidget(self.gen_to, 0, 3); f_lay.addWidget(QLabel("الفترة:"), 0, 4); f_lay.addWidget(self.gen_period, 0, 5)
        f_lay.addWidget(btn_run, 1, 1); f_lay.addWidget(btn_excel, 1, 2); f_lay.addWidget(btn_pdf, 1, 3); f_lay.addWidget(btn_print, 1, 4)
        lay.addWidget(box)
        self.table_gen = QTableWidget(0, 6)
        self.table_gen.setHorizontalHeaderLabels(["إجمالي التأخير", "تأخير ف2", "تأخير ف1", "الغياب (أيام)", "الحضور (أيام)", "اسم الموظف"])
        self.table_gen.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.table_gen)

    def load_general_data(self):
        d1, d2 = self.gen_from.date().toPyDate(), self.gen_to.date().toPyDate()
        holidays = self.get_holidays_list()
        period_choice = self.gen_period.currentText()

        if period_choice == "الفترة الأولى فقط":
            self.table_gen.setColumnHidden(2, False); self.table_gen.setColumnHidden(1, True)
        elif period_choice == "الفترة الثانية فقط":
            self.table_gen.setColumnHidden(2, True); self.table_gen.setColumnHidden(1, False)
        else:
            self.table_gen.setColumnHidden(2, False); self.table_gen.setColumnHidden(1, False)

        try:
            conn = sqlite3.connect(get_db_path())
            emps = conn.execute("SELECT finger_id, name FROM employees").fetchall()
            self.table_gen.setRowCount(0)
            for f_id, name in emps:
                query = "SELECT date, check_in, check_in_2 FROM attendance WHERE employee_id=? AND date BETWEEN ? AND ?"
                att_dict = {r[0]: (r[1], r[2]) for r in conn.execute(query, (f_id, d1.isoformat(), d2.isoformat())).fetchall()}
                pres, ab_days, delay_f1, delay_f2 = 0, 0, 0, 0
                curr = d1
                while curr <= d2:
                    d_str = curr.isoformat()
                    if d_str not in holidays and curr.weekday() not in [4, 5]:
                        day = att_dict.get(d_str)
                        cin1 = day[0] if day and day[0] not in ["0", "--", None, "00:00:00"] else None
                        cin2 = day[1] if day and day[1] not in ["0", "--", None, "00:00:00"] else None
                        
                        m1 = self.calculate_delay(cin1, self.work_start_1) if cin1 else 0
                        m2 = self.calculate_delay(cin2, self.work_start_2) if cin2 else 0

                        is_p = False
                        if period_choice == "الفترة الأولى فقط":
                            is_p = bool(cin1)
                            if is_p: delay_f1 += m1
                        elif period_choice == "الفترة الثانية فقط":
                            is_p = bool(cin2)
                            if is_p: delay_f2 += m2
                        else:
                            is_p = bool(cin1 or cin2)
                            if is_p:
                                delay_f1 += m1
                                delay_f2 += m2
                        
                        if is_p: pres += 1
                        else: ab_days += 1
                    curr += timedelta(days=1)
                
                idx = self.table_gen.rowCount(); self.table_gen.insertRow(idx)
                vals = [f"{delay_f1+delay_f2} د", f"{delay_f2} د", f"{delay_f1} د", str(ab_days), str(pres), name]
                for i, v in enumerate(vals):
                    item = QTableWidgetItem(v); item.setTextAlignment(Qt.AlignCenter); self.table_gen.setItem(idx, i, item)
            conn.close()
        except: pass

    def export_to_excel(self, table, filename):
        if table.rowCount() == 0: return
        path, _ = QFileDialog.getSaveFileName(self, "حفظ Excel", f"{filename}.xlsx", "Excel Files (*.xlsx)")
        if path:
            headers = []
            visible_cols = []
            for i in range(table.columnCount()):
                if not table.isColumnHidden(i):
                    headers.append(table.horizontalHeaderItem(i).text())
                    visible_cols.append(i)
            data = []
            for r in range(table.rowCount()):
                row_data = []
                for c in visible_cols:
                    row_data.append(table.item(r, c).text())
                data.append(row_data)
            pd.DataFrame(data, columns=headers).to_excel(path, index=False)
            QMessageBox.information(self, "تم", "تم التصدير بنجاح")

    def card_style(self, color):
        return f"QPushButton {{ background: white; color: {color}; border: 4px solid {color}; border-radius: 20px; font-size: 18px; font-weight: bold; }} QPushButton:hover {{ background: {color}; color: white; }}"

    def go_to_individual(self):
        self.ind_emp.clear()
        try:
            conn = sqlite3.connect(get_db_path())
            cur = conn.execute("SELECT finger_id, name FROM employees ORDER BY name ASC").fetchall()
            for row in cur: self.ind_emp.addItem(row[1], row[0])
            conn.close(); self.stack.setCurrentIndex(1)
        except: pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ReportsWindow()
    win.show()
    sys.exit(app.exec_())