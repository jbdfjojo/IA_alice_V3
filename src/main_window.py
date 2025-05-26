import os
import json
import time
import pyttsx3
import speech_recognition as sr
import pyperclip
import re
from html import escape

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMutex, QThreadPool, QRunnable, QTimer, QMetaObject, Q_ARG
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel,
    QCheckBox, QComboBox, QMessageBox, QScrollArea, QApplication
)
from PyQt5.QtGui import QPixmap, QTextCursor, QPalette, QColor

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

from llama_cpp_agent import LlamaCppAgent

from diffusers import StableDiffusionPipeline

try:
    from PyQt5.QtCore import qRegisterMetaType
    from PyQt5.QtGui import QTextCursor
    qRegisterMetaType(QTextCursor, "QTextCursor")
except Exception as e:
    print(f"Warning qRegisterMetaType QTextCursor skipped: {e}")


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
        self.last_active_time = time.time()
        self.max_inactive_duration = 30

    def run(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            while self.running:
                self.mutex.lock()
                paused = self.is_paused
                self.mutex.unlock()

                if paused:
                    time.sleep(0.5)
                    continue

                if time.time() - self.last_active_time > self.max_inactive_duration:
                    self.pause()
                    continue

                try:
                    audio = self.recognizer.listen(source, timeout=10)

                    if self.is_paused:
                        continue

                    text = self.recognizer.recognize_google(audio, language="fr-FR").lower()
                    self.last_active_time = time.time()

                    if "alice" in text:
                        cleaned_text = text.split("alice", 1)[-1].strip()
                        if cleaned_text:
                            self.is_processing_response = True
                            self.result_signal.emit(cleaned_text)
                except:
                    pass
                finally:
                    self.is_processing_response = False

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False
        self.last_active_time = time.time()

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


class RunnableFunc(QRunnable):
    def __init__(self, func):
        super().__init__()
        self.func = func

    def run(self):
        self.func()


def load_config():
    if os.path.exists("config.json"):
        with open("config.json", "r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                pass
    return {}


def save_config(config):
    with open("config.json", "w") as file:
        json.dump(config, file, indent=4)


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
        self.is_user_speaking = True

        self.setup_ui()
        self.apply_dark_theme()

        last_model = self.config.get("last_model", "Mistral-7B-Instruct")
        index = self.model_selector.findText(last_model)
        self.model_selector.setCurrentIndex(index if index != -1 else 0)
        self.voice_checkbox.setChecked(self.config.get("voice_enabled", True))

    def apply_dark_theme(self):
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(30, 30, 30))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)

        self.setPalette(dark_palette)
        QApplication.setPalette(dark_palette)

        self.setStyleSheet("""
            QTextEdit, QLineEdit, QLabel {
                color: white;
                background-color: #1e1e1e;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: white;
                font-weight: bold;
                padding: 6px;
            }
            QComboBox, QCheckBox {
                color: white;
                background-color: #2e2e2e;
            }
        """)

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
        self.voice_button.setStyleSheet("background-color: lightcoral; font-weight: bold;")

        self.language_selector = QComboBox()
        self.language_selector.addItems(["Python", "JavaScript", "C++", "HTML", "SQL"])
        control_layout.addWidget(self.language_selector)

        self.force_code_button = QPushButton("Tester Code Vocal")
        self.force_code_button.clicked.connect(lambda: self.on_text_recognized("alice crée un code python pour afficher l'heure"))
        control_layout.addWidget(self.force_code_button)

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

        self.setLayout(layout)

    def toggle_voice(self, state):
        self.config["voice_enabled"] = bool(state)
        save_config(self.config)

    def toggle_voice_input(self):
        self.voice_input_enabled = not self.voice_input_enabled
        if self.voice_input_enabled:
            self.voice_button.setText("🎤 Micro: ON")
            self.voice_button.setStyleSheet("background-color: lightgreen; font-weight: bold;")
            if not self.voice_recognition_thread.isRunning():
                self.voice_recognition_thread.start()
            else:
                self.voice_recognition_thread.resume()
        else:
            self.voice_button.setText("🎤 Micro: OFF")
            self.voice_button.setStyleSheet("background-color: lightcoral; font-weight: bold;")
            self.voice_recognition_thread.stop()

    def load_model(self, model_name):
        self.config["last_model"] = model_name
        save_config(self.config)
        try:
            self.agent = LlamaCppAgent(self.model_paths, selected_model=model_name)
            self.voice_recognition_thread.agent = self.agent
        except Exception as e:
            print(f"[ERREUR CHARGEMENT MODÈLE] : {e}")

    def on_text_recognized(self, text):
        print("[DEBUG] Texte brut reconnu :", text)
        if self.is_user_speaking:
            self.response_box.append(f"<b style='color: lightblue'>[Vous]</b> {text}")

            self.input_box.setText(text)
            self.is_user_speaking = False
            self.voice_recognition_thread.pause()
            text_lower = text.lower()

            if any(kw in text_lower for kw in ["image", "dessine", "dessin", "photo", "génère une image"]):
                self.generate_image_from_text(text)
            elif any(kw in text_lower for kw in ["code", "fonction", "script", "programme", "algo", "python", "afficher", "fonctionne"]):
                self.generate_code_from_text(text)
            else:
                self.generate_model_response(text)

    def generate_code_from_text(self, text):
        print("[DEBUG] >>> Appel de generate_code_from_text() avec :", text)
        self.response_box.append("<b style='color: lightgreen'>[Alice]</b> Je génère un code... ⌨️")
        QApplication.processEvents()

        def run():
            language = self.language_selector.currentText()
            code_response = self.agent.generate_code(text, language=language)
            print("[DEBUG] Code brut retourné :", repr(code_response))

            match = re.search(r"```(?:\w+)?\s*(.*?)```", code_response, re.DOTALL)
            extracted_code = match.group(1).strip() if match else code_response.strip()

            try:
                lexer = get_lexer_by_name(language.lower(), stripall=True)
            except Exception:
                lexer = get_lexer_by_name("text", stripall=True)

            formatter = HtmlFormatter(style="monokai", noclasses=True)
            highlighted = highlight(extracted_code, lexer, formatter)

            self.response_box.append('<b style="color: lightgreen">[Alice]</b> Voici le code généré :<br>')

            code_html = f'''
            <div style="
                background-color: #1e1e1e;
                color: white;
                padding: 12px;
                border-radius: 10px;
                margin-top: 5px;
                margin-bottom: 15px;
                font-family: Consolas, monospace;
                font-size: 14px;
            ">
            {highlighted}
            </div>
            '''
            self.response_box.append(code_html)
            self.response_box.append('<div style="background: none; color: white; margin: 5px 0;"></div>')

            if self.voice_checkbox.isChecked():
                self.agent.speak("Voici le code généré.")
            self.voice_recognition_thread.resume()

        QThreadPool.globalInstance().start(RunnableFunc(run))


    def generate_image_from_text(self, text):
        self.response_box.append(f"<b>[Vous]</b> {text}")
        self.response_box.append("<b>[Alice]</b> Je vais générer une image... Veuillez patienter ⏳")
        QApplication.processEvents()

        def run():
            print("[DEBUG] → Début de run() image")
            result = self.agent.generate_image(text)
            print("[DEBUG] >>> resultat chemin generation image :", result)
            image_path = result.split("#image")[-1].strip() if "#image" in result else None
            print("[DEBUG] >>> resultat chemin image_path :", image_path)

            self.image_path_result = image_path  # Stocke dans l'instance
            QTimer.singleShot(0, self.display_generated_image)  # Appel Qt-thread safe

        QThreadPool.globalInstance().start(RunnableFunc(run))


    def display_generated_image(self):
        print("[DEBUG] → Entrée dans display_generated_image()")
        image_path = getattr(self, 'image_path_result', None)
        if image_path and os.path.exists(image_path):
            full_path = os.path.abspath(image_path).replace("\\", "/")
            pixmap = QPixmap(full_path)
            print(f"[DEBUG] Chargement pixmap depuis : {full_path} | Null ? {pixmap.isNull()}")

            if not pixmap.isNull():
                img_html = f'''
                <div style="background-color: #1e1e1e; padding: 10px; border-radius: 8px; margin-bottom: 10px;">
                    <img src="file:///{full_path}" width="350">
                </div>
                '''
                self.response_box.append("<b>[Alice]</b> Voici votre image générée :")
                self.response_box.append(img_html)
            else:
                self.response_box.append("<b>[Alice]</b> L'image est invalide ou corrompue.")
        else:
            self.response_box.append("<b>[Alice]</b> Erreur : image introuvable.")

        self.voice_recognition_thread.resume()



    def generate_model_response(self, prompt):
        print("[DEBUG] >>> Appel de generate_model_response() avec :", prompt)
        self.waiting_label.setVisible(True)
        QApplication.processEvents()

        def run():
            response = self.agent.generate(prompt)
            print("[DEBUG] Réponse brute :", response)
            self.response_box.append(f"<b>[Alice]</b> <span style='color: black;'>{escape(response)}</span>")
            self.waiting_label.setVisible(False)
            if self.voice_checkbox.isChecked():
                self.agent.speak(response)
            self.is_user_speaking = True
            self.voice_recognition_thread.resume()

        QThreadPool.globalInstance().start(RunnableFunc(run))


    def send_prompt(self):
        text = self.input_box.toPlainText().strip()
        if text:
            self.response_box.append(f"<b style='color: lightblue'>[Vous]</b> {text}")
            text_lower = text.lower()
            if any(kw in text_lower for kw in ["image", "dessine", "dessin", "photo", "génère une image"]):
                self.generate_image_from_text(text)
            elif any(kw in text_lower for kw in ["code", "fonction", "script", "programme", "algo", "python", "afficher", "fonctionne"]):
                self.generate_code_from_text(text)
            else:
                self.generate_model_response(text)

    def save_prompt(self):
        prompt = self.input_box.toPlainText().strip()
        if prompt:
            self.agent.save_to_memory(prompt, "Interaction sauvegardée manuellement.")
            self.response_box.append("[✔] Interaction sauvegardée.")

    def open_memory_window(self):
        from gui.memory_window import MemoryViewer
        mem_window = MemoryViewer(self.agent)
        mem_window.show()

    def closeEvent(self, event):
        self.voice_recognition_thread.stop()
        event.accept()

    def copy_last_code(self):
        cursor = self.response_box.textCursor()
        cursor.select(QTextCursor.Document)
        pyperclip.copy(cursor.selectedText())
        QMessageBox.information(self, "Copié", "Code copié dans le presse-papiers.")
