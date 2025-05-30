def apply_dark_theme(app):
    dark_stylesheet = """
    QWidget {
        background-color: #1e1e1e;
        color: #e0e0e0;
        font-family: 'Segoe UI', sans-serif;
        font-size: 14px;
    }
    QPushButton {
        background-color: #333;
        border: 1px solid #555;
        border-radius: 8px;
        padding: 6px 12px;
    }
    QPushButton:hover {
        background-color: #444;
    }
    QLineEdit, QTextEdit {
        background-color: #2c2c2c;
        border: 1px solid #444;
        border-radius: 6px;
        padding: 6px;
        color: #e0e0e0;
    }
    QLabel {
        font-size: 16px;
    }
    """
    app.setStyleSheet(dark_stylesheet)
