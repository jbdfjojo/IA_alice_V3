import os
import json
import time
import pyttsx3
import speech_recognition as sr
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMutex, QThreadPool, QRunnable
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel,
    QCheckBox, QComboBox, QScrollArea, QApplication
)
from llama_cpp_agent import LlamaCppAgent
from gui.memory_window import MemoryViewer


# Thread reconnaissance vocale
class VoiceRecognitionThread(QThread):
    result_signal = pyqtSignal(str)

    def __init__(self, agent):
        super().__init__()
        self.agent = agent
        self.running = True
        self.is_paused = False
        self.is_processing_response = False
        self.mutex = QMutex()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone(device_index=1)

        # Debug pour afficher les micros dispo
        print("Microphones disponibles :")
        for i, name in enumerate(sr.Microphone.list_microphone_names()):
            print(f"{i}: {name}")

    def run(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            while self.running:
                self.mutex.lock()
                if self.is_paused or self.is_processing_response:
                    self.mutex.unlock()
                    time.sleep(0.1)
                    continue
                self.mutex.unlock()

                try:
                    print("🎤 En écoute...")
                    audio = self.recognizer.listen(source, timeout=10)
                    print("🔊 Traitement audio...")

                    text = self.recognizer.recognize_google(audio, language="fr-FR").lower()
                    print(f"[DEBUG] Texte reconnu brut : '{text}'")

                    if "alice" in text:
                        print("[DEBUG] Mot-clé 'alice' détecté")

                        cleaned_text = text.split("alice", 1)[-1].strip()
                        if cleaned_text:
                            self.is_processing_response = True
                            self.result_signal.emit(cleaned_text)
                        else:
                            print("⚠️ Mot-clé détecté, mais rien après.")
                    else:
                        print("🔇 Aucun mot-clé détecté dans : ", text)

                except sr.WaitTimeoutError:
                    print("⏱️ Aucun son détecté.")
                except sr.UnknownValueError:
                    print("🤷 Audio incompréhensible")
                except sr.RequestError as e:
                    print(f"❌ Erreur API : {e}")
                finally:
                    self.is_processing_response = False

    def pause(self):
        self.is_paused = True
        print("🎤 Pause du micro.")

    def resume(self):
        self.is_paused = False
        print("🎤 Reprise du micro.")

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


# Exécuter une fonction dans un thread sans bloquer l'UI
class RunnableFunc(QRunnable):
    def __init__(self, func):
        super().__init__()
        self.func = func

    def run(self):
        self.func()


# Fonction utilitaire
def load_config():
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, "r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as e:
                print(f"[ERREUR CONFIG] : {e}")
    return {}


def save_config(config):
    with open("config.json", "w") as file:
        json.dump(config, file, indent=4)


# Interface principale
class MainWindow(QWidget):
    def __init__(self, model_paths: dict, agent):
        super().__init__()
        self.setWindowTitle("Alice - Interface IA")
        self.setGeometry(100, 100, 800, 600)

        self.model_paths = model_paths
        self.agent = agent
        self.config = load_config()

        self.voice_input_enabled = False
        self.voice_recognition_thread = VoiceRecognitionThread(self.agent)
        self.voice_recognition_thread.result_signal.connect(self.on_text_recognized)
        self.voice_recognition_thread.start()

        self.is_user_speaking = True

        self.setup_ui()

        # Restaurer le modèle précédent
        last_model = self.config.get("last_model", "Mistral-7B-Instruct")
        index = self.model_selector.findText(last_model)
        self.model_selector.setCurrentIndex(index if index != -1 else 0)
        self.voice_checkbox.setChecked(self.config.get("voice_enabled", True))

    def setup_ui(self):
        layout = QVBoxLayout()
        control_layout = QHBoxLayout()

        self.voice_checkbox = QCheckBox("Voix")
        self.voice_checkbox.stateChanged.connect(self.toggle_voice)

        self.memory_button = QPushButton("Mémoire")
        self.memory_button.clicked.connect(self.open_memory_window)

        self.model_selector = QComboBox()
        self.model_selector.addItems(self.model_paths.keys())
        self.model_selector.currentTextChanged.connect(self.load_model)

        self.voice_button = QPushButton("🎤 Micro: OFF")
        self.voice_button.setCheckable(True)
        self.voice_button.clicked.connect(self.toggle_voice_input)

        control_layout.addWidget(self.voice_checkbox)
        control_layout.addWidget(self.memory_button)
        control_layout.addWidget(self.model_selector)
        control_layout.addWidget(self.voice_button)

        layout.addLayout(control_layout)

        self.response_box = QTextEdit()
        self.response_box.setReadOnly(True)
        layout.addWidget(self.response_box)

        self.waiting_label = QLabel("Alice réfléchit...")
        self.waiting_label.setAlignment(Qt.AlignCenter)
        self.waiting_label.setVisible(False)
        layout.addWidget(self.waiting_label)

        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Entrez votre message ici...")
        layout.addWidget(self.input_box)

        button_layout = QHBoxLayout()
        self.send_button = QPushButton("Envoyer")
        self.send_button.clicked.connect(self.send_prompt)
        self.save_button = QPushButton("Sauvegarder")
        self.save_button.clicked.connect(self.save_prompt)
        button_layout.addWidget(self.send_button)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

        self.image_label = QLabel()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setVisible(False)
        layout.addWidget(self.scroll_area)

        self.setLayout(layout)

    def toggle_voice(self, state):
        self.config["voice_enabled"] = bool(state)
        save_config(self.config)

    def toggle_voice_input(self):
        self.voice_input_enabled = not self.voice_input_enabled
        if self.voice_input_enabled:
            self.voice_button.setText("🎤 Micro: ON")
            self.voice_recognition_thread.resume()
        else:
            self.voice_button.setText("🎤 Micro: OFF")
            self.voice_recognition_thread.pause()

    def load_model(self, model_name):
        self.config["last_model"] = model_name
        save_config(self.config)

        try:
            self.agent = LlamaCppAgent(self.model_paths, selected_model=model_name)
            print(f"✅ Modèle chargé : {model_name}")
            self.voice_recognition_thread.agent = self.agent  # Update agent dans le thread
        except Exception as e:
            print(f"[ERREUR CHARGEMENT MODÈLE] : {e}")

    def on_text_recognized(self, text):
        if self.is_user_speaking:
            self.response_box.append(f"[Vous] {text}")
            self.input_box.setText(text)
            self.is_user_speaking = False

            self.voice_recognition_thread.pause()

            if "image" in text.lower():
                self.generate_image_from_text(text)
            elif "code" in text.lower():
                self.generate_code_from_text(text)
            else:
                self.generate_model_response(text)

    def generate_model_response(self, prompt):
        self.waiting_label.setVisible(True)
        QApplication.processEvents()

        def run():
            response = self.agent.generate(prompt)
            self.response_box.append(f"[Alice] {response}")
            self.waiting_label.setVisible(False)

            if self.voice_checkbox.isChecked():
                self.agent.speak(response)

            self.is_user_speaking = True
            self.voice_recognition_thread.resume()

        QThreadPool.globalInstance().start(RunnableFunc(run))

    def generate_image_from_text(self, text):
        result = self.agent.generate_image(text)
        self.response_box.append(result)

    def generate_code_from_text(self, text):
        self.response_box.append("[Code] (fonction à implémenter)")

    def send_prompt(self):
        prompt = self.input_box.toPlainText().strip()
        if prompt:
            self.response_box.append(f"[Vous] {prompt}")
            self.generate_model_response(prompt)

    def save_prompt(self):
        prompt = self.input_box.toPlainText().strip()
        if prompt:
            self.agent.save_to_memory(prompt, "Interaction sauvegardée manuellement.")
            self.response_box.append("[✔] Interaction sauvegardée.")

    def open_memory_window(self):
        mem_window = MemoryViewer(self.agent)
        mem_window.exec_()

    def closeEvent(self, event):
        self.voice_recognition_thread.stop()
        event.accept()
