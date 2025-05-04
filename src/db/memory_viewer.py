# src/gui/memory_window.py

import mysql.connector
from mysql.connector import Error
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton

class MemoryViewer(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Mémoire d'Alice")
        self.resize(600, 400)

        # Connexion à MySQL
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

        # Interface graphique
        self.layout = QVBoxLayout()

        self.memory_display = QTextEdit()
        self.memory_display.setReadOnly(True)
        self.layout.addWidget(QLabel("Mémoire d'Alice :"))
        self.layout.addWidget(self.memory_display)

        self.button_close = QPushButton("Fermer")
        self.button_close.clicked.connect(self.close)
        self.layout.addWidget(self.button_close)

        self.setLayout(self.layout)

        # Charger la mémoire
        self.load_memory()

    def load_memory(self):
        try:
            self.cursor.execute("SELECT prompt, response FROM memory")
            records = self.cursor.fetchall()

            if records:
                for prompt, response in records:
                    self.memory_display.append(f"Vous : {prompt}\nAlice : {response}\n\n")
            else:
                self.memory_display.append("Aucune mémoire enregistrée.")

        except Error as e:
            print(f"[MySQL] Erreur de lecture de la mémoire : {e}")
        
    def close(self):
        if self.conn.is_connected():
            self.cursor.close()
            self.conn.close()
            print("[MySQL] Connexion fermée.")
        super().close()
