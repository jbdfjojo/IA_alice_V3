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
        super().__init__()  # ← OBLIGATOIRE
        self.parent = parent
        self.agent = agent

    def generate_code_from_text(self, text):
        self.parent.set_waiting_message("Alice réfléchit...")
        self.parent.spinner_label.setVisible(True)
        self.parent.spinner_movie.start()
        self.parent.waiting_label.setVisible(True)
        print("[DEBUG] >>> Appel de generate_code_from_text() avec :", text)

        # Message d'attente
        self.parent.scroll_layout.addWidget(StyledLabel("<b style='color: lightgreen'>[Alice]</b> Je génère un code... ⌨️"))
        QApplication.processEvents()

        def run():
            print("[DEBUG] → Début du thread de génération de code")
            language = self.parent.language_selector.currentText()
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

            self.parent.clear_waiting_message()
            self.parent.spinner_movie.stop()
            self.parent.spinner_label.setVisible(False)

            # Mise à jour de l'interface (Qt thread-safe)
            QMetaObject.invokeMethod(self, "append_code_block", Qt.QueuedConnection,
                                    Q_ARG(str, highlighted),
                                    Q_ARG(str, extracted_code))
        QTimer.singleShot(100, lambda:self.parent.scroll_area.verticalScrollBar().setValue(self.parent.scroll_area.verticalScrollBar().maximum()))

        QThreadPool.globalInstance().start(RunnableFunc(run))


    @pyqtSlot(str, str)
    def append_code_block(self, highlighted_code, raw_code):
        title = StyledLabel("<b style='color: lightgreen'>[Alice]</b> Voici le code généré :")
        self.parent.scroll_layout.addWidget(title)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(2)
        container.setStyleSheet("background-color: #1e1e1e; border-radius: 4px; padding: 0; margin: 0;")
        
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

        # Nettoyage du HTML : suppression des <pre> extérieurs inutiles
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


        # ✅ Mémorisation pour bouton "Sauvegarder"
        self.parent.last_response = raw_code
        self.parent.last_prompt = self.parent.input_box.toPlainText().strip() or "Code généré"

        if self.parent.voice_checkbox.isChecked():
            self.parent.images.speak("Voici le code généré.")
        self.parent.voice_recognition_thread.resume()


