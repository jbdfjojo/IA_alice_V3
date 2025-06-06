# --- Standard library ---
import os
import json
import time
import re
import psutil
import pyperclip
from html import escape

# --- Third-party libraries ---
import speech_recognition as sr
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from gestionnaire_ressources.resource_manager import IAResourceManager

# --- PyQt5 ---
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QMutex, QThreadPool, QRunnable, QTimer,
    QMetaObject, Q_ARG, pyqtSlot, QObject
)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel,
    QCheckBox, QComboBox, QMessageBox, QScrollArea, QApplication
)
from PyQt5.QtGui import QPixmap, QTextCursor, QPalette, QColor, QFont, QMovie

from utils.utils import RunnableFunc, StyledLabel

# --- Projet ---
from llama_cpp_agent import LlamaCppAgent  # utilisé pour self.agent
# from diffusers import StableDiffusionPipeline  # si inutilisé ici, peut être commenté

# --- Qt meta-type registration (facultatif) ---
try:
    from PyQt5.QtCore import qRegisterMetaType
    qRegisterMetaType(QTextCursor, "QTextCursor")
except Exception as e:
    print(f"Warning qRegisterMetaType QTextCursor skipped: {e}")


class codeManager(QObject):
    def __init__(self, parent=None, agent=None):
        super().__init__()  # Obligatoire
        self.parent = parent
        self.agent = agent
        
        # Initialisation du gestionnaire de ressources IA
        self.resource_manager = IAResourceManager(self.agent, max_threads=3, max_memory_gb=24)
        self.resource_manager.overload_signal.connect(self.parent.handle_resource_overload)
        self.resource_manager.ready_signal.connect(self.parent.handle_resource_ready)


    def generate_code_from_text(self, text):
        self.parent.set_waiting_message("Alice réfléchit...")
        self.parent.spinner_label.setVisible(True)
        self.parent.spinner_movie.start()
        self.parent.waiting_label.setVisible(True)
        print("[DEBUG] >>> Appel de generate_code_from_text() avec :", text)

        # Message d'attente affiché dans l'interface
        self.parent.scroll_layout.addWidget(
            StyledLabel("<b style='color: lightgreen'>[Alice]</b> Je génère un code... ⌨️")
        )
        QApplication.processEvents()

        if not self.resource_manager.ressources_disponibles():
            print("[INFO] Requête refusée: surcharge CPU ou RAM")
            return "Les ressources système sont surchargées. Veuillez réessayer plus tard."

        def run():
            print("[DEBUG] → Début du thread de génération de code")
            language = self.parent.language_selector.currentText()
            code_response = self.agent.generate_code(text, language=language)
            print("[DEBUG] Code brut retourné :", repr(code_response))

            # Extraction du code entre balises ```...```
            match = re.search(r"```(?:\w+)?\s*(.*?)```", code_response, re.DOTALL)
            extracted_code = match.group(1).strip() if match else code_response.strip()

            # Choix du lexer Pygments selon langage
            try:
                lexer = get_lexer_by_name(language.lower(), stripall=True)
            except Exception:
                lexer = get_lexer_by_name("text", stripall=True)

            formatter = HtmlFormatter(style="monokai", noclasses=True)
            highlighted = highlight(extracted_code, lexer, formatter)

            # Arrêt message attente et spinner
            self.parent.clear_waiting_message()
            self.parent.spinner_movie.stop()
            self.parent.spinner_label.setVisible(False)

            # Mise à jour de l'interface (Qt thread-safe)
            QMetaObject.invokeMethod(
                self,
                "append_code_block",
                Qt.QueuedConnection,
                Q_ARG(str, highlighted),
                Q_ARG(str, extracted_code)
            )

        # Scroll vers le bas léger pour lisibilité
        QTimer.singleShot(100, lambda: self.parent.scroll_area.verticalScrollBar().setValue(
            self.parent.scroll_area.verticalScrollBar().maximum()))

        # Lancement thread via QRunnable
        QThreadPool.globalInstance().start(RunnableFunc(run))


    @pyqtSlot(str, str)
    def append_code_block(self, highlighted_code, raw_code):
        title = StyledLabel("<b style='color: lightgreen'>[Alice]</b> Voici le code généré :")
        self.parent.scroll_layout.addWidget(title)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(2)
        container.setStyleSheet(
            "background-color: #1e1e1e; border-radius: 4px; padding: 0; margin: 0;"
        )

        code_display = QTextEdit()
        code_display.setReadOnly(True)
        code_display.setTextInteractionFlags(Qt.TextSelectableByMouse)
        code_display.setStyleSheet("""
            background-color: #1e1e1e;
            color: white;
            border: none;
            padding: 4px;
            margin: 0;
            font-family: Consolas, monospace;
            font-size: 13px;
            line-height: 1.2em;
        """)
        code_display.setMinimumHeight(50)
        code_display.setMaximumHeight(200)
        code_display.setMaximumWidth(450)
        code_display.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        code_display.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Nettoyage du HTML pour retirer <pre> inutiles
        cleaned_html = re.sub(r"</?pre[^>]*>", "", highlighted_code, flags=re.IGNORECASE)
        code_display.setHtml(f"<div style='line-height: 1.2em; font-family: Consolas, monospace;'>{cleaned_html}</div>")

        container_layout.addWidget(code_display)

        copy_btn = QPushButton("📋 Copier le code")
        copy_btn.setFixedWidth(160)
        copy_btn.clicked.connect(lambda: pyperclip.copy(raw_code))
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: white;
                border-radius: 6px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)

        container_layout.addWidget(copy_btn, alignment=Qt.AlignRight)
        self.parent.save_button.setEnabled(True)

        self.parent.scroll_layout.addWidget(container)
        QTimer.singleShot(100, lambda: self.parent.scroll_area.verticalScrollBar().setValue(
            self.parent.scroll_area.verticalScrollBar().maximum()))

        # ✅ Stockage du dernier prompt / réponse pour bouton sauvegarder
        self.parent.last_response = raw_code
        self.parent.last_prompt = self.parent.input_box.toPlainText().strip() or "Code généré"

        # Synthèse vocale si activée
        if self.parent.voice_checkbox.isChecked():
            self.parent.images.speak("Voici le code généré.")

        # Reprise reconnaissance vocale si thread prévu
        self.parent.voice_recognition_thread.resume()

