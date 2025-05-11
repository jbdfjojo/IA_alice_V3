import sys
import os
import json
import pyttsx3
import speech_recognition as sr
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QCheckBox, QComboBox,
    QScrollArea
)
from gui.memory_window import MemoryViewer  # fenêtre mémoire

# Simuler un agent pour test
class LlamaCppAgent:
    def __init__(self, model_paths: dict):
        self.model_paths = model_paths
        self.speech_enabled = False

    def set_speech_enabled(self, enabled):
        self.speech_enabled = enabled

    def generate(self, prompt):
        return f"Réponse générée pour: {prompt}"

    def get_all_memory(self):
        return "Mémoire d'exemple."

def load_config():
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, "r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as e:
                print(f"[ERREUR] config.json malformé: {e}")
    return {}

def save_config(config):
    with open("config.json", "w") as file:
        json.dump(config, file, indent=4)

# THREAD POUR LE MICRO
class VoiceRecognitionThread(QThread):
    result_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            while self.running:
                print("🎤 En écoute...")
                try:
                    audio = recognizer.listen(source, timeout=5)
                    text = recognizer.recognize_google(audio, language="fr-FR")
                    self.result_signal.emit(text)
                except sr.WaitTimeoutError:
                    continue  # Aucun son détecté dans le délai -> réécoute
                except sr.UnknownValueError:
                    self.result_signal.emit("[Audio incompréhensible]")
                except sr.RequestError:
                    self.result_signal.emit("[Erreur API de reconnaissance vocale]")

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


class MainWindow(QWidget):
    def __init__(self, model_paths: dict):
        super().__init__()
        self.setWindowTitle("Alice - Interface")
        self.setGeometry(100, 100, 800, 600)

        self.model_paths = model_paths
        self.agent = None

        self.config = load_config()
        self.voice_input_enabled = False
        self.tts_engine = pyttsx3.init()

        self.voice_recognition_thread = None
        self.setup_ui()

        last_model = self.config.get("last_model", "Mistral-7B-Instruct")
        index = self.model_selector.findText(last_model)
        self.model_selector.setCurrentIndex(index if index != -1 else 0)
        self.load_model(self.model_selector.currentText())

        self.voice_checkbox.setChecked(self.config.get("voice_enabled", True))

    def setup_ui(self):
        main_layout = QVBoxLayout()
        controls_layout = QHBoxLayout()

        self.voice_checkbox = QCheckBox("Voix")
        self.voice_checkbox.setChecked(True)
        self.voice_checkbox.stateChanged.connect(self.toggle_voice)

        self.memory_button = QPushButton("Mémoire")
        self.memory_button.clicked.connect(self.open_memory_window)

        self.model_selector = QComboBox()
        self.model_selector.addItems(self.model_paths.keys())
        self.model_selector.currentTextChanged.connect(self.load_model)

        self.voice_button = QPushButton("🎤 Micro: OFF")
        self.voice_button.setCheckable(True)
        self.voice_button.clicked.connect(self.toggle_voice_input)

        controls_layout.addWidget(self.voice_checkbox)
        controls_layout.addWidget(self.memory_button)
        controls_layout.addWidget(self.model_selector)
        controls_layout.addWidget(self.voice_button)

        main_layout.addLayout(controls_layout)

        self.response_box = QTextEdit()
        self.response_box.setReadOnly(True)
        main_layout.addWidget(self.response_box)

        self.waiting_label = QLabel("Alice travaille sur votre demande...")
        self.waiting_label.setAlignment(Qt.AlignCenter)
        self.waiting_label.setVisible(False)
        main_layout.addWidget(self.waiting_label)

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

        self.scroll_area = QScrollArea()
        self.image_label = QLabel()
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setVisible(False)
        main_layout.addWidget(self.scroll_area)

        self.setLayout(main_layout)

    def load_model(self, model_name):
        self.config["last_model"] = model_name
        save_config(self.config)
        model_path = self.model_paths.get(model_name)
        if model_path:
            self.agent = LlamaCppAgent(self.model_paths)
            self.agent.set_speech_enabled(self.voice_checkbox.isChecked())
        else:
            print(f"[ERREUR] Modèle introuvable: {model_name}")

    def toggle_voice(self):
        if self.agent:
            self.agent.set_speech_enabled(self.voice_checkbox.isChecked())
        self.config["voice_enabled"] = self.voice_checkbox.isChecked()
        save_config(self.config)

    def toggle_voice_input(self):
        if self.voice_input_enabled:
            self.voice_input_enabled = False
            self.voice_button.setText("🎤 Micro: OFF")
            if self.voice_recognition_thread:
                self.voice_recognition_thread.stop()
                self.voice_recognition_thread = None
        else:
            self.voice_input_enabled = True
            self.voice_button.setText("🎤 Micro: ON")
            self.voice_recognition_thread = VoiceRecognitionThread()
            self.voice_recognition_thread.result_signal.connect(self.handle_voice_input)
            self.voice_recognition_thread.start()


    def handle_voice_input(self, text):
        self.input_box.setPlainText(text)
        self.send_prompt()  # déclenche automatiquement la réponse

    def send_prompt(self):
        prompt = self.input_box.toPlainText().strip()
        if prompt:
            self.response_box.append(f"Vous: {prompt}")
            self.input_box.clear()
            self.waiting_label.setVisible(True)
            response = self.agent.generate(prompt)
            self.response_box.append(f"Alice: {response}")
            self.waiting_label.setVisible(False)

    def save_prompt(self):
        prompt = self.input_box.toPlainText().strip()
        if prompt:
            print(f"Prompt sauvegardé: {prompt}")  # à remplacer

    def open_memory_window(self):
        memory_data = self.agent.get_all_memory()
        self.memory_window = MemoryViewer(memory_data)
        self.memory_window.show()

if __name__ == "__main__":
    model_paths = {
        "Mistral-7B-Instruct": "C:/Users/Blazufr/Desktop/IA_alice_V3/model/mistral-7b-instruct-v0.2.Q8_0",
        "Nous-Hermes-2-Mixtral": "C:/Users/Blazufr/Desktop/IA_alice_V3/model/nous-hermes-llama2-13b.Q8_0"
    }
    app = QApplication(sys.argv)
    window = MainWindow(model_paths)
    window.show()
    sys.exit(app.exec_())
