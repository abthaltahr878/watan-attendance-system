STYLE_SHEET = """
QMainWindow, QWidget {
    background-color: #f5f6fa;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QPushButton#MenuCard {
    background-color: #ffffff;
    color: #2d3436;
    border-radius: 20px;
    border: 1px solid #e1e8ed;
    padding: 20px;
    font-size: 18px;
    font-weight: bold;
}
QPushButton#MenuCard:hover {
    border: 2px solid #0984e3;
    color: #0984e3;
    margin-top: -5px;
}
QPushButton#PrimaryBtn {
    background-color: #0984e3;
    color: white;
    border-radius: 10px;
    padding: 10px;
    font-weight: bold;
}
QPushButton#DangerBtn {
    background-color: #eb4d4b;
    color: white;
    border-radius: 10px;
    padding: 10px;
}
QLineEdit {
    padding: 10px;
    border: 1px solid #dcdde1;
    border-radius: 8px;
    background-color: white;
}
QTableWidget {
    background-color: white;
    border-radius: 15px;
    gridline-color: #f1f2f6;
}
QHeaderView::section {
    background-color: #f8f9fa;
    padding: 12px;
    font-weight: bold;
    border-bottom: 2px solid #0984e3;
}
"""