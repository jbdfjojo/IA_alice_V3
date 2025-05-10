from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QLabel, QCheckBox, QComboBox, QScrollArea
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QPixmap
from src.llama_cpp_agent import LlamaCppAgent, LlamaThread
from gui.memory_window import MemoryViewer


class MainWindow(QWidget):
    def __init__(self, model_paths: dict):
        super().__init__()
        self.setWindowTitle("Alice - Interface")
        self.setGeometry(100, 100, 800, 600)

        self.model_paths = model_paths
        self.agent = None
        self.settings = QSettings("AliceAI", "AliceApp")

        self.setup_ui()

        last_model = self.settings.value("last_model", self.model_selector.itemText(0))
        index = self.model_selector.findText(last_model)
        self.model_selector.setCurrentIndex(index if index != -1 else 0)
        self.load_model(self.model_selector.currentText())

    def setup_ui(self):
        main_layout = QVBoxLayout()

        # Top controls
        controls_layout = QHBoxLayout()
        self.voice_checkbox = QCheckBox("Voix")
        self.voice_checkbox.setChecked(self.settings.value("voice_enabled", True, type=bool))
        self.voice_checkbox.stateChanged.connect(self.toggle_voice)

        self.memory_button = QPushButton("Mémoire")
        self.memory_button.clicked.connect(self.open_memory_window)

        self.model_selector = QComboBox()
        self.model_selector.addItems(self.model_paths.keys())
        self.model_selector.currentTextChanged.connect(self.load_model)

        controls_layout.addWidget(self.voice_checkbox)
        controls_layout.addWidget(self.memory_button)
        controls_layout.addWidget(self.model_selector)
        main_layout.addLayout(controls_layout)

        # Response area
        self.response_box = QTextEdit()
        self.response_box.setReadOnly(True)
        main_layout.addWidget(self.response_box)

        # Waiting message
        self.waiting_label = QLabel("Alice travaille sur votre demande... Veuillez patienter.")
        self.waiting_label.setAlignment(Qt.AlignCenter)
        self.waiting_label.setVisible(False)
        main_layout.addWidget(self.waiting_label)

        # Prompt area
        input_layout = QVBoxLayout()
        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Entrez votre message pour Alice...")

        buttons_layout = QHBoxLayout()
        self.send_button = QPushButton("Envoyer")
        self.send_button.clicked.connect(self.send_prompt)
        self.save_button = QPushButton("#save")
        self.save_button.clicked.connect(self.save_prompt)

        buttons_layout.addWidget(self.send_button)
        buttons_layout.addWidget(self.save_button)

        self.explanation_label = QLabel("Tapez '#save' pour enregistrer la donnée dans la mémoire.")
        self.explanation_label.setAlignment(Qt.AlignCenter)

        input_layout.addWidget(self.input_box)
        input_layout.addLayout(buttons_layout)
        input_layout.addWidget(self.explanation_label)

        main_layout.addLayout(input_layout)

        # Scroll area for displaying images
        self.scroll_area = QScrollArea()
        self.image_label = QLabel()  # For displaying images
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setVisible(False)
        main_layout.addWidget(self.scroll_area)

        self.setLayout(main_layout)

    def load_model(self, model_name):
        self.settings.setValue("last_model", model_name)
        model_path = self.model_paths.get(model_name)
        if model_path:
            self.agent = LlamaCppAgent(self.model_paths)
            self.agent.set_speech_enabled(self.voice_checkbox.isChecked())

    def toggle_voice(self):
        if self.agent:
            self.agent.set_speech_enabled(self.voice_checkbox.isChecked())
        self.settings.setValue("voice_enabled", self.voice_checkbox.isChecked())

    def send_prompt(self):
        prompt = self.input_box.toPlainText().strip()
        if not prompt:
            return

        # Ajouter automatiquement #image si l'utilisateur demande une image
        if "image" in prompt.lower() and "#image" not in prompt.lower():
            prompt += " #image"

        # Ajouter automatiquement #save si l'utilisateur tape "sauvegarde" ou "mémorise"
        if any(word in prompt.lower() for word in ["#save", "sauvegarde", "mémorise"]):
            if "#save" not in prompt.lower():
                prompt += " #save"

        self.input_box.clear()
        self.current_prompt = prompt  # stocker pour affichage

        # Afficher l'indicateur de travail
        self.waiting_label.setVisible(True)

        # Affichage dans la zone de réponse
        self.response_box.append(f"<b>Vous :</b> {prompt}")

        # Envoyer la requête via le thread
        self.thread = LlamaThread(self.agent, prompt)
        self.thread.response_ready.connect(self.display_response)
        self.thread.start()

    def save_prompt(self):
        text = self.input_box.toPlainText().strip()
        if text:
            self.input_box.setText(f"{text} #save")
            self.send_prompt()

    def display_response(self, prompt: str, response: str):
        # Détection du mot-clé image
        if "#image" in response:
            image_path = response.split(" ", 1)[-1]  # Récupère le chemin de l'image
            self.display_image(image_path)
        else:
            # Affiche le texte dans le fil de discussion
            self.display_text(prompt, response)

    def display_image(self, image_path: str):
        try:
            # Créez un chemin d'image HTML pour l'afficher dans QTextEdit
            image_html = f'<img src="{image_path}" width="400" />'  # Vous pouvez ajuster la largeur à votre convenance

            # Ajoutez l'image au QTextEdit sous forme de contenu HTML
            self.response_box.append(f"<b>Vous :</b> {self.current_prompt}")
            self.response_box.append("<b>Alice :</b>")
            self.response_box.append(image_html)  # Affiche l'image dans la zone de texte
            self.response_box.append("")  # Ligne vide après l'image pour espacer le texte

        except Exception as e:
            print(f"[ERREUR] Affichage de l'image : {str(e)}")

    def display_text(self, prompt: str, response: str):
        # Ajoute la réponse dans le fil de discussion
        self.response_box.append(f"<b>Vous :</b> {prompt}")
        self.response_box.append(f"<b>Alice :</b> {response}")

    def open_memory_window(self):
        self.memory_window = MemoryViewer()
        self.memory_window.show()
