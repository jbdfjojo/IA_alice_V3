from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea,
    QHBoxLayout, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt
from db.mysql_manager import MySQLManager


class MemoryViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mémoire d'Alice")
        self.setGeometry(150, 150, 700, 500)

        self.db_manager = MySQLManager(
            host="localhost",
            user="root",
            password="JOJOJOJO88",
            database="ia_alice"
        )

        self.layout = QVBoxLayout(self)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container.setLayout(self.container_layout)

        self.scroll_area.setWidget(self.container)
        self.layout.addWidget(self.scroll_area)

        self.refresh_memory()

    def refresh_memory(self):
        # Nettoyage de l'affichage actuel
        for i in reversed(range(self.container_layout.count())):
            item = self.container_layout.itemAt(i).widget()
            if item:
                item.setParent(None)

        try:
            memories = self.db_manager.fetch_all_memories()
            if not memories:
                label = QLabel("Aucune mémoire enregistrée.")
                label.setStyleSheet("color: gray;")
                self.container_layout.addWidget(label)
                return

            for memory_id, prompt, response in memories:
                frame = QFrame()
                frame.setStyleSheet("background-color: #2d2d2d; border: 1px solid #444444; border-radius: 5px;")
                frame_layout = QVBoxLayout(frame)

                prompt_label = QLabel(f"<b>Vous :</b> {prompt}")
                prompt_label.setWordWrap(True)
                prompt_label.setStyleSheet("color: #80d4ff;")

                response_label = QLabel(f"<b>Alice :</b> {response}")
                response_label.setWordWrap(True)
                response_label.setStyleSheet("color: #c8ffc8;")

                delete_button = QPushButton("Supprimer")
                delete_button.setStyleSheet("background-color: #aa0000; color: white;")
                delete_button.clicked.connect(lambda _, mem_id=memory_id: self.delete_memory(mem_id))

                frame_layout.addWidget(prompt_label)
                frame_layout.addWidget(response_label)
                frame_layout.addWidget(delete_button)

                self.container_layout.addWidget(frame)

        except Exception as e:
            error_label = QLabel(f"[ERREUR] Impossible de charger les mémoires : {e}")
            error_label.setStyleSheet("color: red;")
            self.container_layout.addWidget(error_label)

    def delete_memory(self, memory_id):
        confirm = QMessageBox.question(
            self, "Supprimer la mémoire",
            "Voulez-vous vraiment supprimer cette mémoire ?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            try:
                self.db_manager.delete_memory_by_id(memory_id)
                self.refresh_memory()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Échec de la suppression : {e}")
