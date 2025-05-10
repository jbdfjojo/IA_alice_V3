from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QLabel, QCheckBox, QComboBox, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QPixmap
from src.llama_cpp_agent import LlamaCppAgent, LlamaThread
from gui.memory_window import MemoryViewer # Assure-toi que ce fichier existe

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

        # Top controls
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

        # Prompt area
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

    def load_model(self, model_name):
        self.settings.setValue("last_model", model_name)
        model_path = self.model_paths.get(model_name)
        if model_path:
            self.agent = LlamaCppAgent(self.model_paths)
            self.agent.set_speech_enabled(self.voice_checkbox.isChecked())

    def toggle_voice(self):
        if self.agent:
            self.agent.set_speech_enabled(self.voice_checkbox.isChecked())
        self.settings.setValue("voice_enabled", self.voice_checkbox.isChecked())

    def send_prompt(self):
        prompt = self.input_box.toPlainText().strip()
        if not prompt:
            return

        self.input_box.clear()
        self.response_box.append(f"<b>Vous :</b> {prompt}")

        self.thread = LlamaThread(self.agent, prompt)
        self.thread.response_ready.connect(self.display_response)
        self.thread.start()

    def save_prompt(self):
        text = self.input_box.toPlainText().strip()
        if text:
            self.input_box.setText(f"{text} #save")
            self.send_prompt()

    def display_response(self, response):
        if "#image" in response:
            path = response.replace("#image", "").strip()
            self.image_label.setPixmap(QPixmap(path).scaled(400, 400, Qt.KeepAspectRatio))
            self.image_label.setVisible(True)
        else:
            self.image_label.setVisible(False)
        self.response_box.append(f"<b>Alice :</b> {response}")

    def open_memory_window(self):
        self.memory_window = MemoryViewer()
        self.memory_window.show()
