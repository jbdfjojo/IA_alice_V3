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
from interfaceManager.interface_manager import InterfaceManager
from gestionnaire_ressources.resource_manager import IAResourceManager
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

        self.model_paths = model_paths
        self.images = images
        self.config = load_config()

        self.voice_input_enabled = False
        self.voice_recognition_thread = VoiceRecognitionThread(self.images)
        self.voice_recognition_thread.result_signal.connect(self.on_text_recognized)
        self.is_user_speaking = True

        self.llama_agent = LlamaCppAgent(self.model_paths)
        self.codeManager = codeManager(parent=self, agent=self.llama_agent)
        self.image_manager = Image_Manager(parent=self, agent=self.llama_agent)

        # Initialisation du gestionnaire de ressources IA
        self.resource_manager = IAResourceManager(self.llama_agent, max_threads=3, max_memory_gb=24)
        self.resource_manager.overload_signal.connect(self.handle_resource_overload)
        self.resource_manager.ready_signal.connect(self.handle_resource_ready)


        self.resize(800, 500)  # 🖥️ Taille de départ de la fenêtre

        self.interface = InterfaceManager(self)
        self.last_response = ""  # 🔐 Pour initialiser
        self.last_prompt = ""  # 🧠 Pour #save

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

        self.last_prompt = prompt  # 🧠 Mémorise le prompt pour #save

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

        # Soumet la tâche au gestionnaire de ressources
        if not self.resource_manager.submit(run):
            self.clear_waiting_message()
            self.scroll_layout.addWidget(StyledLabel("<span style='color:red'>[!] Trop de charge système, réessayez plus tard.</span>"))
            print("[INFO] Requête refusée: surcharge CPU ou RAM")


    @pyqtSlot(str)
    def display_model_response(self, response):
        self.clear_waiting_message()
        self.spinner_movie.stop()
        self.spinner_label.setVisible(False)
        self.save_button.setEnabled(True)

        # 🔐 Sauvegarder les derniers prompt/réponse
        self.last_response = response.strip()

        label = StyledLabel(f"<b style='color: lightgreen'>[Alice]</b> <span style='color: white;'>{escape(response)}</span>")
        self.scroll_layout.addWidget(label)
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()))

        if self.voice_checkbox.isChecked():
            self.images.speak(response)

        # ✅ Sauvegarde automatique si #save dans le prompt
        if "#save" in self.last_prompt.lower():
            print("🔄 Détection de #save dans le prompt -> lancement sauvegarde")
            self.save_prompt()

        self.is_user_speaking = True
        self.voice_recognition_thread.resume()




    def send_prompt(self):
        text = self.input_box.toPlainText().strip()
        if not text:
            return

        # Si l'utilisateur tape #save → déclencher la sauvegarde
        if "#save" in text:
            self.save_prompt()
            self.input_box.clear()
            return

        # Sauvegarde du prompt actuel pour usage ultérieur
        self.last_prompt = text

        # Affichage du message utilisateur dans l'UI
        user_label = StyledLabel(f"<b style='color: lightblue'>[Vous]</b> {escape(text)}")
        self.scroll_layout.addWidget(user_label)
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()))
        self.last_prompt = text  # 🧠 Stocke le prompt avant de vider
        self.input_box.clear()

        text_lower = text.lower()
        if any(kw in text_lower for kw in ["image", "dessine", "dessin", "photo", "génère une image"]):
            self.image_manager.generate_image_from_text(text)
        elif any(kw in text_lower for kw in ["code", "fonction", "script", "programme", "algo", "python", "afficher", "fonctionne"]):
            self.codeManager.generate_code_from_text(text)
        else:
            self.generate_model_response(text)


    def save_prompt(self):
        prompt = self.last_prompt.strip()
        response = self.last_response.strip()

        # 🔍 Si vide, on tente de lire depuis l'UI
        if not prompt:
            prompt = self.input_box.toPlainText().strip()

        print("📝 [Sauvegarde demandée]")
        print("Prompt :", prompt)
        print("Réponse :", response)

        if not prompt or not response:
            self.scroll_layout.addWidget(StyledLabel("<span style='color:red'>[!] Aucune réponse à sauvegarder.</span>"))
            return

        from memoireManager.memory_window import MemoryViewer
        mem = MemoryViewer(memory_data=None)
        mem.save_to_database(prompt, response)
        mem.close()

        self.scroll_layout.addWidget(StyledLabel("<span style='color: lightgreen'>[✔] Interaction sauvegardée.</span>"))



    def open_memory_window(self):
        from memoireManager.memory_window import MemoryViewer
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

        # 🔧 Nettoyage du code brut pour éviter les ```python
        clean_code = raw_code.strip()
        if clean_code.startswith("```"):
            # Supprime les balises markdown
            clean_code = re.sub(r"^```[a-zA-Z]*\n?", "", clean_code)
            clean_code = re.sub(r"```$", "", clean_code).strip()

        self.last_response = clean_code  # ✅ Code propre à sauvegarder
        self.last_prompt = self.input_box.toPlainText().strip() or "Code généré"

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
        copy_btn.clicked.connect(lambda: pyperclip.copy(clean_code))
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

    def handle_resource_overload(self, message):
        self.handle_resource_alert(True, 0, 0)
        self.scroll_layout.addWidget(StyledLabel(f"<span style='color: orange; font-weight:bold;'>[ALERTE]</span> {message}"))
        print("[ALERTE] " + message)

    def handle_resource_ready(self):
        self.handle_resource_alert(False, 0, 0)
        # Ici tu peux gérer la levée d’alerte si besoin (nettoyer UI par ex)
