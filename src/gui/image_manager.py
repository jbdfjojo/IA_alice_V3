import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QMessageBox, QSizePolicy, QApplication, QDialog
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QSize

class ImageViewer(QDialog):
    """Fenêtre pour afficher une image en grand."""
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image en grand")
        self.setWindowModality(Qt.ApplicationModal)
        self.layout = QVBoxLayout(self)
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.label)

        pixmap = QPixmap(image_path)
        screen_size = QApplication.primaryScreen().size()
        max_width = screen_size.width() * 0.8
        max_height = screen_size.height() * 0.8
        pixmap = pixmap.scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label.setPixmap(pixmap)
        self.resize(pixmap.size())

class ImageManager(QWidget):
    def __init__(self, images_folder="images", style_sheet=None, parent=None):
        super().__init__(parent)
        self.images_folder = images_folder

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

        self.load_images()

    def load_images(self):
        # Nettoyer la vue avant de recharger
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not os.path.exists(self.images_folder):
            QMessageBox.warning(self, "Dossier non trouvé", f"Le dossier {self.images_folder} n'existe pas.")
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
        label.setScaledContents(False)
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


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = ImageManager()
    w.resize(600, 400)
    w.show()
    sys.exit(app.exec_())
