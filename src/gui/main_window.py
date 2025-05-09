from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QComboBox, QCheckBox, QScrollArea, QFrame
)
from PyQt5.QtCore import QThread, pyqtSignal, QSettings, Qt
from PyQt5.QtGui import QPixmap, QTextCursor, QColor, QTextCharFormat
from gui.memory_window import MemoryViewer
from llama_cpp_agent import LlamaCppAgent
import os

class LlamaThread(QThread):
    response_ready = pyqtSignal(str)

    def __init__(self, agent, prompt):
        super().__init__()
        self.agent = agent
        self.prompt = prompt

    def run(self):
        try:
            prompt_with_instruction = f"Réponds uniquement à la question suivante : {self.prompt}"
            response = self.agent.generate(prompt_with_instruction)
            self.response_ready.emit(response)
        except Exception as e:
            self.response_ready.emit(f"[ERREUR] [AGENT] Erreur lors de la génération : {str(e)}")

class MainWindow(QWidget):
    def __init__(self, model_paths: dict):
        super().__init__()
        self.setWindowTitle("Alice - Interface")
        self.setGeometry(100, 100, 800, 600)

        self.model_paths = model_paths
        self.agent = None
        self.settings = QSettings("AliceAI", "AliceApp")

        self.setup_ui()

        last_model = self.settings.value("last_model", self.model_selector.itemText(0))
        index = self.model_selector.findText(last_model)
        self.model_selector.setCurrentIndex(index if index != -1 else 0)
        self.load_model(self.model_selector.currentText())

    def setup_ui(self):
        main_layout = QVBoxLayout()

        # Top controls layout
        controls_layout = QHBoxLayout()

        self.voice_checkbox = QCheckBox("Voix")
        self.voice_checkbox.setChecked(self.settings.value("voice_enabled", True, type=bool))
        self.voice_checkbox.stateChanged.connect(self.toggle_voice)

        self.memory_button = QPushButton("Mémoire")
        self.memory_button.clicked.connect(self.open_memory_window)

        self.model_selector = QComboBox()
        self.model_selector.addItems(self.model_paths.keys())
        self.model_selector.currentTextChanged.connect(self.load_model)

        controls_layout.addWidget(self.voice_checkbox)
        controls_layout.addWidget(self.memory_button)
        controls_layout.addWidget(self.model_selector)

        main_layout.addLayout(controls_layout)

        # Response area
        self.response_box = QTextEdit()
        self.response_box.setReadOnly(True)
        main_layout.addWidget(self.response_box)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setVisible(False)
        main_layout.addWidget(self.image_label)

        # Prompt input area (bottom)
        input_layout = QVBoxLayout()
        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Entrez votre message pour Alice...")

        buttons_layout = QHBoxLayout()
        self.send_button = QPushButton("Envoyer")
        self.send_button.clicked.connect(self.send_prompt)
        self.save_button = QPushButton("#save")
        self.save_button.clicked.connect(self.save_prompt)
        buttons_layout.addWidget(self.send_button)
        buttons_layout.addWidget(self.save_button)

        self.explanation_label = QLabel("Tapez '#save' pour enregistrer la donnée dans la mémoire.")
        self.explanation_label.setAlignment(Qt.AlignCenter)

        input_layout.addWidget(self.input_box)
        input_layout.addLayout(buttons_layout)
        input_layout.addWidget(self.explanation_label)

        main_layout.addLayout(input_layout)
        self.setLayout(main_layout)

    def format_response(self, sender: str, text: str):
        if "[IMAGE]" in text:
            return f"{sender} : [Image générée]"
        if "```" in text:
            return f"{sender} :\n<code>\n{text}\n</code>"
        return f"{sender} : {text}"

    def load_model(self, model_name):
        try:
            path = self.model_paths[model_name]
            self.agent = LlamaCppAgent(path)
            self.agent.set_speech_enabled(self.voice_checkbox.isChecked())
            self.response_box.append(f"[INFO] Modèle chargé : {model_name}")
            self.settings.setValue("last_model", model_name)
        except Exception as e:
            self.response_box.append(f"[ERREUR] Chargement du modèle : {str(e)}")

    def toggle_voice(self):
        if self.agent:
            self.agent.set_speech_enabled(self.voice_checkbox.isChecked())
        self.settings.setValue("voice_enabled", self.voice_checkbox.isChecked())

    def send_prompt(self):
        prompt = self.input_box.toPlainText().strip()
        if not prompt:
            return

        self.response_box.append(self.format_response("Vous", prompt))
        self.input_box.clear()
        self.send_button.setEnabled(False)

        if any(keyword in prompt.lower() for keyword in ["#save", "cree", "ajoute", "souviens-toi", "enregistre"]):
            if self.agent and hasattr(self.agent, 'db_manager'):
                self.agent.db_manager.save_memory(prompt, "Ajout automatique via mot-clé")
                self.response_box.append("[INFO] Mémoire enregistrée automatiquement.")

        if self.agent:
            self.agent.set_speech_enabled(self.voice_checkbox.isChecked())

        self.thread = LlamaThread(self.agent, prompt)
        self.thread.response_ready.connect(self.display_response)
        self.thread.start()

    def display_response(self, response):
        if response.startswith("[ERREUR]"):
            self.response_box.append(response)
        else:
            self.response_box.append(self.format_response("Alice", response))

            if "[IMAGE]" in response and "output.png" in response:
                image_path = os.path.abspath("output.png")
                if os.path.exists(image_path):
                    pixmap = QPixmap(image_path).scaledToWidth(512)
                    self.image_label.setPixmap(pixmap)
                    self.image_label.setVisible(True)
                else:
                    self.response_box.append("[INFO] Image demandée mais introuvable.")
            else:
                self.image_label.clear()
                self.image_label.setVisible(False)

        self.send_button.setEnabled(True)

    def save_prompt(self):
        prompt = self.input_box.toPlainText().strip().lower()
        keywords = ["cree", "ajoute", "remplace", "souviens-toi", "enregistre", "#save"]
        if any(keyword in prompt for keyword in keywords):
            self.agent.db_manager.save_memory(prompt, "Donnée sauvegardée par l'utilisateur")
            self.response_box.append("[INFO] Donnée sauvegardée avec succès.")
        else:
            self.response_box.append("[INFO] Aucun mot-clé détecté pour la sauvegarde.")

    def open_memory_window(self):
        self.memory_window = MemoryViewer()
        self.memory_window.show()

    def closeEvent(self, event):
        self.settings.setValue("voice_enabled", self.voice_checkbox.isChecked())
        self.settings.setValue("last_model", self.model_selector.currentText())
        event.accept()
