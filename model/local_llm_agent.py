# src/gui/main_window.py

import os
from PyQt5.QtWidgets import QWidget, QTextEdit, QPushButton, QVBoxLayout, QComboBox, QLabel
from src.model.local_llm_agent import LocalLLMAgent

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Alice - Interface IA")
        self.setGeometry(100, 100, 800, 600)

        self.agent = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.model_selector = QComboBox()
        self.model_selector.addItems(["Mistral", "Nous-Hermes"])
        layout.addWidget(QLabel("Choix du modèle :"))
        layout.addWidget(self.model_selector)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Entrez votre message ici...")
        layout.addWidget(self.input_field)

        self.send_button = QPushButton("Envoyer")
        self.send_button.clicked.connect(self.send_message)
        layout.addWidget(self.send_button)

        self.setLayout(layout)

    def load_agent(self):
        selected = self.model_selector.currentText()
        model_filename = {
            "Mistral": "mistral-7b-instruct-v0.2.Q8_0.gguf",
            "Nous-Hermes": "nous-hermes-2-mixtral-8x7b-sft.Q8_0.gguf"
        }.get(selected)

        model_path = os.path.join("model", model_filename)
        if self.agent is None or self.agent.llm.model_path != model_path:
            self.agent = LocalLLMAgent(model_path)

    def send_message(self):
        user_input = self.input_field.toPlainText().strip()
        if not user_input:
            return

        self.chat_display.append(f"👤 Utilisateur : {user_input}")
        self.load_agent()

        try:
            response = self.agent.generate(user_input)
            self.chat_display.append(f"🤖 Alice : {response}\n")
        except Exception as e:
            self.chat_display.append(f"[Erreur IA] {str(e)}\n")

        self.input_field.clear()
