# --- Standard library ---
import os
import json
import time
import re
import psutil
import pyperclip
import shutil  # Ajout pour deplacer les fichiers
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
    QCheckBox, QComboBox, QMessageBox, QScrollArea, QApplication, QDialog, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QTextCursor, QPalette, QColor, QFont, QMovie

from utils.utils import RunnableFunc, StyledLabel

# --- Projet ---
from llama_cpp_agent import LlamaCppAgent

try:
    from PyQt5.QtCore import qRegisterMetaType
    qRegisterMetaType(QTextCursor, "QTextCursor")
except Exception as e:
    print(f"Warning qRegisterMetaType QTextCursor skipped: {e}")


class ImageViewer(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image en grand")
        self.setWindowModality(Qt.ApplicationModal)
        layout = QVBoxLayout(self)
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        pixmap = QPixmap(image_path)
        screen_size = QApplication.primaryScreen().size()
        max_width = screen_size.width() * 0.8
        max_height = screen_size.height() * 0.8
        pixmap = pixmap.scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(pixmap)
        self.resize(pixmap.size())


class Image_Manager(QWidget):
    def __init__(self, images_folder="imagesManager/views_images", agent=None, style_sheet=None, parent=None):
        super().__init__(parent)
        self.images_folder = images_folder
        self.parent = parent
        self.agent = agent

        if style_sheet:
            self.setStyleSheet(style_sheet)

        self.setWindowTitle("Gestionnaire d'images")
        self.layout = QVBoxLayout(self)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignTop)

        self.scroll.setWidget(self.container)
        self.layout.addWidget(self.scroll)

        # Initialisation du gestionnaire de ressources IA
        self.resource_manager = IAResourceManager(self.agent, max_threads=3, max_memory_gb=24)
        self.resource_manager.overload_signal.connect(self.parent.handle_resource_overload)
        self.resource_manager.ready_signal.connect(self.parent.handle_resource_ready)

        self.load_images()

    def load_images(self):
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not os.path.exists(self.images_folder):
            QMessageBox.warning(self, "Dossier non trouv\u00e9", f"Le dossier {self.images_folder} n'existe pas.")
            return

        images_files = [f for f in os.listdir(self.images_folder)
                        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]

        for img_file in images_files:
            full_path = os.path.join(self.images_folder, img_file)
            self.add_image_widget(full_path)

    def add_image_widget(self, image_path):
        widget = QWidget()
        h_layout = QHBoxLayout(widget)
        h_layout.setContentsMargins(5, 5, 5, 5)

        label = QLabel()
        pixmap = QPixmap(image_path)
        pixmap = pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(pixmap)
        label.setFixedSize(120, 120)
        label.setCursor(Qt.PointingHandCursor)
        label.mousePressEvent = lambda event, p=image_path: self.show_image(p)
        h_layout.addWidget(label)

        name_label = QLabel(os.path.basename(image_path))
        name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        h_layout.addWidget(name_label)

        btn_delete = QPushButton("Supprimer")
        btn_delete.clicked.connect(lambda _, p=image_path, w=widget: self.delete_image(p, w))
        h_layout.addWidget(btn_delete)

        self.container_layout.addWidget(widget)

    def show_image(self, image_path):
        viewer = ImageViewer(image_path, self)
        viewer.exec_()

    def delete_image(self, image_path, widget):
        reply = QMessageBox.question(
            self, "Confirmer la suppression",
            f"Voulez-vous vraiment supprimer l'image:\n{os.path.basename(image_path)} ?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                os.remove(image_path)
                widget.deleteLater()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible de supprimer l'image:\n{e}")

    def generate_image_from_text(self, text):

        def can_generate_image():
            mem = psutil.virtual_memory()
            print(f"[DEBUG] RAM utilis\u00e9e : {mem.percent}%")
            return mem.percent < 85

        def afficher_erreur(message):
            self.parent.clear_waiting_message()
            self.parent.spinner_movie.stop()
            self.parent.spinner_label.setVisible(False)
            error_label = QLabel(f"<span style='color:red'><b>[ERREUR]</b> {message}</span>")
            error_label.setWordWrap(True)
            self.parent.scroll_layout.addWidget(error_label)

        self.parent.set_waiting_message("Alice r\u00e9fl\u00e9chit...")
        self.parent.spinner_label.setVisible(True)
        self.parent.spinner_movie.start()
        self.parent.waiting_label.setVisible(True)

        label_wait = QLabel("<b>[Alice]</b> Je vais g\u00e9n\u00e9rer une image... Veuillez patienter \u23f3")
        self.parent.scroll_layout.addWidget(label_wait)
        QApplication.processEvents()

        if not self.resource_manager.ressources_disponibles():
            print("[INFO] Requête refusée: surcharge CPU ou RAM")
            return "Les ressources système sont surchargées. Veuillez réessayer plus tard."


        def run():
            print("[DEBUG] \u2192 D\u00e9but de run() image")

            if not can_generate_image():
                afficher_erreur("M\u00e9moire insuffisante pour g\u00e9n\u00e9rer une image. Veuillez fermer des applications ou r\u00e9essayer plus tard.")
                return

            result = self.agent.generate_image(text)
            print("[DEBUG] >>> resultat chemin generation image :", result)
            image_path = result.split("#image")[-1].strip() if result and "#image" in result else None

            if image_path and os.path.exists(image_path):
                correct_folder = "imagesManager/views_images"
                os.makedirs(correct_folder, exist_ok=True)
                correct_path = os.path.join(correct_folder, os.path.basename(image_path))

                if image_path != correct_path:
                    try:
                        shutil.move(image_path, correct_path)
                        print(f"[DEBUG] Image d\u00e9plac\u00e9e vers : {correct_path}")
                        image_path = correct_path
                    except Exception as e:
                        print(f"[ERREUR] Impossible de d\u00e9placer l'image : {e}")

            print("[DEBUG] >>> resultat chemin image_path :", image_path)

            if not image_path or not os.path.exists(image_path):
                afficher_erreur("L'image n'a pas pu \u00eatre g\u00e9n\u00e9r\u00e9e. Chemin invalide ou g\u00e9n\u00e9ration \u00e9chou\u00e9e.")
                return

            self.parent.image_path_result = image_path
            self.parent.clear_waiting_message()
            self.parent.spinner_movie.stop()
            self.parent.spinner_label.setVisible(False)
            QTimer.singleShot(0, self.display_generated_image)

        QTimer.singleShot(100, lambda: self.parent.scroll_area.verticalScrollBar().setValue(
            self.parent.scroll_area.verticalScrollBar().maximum()))

        QThreadPool.globalInstance().start(RunnableFunc(run))

    def display_generated_image(self):
        print("[DEBUG] \u2192 Entr\u00e9e dans display_generated_image()")
        image_path = getattr(self.parent, 'image_path_result', None)
        if image_path and os.path.exists(image_path):
            full_path = os.path.abspath(image_path).replace("\\", "/")
            pixmap = QPixmap(full_path)
            print(f"[DEBUG] Chargement pixmap depuis : {full_path} | Null ? {pixmap.isNull()}")

            if not pixmap.isNull():
                label = QLabel("<b>[Alice]</b> Voici votre image g\u00e9n\u00e9r\u00e9e :")
                label.setWordWrap(True)
                label.setStyleSheet("margin-top: 2px; margin-bottom: 2px; line-height: 1.2em;")
                self.parent.scroll_layout.addWidget(label)

                img_label = QLabel()
                img_label.setAlignment(Qt.AlignCenter)
                img_label.setPixmap(pixmap.scaledToWidth(350, Qt.SmoothTransformation))
                img_label.setStyleSheet("margin-top: 10px; margin-bottom: 10px;")
                self.parent.scroll_layout.addWidget(img_label)
                self.parent.save_button.setEnabled(True)
            else:
                self.parent.scroll_layout.addWidget(QLabel("<b>[Alice]</b> L'image est invalide ou corrompue."))
        else:
            self.parent.scroll_layout.addWidget(QLabel("<b>[Alice]</b> Erreur : image introuvable."))

        self.parent.voice_recognition_thread.resume()
        
        # Scroll automatique vers le bas
        QTimer.singleShot(100, lambda: self.parent.scroll_area.verticalScrollBar().setValue(
            self.parent.scroll_area.verticalScrollBar().maximum()))



if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = Image_Manager()
    w.resize(600, 400)
    w.show()
    sys.exit(app.exec_())