# interfaceManager/interface_manager.py

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QScrollArea, QWidget, QPushButton,
    QTextEdit, QLabel, QComboBox, QCheckBox, QSizePolicy
)
from PyQt5.QtGui import QMovie, QFont
from PyQt5.QtCore import Qt, QSize

from utils.utils import StyledLabel, InputTextEdit

class InterfaceManager:
    def __init__(self, parent):
        self.parent = parent
        self.apply_dark_theme()
        self.setup_ui()

    def apply_dark_theme(self):
        self.parent.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #f0f0f0;
                font-family: 'Times New Roman', serif;
                font-size: 16px;
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

        # --- Top controls ---
        top_controls = QHBoxLayout()

        self.parent.model_selector = QComboBox()
        self.parent.model_selector.addItems(self.parent.model_paths.keys())
        self.parent.model_selector.currentTextChanged.connect(self.parent.load_model)
        top_controls.addWidget(self.parent.model_selector)

        self.parent.voice_checkbox = QCheckBox("Voix")
        self.parent.voice_checkbox.stateChanged.connect(self.parent.toggle_voice)
        top_controls.addWidget(self.parent.voice_checkbox)

        self.parent.voice_button = QPushButton("🎤 Micro: OFF")
        self.parent.voice_button.setCheckable(True)
        self.parent.voice_button.clicked.connect(self.parent.toggle_voice_input)
        self.parent.voice_button.setStyleSheet("background-color: lightcoral; font-weight: bold;")
        top_controls.addWidget(self.parent.voice_button)

        self.parent.language_selector = QComboBox()
        self.parent.language_selector.addItems(["Python", "JavaScript", "C++", "HTML", "SQL"])
        top_controls.addWidget(self.parent.language_selector)

        self.parent.image_manager_button = QPushButton("Images")
        self.parent.image_manager_button.clicked.connect(self.parent.open_image_manager)
        top_controls.addWidget(self.parent.image_manager_button)

        self.parent.memory_button = QPushButton("Mémoire")
        self.parent.memory_button.clicked.connect(self.parent.open_memory_window)
        top_controls.addWidget(self.parent.memory_button)

        self.parent.save_button = QPushButton("Sauvegarder")
        self.parent.save_button.clicked.connect(self.parent.save_prompt)
        self.parent.save_button.setEnabled(False)
        top_controls.addWidget(self.parent.save_button)

        layout.addLayout(top_controls)

        # --- Scroll area for response ---
        self.parent.scroll_area = QScrollArea()
        self.parent.scroll_area.setWidgetResizable(True)
        self.parent.scroll_widget = QWidget()
        self.parent.scroll_layout = QVBoxLayout(self.parent.scroll_widget)
        self.parent.scroll_layout.setAlignment(Qt.AlignTop)
        self.parent.scroll_layout.setSpacing(0)
        self.parent.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.parent.scroll_area.setWidget(self.parent.scroll_widget)
        self.parent.scroll_area.setFont(QFont("Times New Roman", 14))
        layout.addWidget(self.parent.scroll_area)

        # --- Waiting container ---
        self.parent.waiting_container = QWidget()
        self.parent.waiting_container.setVisible(False)
        waiting_layout = QHBoxLayout(self.parent.waiting_container)
        waiting_layout.setAlignment(Qt.AlignCenter)

        self.parent.spinner_label = QLabel()
        self.parent.spinner_movie = QMovie("assets/spinner_2.gif")
        self.parent.spinner_movie.setScaledSize(QSize(24, 24))
        if self.parent.spinner_movie.isValid():
            self.parent.spinner_label.setMovie(self.parent.spinner_movie)
        self.parent.spinner_label.setVisible(True)

        self.parent.waiting_label = QLabel("Alice réfléchit...")
        self.parent.waiting_label.setStyleSheet("font-style: italic; font-size: 14px;")
        self.parent.waiting_label.setAlignment(Qt.AlignLeft)

        waiting_layout.addWidget(self.parent.spinner_label)
        waiting_layout.addWidget(self.parent.waiting_label)
        layout.addWidget(self.parent.waiting_container)

        # --- Input box and send button ---
        bottom_layout = QHBoxLayout()

        self.parent.input_box = InputTextEdit(submit_callback=self.parent.send_prompt)
        self.parent.input_box.setPlaceholderText("Entrez votre message ici...")
        self.parent.input_box.setFont(QFont("Times New Roman", 14))
        self.parent.input_box.setFixedHeight(self.parent.height() // 6)
        bottom_layout.addWidget(self.parent.input_box)

        self.parent.send_button = QPushButton("Envoyer")
        self.parent.send_button.clicked.connect(self.parent.send_prompt)
        self.parent.send_button.setFixedHeight(40)
        bottom_layout.addWidget(self.parent.send_button)

        layout.addLayout(bottom_layout)
        self.parent.setLayout(layout)
