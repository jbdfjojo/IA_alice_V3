import mysql.connector
from mysql.connector import Error
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea, QMessageBox,
    QHBoxLayout, QTextEdit, QFrame
)
from PyQt5.QtCore import Qt


class MemoryViewer(QWidget):
    def __init__(self, memory_data, style_sheet=None):
        super().__init__()

        self.setWindowTitle("Mémoire d'Alice")
        self.resize(800, 600)
        if style_sheet:  # Applique le style si fourni
            self.setStyleSheet(style_sheet)

        # Connexion MySQL
        try:
            self.conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="JOJOJOJO88",
                database="ia_alice"
            )
            self.cursor = self.conn.cursor()
            print("[MySQL] Connexion réussie.")
        except Error as e:
            print(f"[MySQL] Erreur de connexion : {e}")

        # Layout principal
        self.layout = QVBoxLayout()

        title = QLabel("Mémoire d'Alice :")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.layout.addWidget(title)

        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.layout.addWidget(self.scroll_area)

        # Boutons
        buttons_layout = QHBoxLayout()
        self.delete_all_button = QPushButton("Tout supprimer")
        self.delete_all_button.clicked.connect(self.delete_all_memory)
        buttons_layout.addWidget(self.delete_all_button)

        self.close_button = QPushButton("Fermer")
        self.close_button.clicked.connect(self.close)
        buttons_layout.addWidget(self.close_button)

        self.layout.addLayout(buttons_layout)
        self.setLayout(self.layout)

        self.load_memory()

    def load_memory(self):
        try:
            self.cursor.execute("SELECT id, prompt, response FROM memory")
            records = self.cursor.fetchall()

            if records:
                for record in records:
                    mem_id, prompt, response = record

                    entry_frame = QFrame()
                    entry_layout = QVBoxLayout(entry_frame)
                    text = QTextEdit()
                    text.setReadOnly(True)
                    text.setPlainText(f"Vous : {prompt}\nAlice : {response}")
                    entry_layout.addWidget(text)

                    del_button = QPushButton("Supprimer")
                    del_button.clicked.connect(lambda _, m_id=mem_id, f=entry_frame: self.delete_memory(m_id, f))
                    entry_layout.addWidget(del_button, alignment=Qt.AlignRight)

                    self.scroll_layout.addWidget(entry_frame)
            else:
                empty_label = QLabel("Aucune mémoire enregistrée.")
                self.scroll_layout.addWidget(empty_label)

        except Error as e:
            print(f"[MySQL] Erreur de lecture de la mémoire : {e}")

    def delete_memory(self, mem_id, frame):
        try:
            self.cursor.execute("DELETE FROM memory WHERE id = %s", (mem_id,))
            self.conn.commit()
            self.scroll_layout.removeWidget(frame)
            frame.setParent(None)
        except Error as e:
            print(f"[MySQL] Erreur de suppression : {e}")

    def delete_all_memory(self):
        confirm = QMessageBox.question(
            self, "Confirmation", "Supprimer toute la mémoire ?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            try:
                self.cursor.execute("DELETE FROM memory")
                self.conn.commit()
                # Vider l'interface
                while self.scroll_layout.count():
                    child = self.scroll_layout.takeAt(0)
                    if child.widget():
                        child.widget().setParent(None)
            except Error as e:
                print(f"[MySQL] Erreur lors de la suppression totale : {e}")

    def close(self):
        if self.conn.is_connected():
            self.cursor.close()
            self.conn.close()
            print("[MySQL] Connexion fermée.")
        super().close()

    def save_to_database(self, prompt, response):
        try:
            self.cursor.execute(
                "INSERT INTO memory (prompt, response) VALUES (%s, %s)",
                (prompt, response)
            )
            self.conn.commit()
            print("[MySQL] Interaction sauvegardée.")
        except Error as e:
            print(f"[MySQL] Erreur lors de l'insertion : {e}")
