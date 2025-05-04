from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel
from db.mysql_manager import MySQLManager


class MemoryWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mémoire d'Alice")
        self.setGeometry(150, 150, 600, 400)

        layout = QVBoxLayout()

        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        layout.addWidget(QLabel("Historique des échanges enregistrés :"))
        layout.addWidget(self.text_display)

        self.refresh_button = QPushButton("Rafraîchir")
        self.refresh_button.clicked.connect(self.load_memory)
        layout.addWidget(self.refresh_button)

        self.setLayout(layout)
        self.load_memory()

    def load_memory(self):
        try:
            db = MySQLManager()
            db.cursor.execute("SELECT prompt, response FROM memory ORDER BY id DESC")
            rows = db.cursor.fetchall()
            db.close()

            self.text_display.clear()
            if rows:
                for prompt, response in rows:
                    self.text_display.append(f"Vous : {prompt}\nAlice : {response}\n{'-'*50}")
            else:
                self.text_display.setText("Aucune donnée enregistrée.")
        except Exception as e:
            self.text_display.setText(f"[Erreur MySQL] : {str(e)}")
