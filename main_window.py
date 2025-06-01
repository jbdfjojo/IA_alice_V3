import os
import json
import time
import psutil 
import pyttsx3
import speech_recognition as sr
import pyperclip
import re
from html import escape
from queue import Queue

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMutex, QThreadPool, QRunnable, QTimer, QMetaObject, Q_ARG, pyqtSlot, QSize
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel,
    QCheckBox, QComboBox, QMessageBox, QScrollArea, QApplication
)
from PyQt5.QtGui import QPixmap, QTextCursor, QPalette, QColor, QFont, QMovie

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from codeManager.codeManager import codeManager
from imagesManager.image_manager import Image_Manager
from llama_cpp_agent import LlamaCppAgent

from diffusers import StableDiffusionPipeline

try:
    from PyQt5.QtCore import qRegisterMetaType
    from PyQt5.QtGui import QTextCursor
    qRegisterMetaType(QTextCursor, "QTextCursor")
except Exception as e:
    print(f"Warning qRegisterMetaType QTextCursor skipped: {e}")

# Ajout d'une méthode utilitaire pour créer un QLabel stylé
class StyledLabel(QLabel):
    def __init__(self, html):
        super().__init__(html)
        self.setWordWrap(True)
        self.setStyleSheet("margin-top: 2px; margin-bottom: 2px; line-height: 1.2em; padding: 0;")

class InputTextEdit(QTextEdit):
    def __init__(self, parent=None, submit_callback=None):
        super().__init__(parent)
        self.submit_callback = submit_callback

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return and not event.modifiers() & Qt.ShiftModifier:
            if self.submit_callback:
                self.submit_callback()
            event.accept()  # empêche le retour à la ligne
        else:
            super().keyPressEvent(event)
class VoiceRecognitionThread(QThread):
    result_signal = pyqtSignal(str)

    def __init__(self, images):
        super().__init__()
        self.images = images
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
    def __init__(self, model_paths: dict, images):
        super().__init__()

        self.setWindowTitle("Alice - Interface IA")
        self.setGeometry(100, 100, 800, 600)

        self.model_paths = model_paths
        self.images = images
        self.config = load_config()

        self.voice_input_enabled = False
        self.voice_recognition_thread = VoiceRecognitionThread(self.images)
        self.voice_recognition_thread.result_signal.connect(self.on_text_recognized)
        self.is_user_speaking = True

        self.llama_agent = LlamaCppAgent(self.model_paths)  # ✅ Ajout ici
        self.codeManager = codeManager(parent=self, agent=self.llama_agent)  # ✅ Maintenant c’est bon
        self.image_manager = Image_Manager(parent=self, agent=self.llama_agent)

        self.setup_ui()
        self.apply_dark_theme()


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
            QWidget {
                        background-color: #121212;
                        color: #f0f0f0;
                        font-family: Consolas, monospace;
                        font-size: 14px;
                    }
                    QScrollArea {
                        background-color: #121212;
                    }
                    QTextEdit {
                        background-color: #1e1e1e;
                        color: #f0f0f0;
                        border: 1px solid #333;
                        border-radius: 5px;
                        padding: 6px;
                    }
                    QPushButton {
                        background-color: #2d2d2d;
                        color: white;
                        border: 1px solid #444;
                        padding: 6px;
                        border-radius: 6px;
                    }
                    QPushButton:hover {
                        background-color: #3a3a3a;
                    }
                    QLabel {
                        color: #f0f0f0;
                    }
                    QComboBox {
                        background-color: #1e1e1e;
                        color: #f0f0f0;
                        border: 1px solid #333;
                        padding: 4px;
                    }
                    QCheckBox {
                        color: #f0f0f0;
                    }
                """)

    def setup_ui(self):
        layout = QVBoxLayout()

        # --- Ligne du haut : boutons et sélecteurs ---
        top_controls = QHBoxLayout()

        # 1. Choix modèle  
        self.model_selector = QComboBox()
        self.model_selector.addItems(self.model_paths.keys())
        self.model_selector.currentTextChanged.connect(self.load_model)
        top_controls.addWidget(self.model_selector)

        # 2. Checkbox voix  
        self.voice_checkbox = QCheckBox("Voix")
        self.voice_checkbox.stateChanged.connect(self.toggle_voice)
        top_controls.addWidget(self.voice_checkbox)

        # 3. Micro On/Off  
        self.voice_button = QPushButton("🎤 Micro: OFF")
        self.voice_button.setCheckable(True)
        self.voice_button.clicked.connect(self.toggle_voice_input)
        self.voice_button.setStyleSheet("background-color: lightcoral; font-weight: bold;")
        top_controls.addWidget(self.voice_button)

        # 4. Choix du langage  
        self.language_selector = QComboBox()
        self.language_selector.addItems(["Python", "JavaScript", "C++", "HTML", "SQL"])
        top_controls.addWidget(self.language_selector)

        # 5. Bouton Images  
        self.image_manager_button = QPushButton("Images")
        self.image_manager_button.clicked.connect(self.open_image_manager)
        top_controls.addWidget(self.image_manager_button)

        # 6. Bouton Mémoire  
        self.memory_button = QPushButton("Mémoire")
        self.memory_button.clicked.connect(self.open_memory_window)
        top_controls.addWidget(self.memory_button)

        # 7. Bouton Sauvegarder  
        self.save_button = QPushButton("Sauvegarder")
        self.save_button.clicked.connect(self.save_prompt)
        top_controls.addWidget(self.save_button)

        layout.addLayout(top_controls)

        # --- Milieu : réponse IA (grand champ avec scroll + police Times New Roman 14px) ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        
        self.scroll_layout.setAlignment(Qt.AlignTop)  # 🔥 ANCRAGE EN HAUT  
        self.scroll_layout.setSpacing(0)               # Pas d'espace entre les éléments  
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)  # Pas de marges
        
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setFont(QFont("Times New Roman", 14))
        
        layout.addWidget(self.scroll_area)

        # --- Zone d'attente centrée avec spinner + texte ---
        self.waiting_container = QWidget()
        self.waiting_container.setVisible(False)
        waiting_layout = QHBoxLayout(self.waiting_container)
        waiting_layout.setAlignment(Qt.AlignCenter)

        # Spinner GIF  
        self.spinner_label = QLabel()
        self.spinner_movie = QMovie("assets/spinner_2.gif")
        self.spinner_movie.setScaledSize(QSize(24, 24))  # 🔹 Taille réduite du spinner  
        if not self.spinner_movie.isValid():
            print("❌ Le fichier spinner_2.gif est introuvable ou invalide.")
        else:
            self.spinner_label.setMovie(self.spinner_movie)
        self.spinner_label.setVisible(True)

        # Texte à côté du spinner  
        self.waiting_label = QLabel("Alice réfléchit...")
        self.waiting_label.setStyleSheet("font-style: italic; font-size: 14px;")
        self.waiting_label.setAlignment(Qt.AlignLeft)

        # Ajouter les deux côte à côte  
        waiting_layout.addWidget(self.spinner_label)
        waiting_layout.addWidget(self.waiting_label)

        layout.addWidget(self.waiting_container)

        # --- Bas : champ utilisateur réduit + bouton Envoyer ---
        bottom_layout = QHBoxLayout()

        self.input_box = InputTextEdit(submit_callback=self.send_prompt)
        self.input_box.setPlaceholderText("Entrez votre message ici...")
        self.input_box.setFont(QFont("Times New Roman", 14))
        self.input_box.setFixedHeight(self.height() // 6)  # ~1/3 de la zone réponse  
        bottom_layout.addWidget(self.input_box)

        self.send_button = QPushButton("Envoyer")
        self.send_button.clicked.connect(self.send_prompt)
        self.send_button.setFixedHeight(40)
        bottom_layout.addWidget(self.send_button)

        layout.addLayout(bottom_layout)

        # --- Appliquer le layout final ---
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
            self.images = LlamaCppAgent(self.model_paths, selected_model=model_name)
            self.voice_recognition_thread.images = self.images
        except Exception as e:
            print(f"[ERREUR CHARGEMENT MODÈLE] : {e}")

    def on_text_recognized(self, text):
        print("[DEBUG] Texte brut reconnu :", text)
        if self.is_user_speaking:
            self.scroll_layout.addWidget(StyledLabel(f"<b style='color: lightblue'>[Vous]</b> {text}"))

            self.input_box.setText(text)
            self.is_user_speaking = False
            self.voice_recognition_thread.pause()
            text_lower = text.lower()

            if any(kw in text_lower for kw in ["image", "dessine", "dessin", "photo", "génère une image"]):
                self.image_manager.generate_image_from_text(text)
            elif any(kw in text_lower for kw in ["code", "fonction", "script", "programme", "algo", "python", "afficher", "fonctionne"]):
                self.generate_code_from_text(text)
            else:
                self.generate_model_response(text)

    def generate_model_response(self, prompt):
        self.set_waiting_message("Alice réfléchit...")
        print("[DEBUG] >>> Appel de generate_model_response() avec :", prompt)

        def run():
            response = self.images.generate(prompt)
            print("[DEBUG] Réponse brute :", response)

            # Passage au thread principal pour mise à jour UI
            QMetaObject.invokeMethod(
                self,
                "display_model_response",
                Qt.QueuedConnection,
                Q_ARG(str, response)
            )

        QThreadPool.globalInstance().start(RunnableFunc(run))

    @pyqtSlot(str)
    def display_model_response(self, response):
        self.clear_waiting_message()
        self.spinner_movie.stop()
        self.spinner_label.setVisible(False)

        label = StyledLabel(f"<b style='color: lightgreen'>[Alice]</b> <span style='color: white;'>{escape(response)}</span>")
        self.scroll_layout.addWidget(label)
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()))

        if self.voice_checkbox.isChecked():
            self.images.speak(response)

        self.is_user_speaking = True
        self.voice_recognition_thread.resume()



    def send_prompt(self):
        text = self.input_box.toPlainText().strip()
        if not text:
            return

        user_label = StyledLabel(f"<b style='color: lightblue'>[Vous]</b> {escape(text)}")
        self.scroll_layout.addWidget(user_label)
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()))

        self.input_box.clear()

        text_lower = text.lower()
        if any(kw in text_lower for kw in ["image", "dessine", "dessin", "photo", "génère une image"]):
            self.image_manager.generate_image_from_text(text)
        elif any(kw in text_lower for kw in ["code", "fonction", "script", "programme", "algo", "python", "afficher", "fonctionne"]):
            self.codeManager.generate_code_from_text(text)

        else:
            self.generate_model_response(text)


    def save_prompt(self):
        prompt = self.input_box.toPlainText().strip()
        if prompt:
            self.images.save_to_memory(prompt, "Interaction sauvegardée manuellement.")
            self.response_box.append("[✔] Interaction sauvegardée.")

    def open_memory_window(self):
        from memoire.memory_window import MemoryViewer
        self.mem_window = MemoryViewer(self.images, style_sheet=self.styleSheet())  # <-- garde une référence
        self.mem_window.show()

    def closeEvent(self, event):
        self.voice_recognition_thread.stop()
        event.accept()

    def copy_last_code(self):
        cursor = self.response_box.textCursor()
        cursor.select(QTextCursor.Document)
        pyperclip.copy(cursor.selectedText())
        QMessageBox.information(self, "Copié", "Code copié dans le presse-papiers.")

    def open_image_manager(self):
        self.image_window = Image_Manager(style_sheet=self.styleSheet())
        self.image_window.show()

    def set_waiting_message(self, message: str):
        self.waiting_label.setText(message)
        self.spinner_movie.start()
        self.waiting_container.setVisible(True)
        QApplication.processEvents()

    def clear_waiting_message(self):
        self.spinner_movie.stop()
        self.waiting_container.setVisible(False)

    def add_code_block(self, highlighted_code: str, raw_code: str):
        container = QWidget()
        container_layout = QVBoxLayout(container)

        code_display = QTextEdit()
        code_display.setReadOnly(True)
        code_display.setTextInteractionFlags(Qt.TextSelectableByMouse)
        code_display.setHtml(f"""
            <div style="font-family: Consolas; font-size: 13px; line-height: 1.2em; margin:0; padding:0;">
                {highlighted_code}
            </div>
        """)

        container_layout.addWidget(code_display)

        copy_btn = QPushButton("📋 Copier le code")
        copy_btn.setFixedWidth(150)
        copy_btn.clicked.connect(lambda: pyperclip.copy(raw_code))
        copy_btn.setStyleSheet("margin-top: 5px; margin-bottom: 10px;")
        container_layout.addWidget(copy_btn, alignment=Qt.AlignCenter)

        self.scroll_layout.addWidget(container)


    def afficher_erreur(self, message):
        self.scroll_layout.addWidget(StyledLabel(
            f"<span style='color:red'><b>[ERREUR]</b> {message}</span>"
        ))

    def handle_resource_alert(self, overloaded, cpu, ram):
        if overloaded:
            alert = f"<b>[Alerte système]</b> CPU: {cpu:.1f}%, RAM: {ram:.1f}% ➜ surcharge détectée ⚠️"
            self.scroll_layout.addWidget(QLabel(alert))
            print("[ALERTE] Ressources critiques détectées.")
        else:
            print(f"[INFO] Ressources OK — CPU: {cpu:.1f}%, RAM: {ram:.1f}%")



