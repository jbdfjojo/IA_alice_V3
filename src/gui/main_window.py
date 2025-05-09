from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QComboBox, QCheckBox
from PyQt5.QtCore import QThread, pyqtSignal, QSettings
from gui.memory_window import MemoryViewer
from llama_cpp_agent import LlamaCppAgent

class LlamaThread(QThread):
    response_ready = pyqtSignal(str)

    def __init__(self, agent, prompt):
        super().__init__()
        self.agent = agent
        self.prompt = prompt

    def run(self):
        try:
            # Modification ici : ajout d'un prompt clair pour le modèle
            prompt_with_instruction = f"Réponds uniquement à la question suivante : {self.prompt}"
            response = self.agent.generate(prompt_with_instruction)
            self.response_ready.emit(response)
        except Exception as e:
            # Gestion de l'erreur : émission d'un message d'erreur
            self.response_ready.emit(f"[ERREUR] [AGENT] Erreur lors de la génération : {str(e)}")

class MainWindow(QWidget):
    def __init__(self, model_paths: dict):
        super().__init__()
        self.setWindowTitle("Alice - Interface")
        self.setGeometry(100, 100, 600, 500)

        self.model_paths = model_paths
        self.agent = None
        self.settings = QSettings("AliceAI", "AliceApp")

        self.layout = QVBoxLayout()

        # Case à cocher pour la voix
        self.voice_checkbox = QCheckBox("Activer la voix")
        voice_enabled = self.settings.value("voice_enabled", True, type=bool)
        self.voice_checkbox.setChecked(voice_enabled)
        self.voice_checkbox.stateChanged.connect(self.toggle_voice)
        self.layout.addWidget(self.voice_checkbox)

        # Bouton mémoire
        self.memory_button = QPushButton("Voir mémoire")
        self.memory_button.clicked.connect(self.open_memory_window)
        self.layout.addWidget(self.memory_button)

        self.label = QLabel("Entrez un message pour Alice :")
        self.input_box = QTextEdit()
        self.response_box = QTextEdit()
        self.response_box.setReadOnly(True)

        self.model_selector = QComboBox()
        self.model_selector.addItems(model_paths.keys())
        self.model_selector.currentTextChanged.connect(self.load_model)

        self.send_button = QPushButton("Envoyer")
        self.send_button.clicked.connect(self.send_prompt)

        self.save_button = QPushButton("Sauvegarder #save")
        self.save_button.clicked.connect(self.save_prompt)

        self.explanation_label = QLabel("Tapez '#save' pour enregistrer la donnée dans la mémoire.")

        # Réorganiser l'ordre des widgets pour mettre la réponse en haut
        self.layout.addWidget(self.response_box)  # Ajouter la réponse en premier
        self.layout.addWidget(QLabel("Réponse :"))
        self.layout.addWidget(self.model_selector)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.input_box)
        self.layout.addWidget(self.send_button)
        self.layout.addWidget(self.save_button)
        self.layout.addWidget(self.explanation_label)

        self.setLayout(self.layout)

        # Charger le dernier modèle utilisé
        last_model = self.settings.value("last_model", self.model_selector.itemText(0))
        index = self.model_selector.findText(last_model)
        self.model_selector.setCurrentIndex(index if index != -1 else 0)
        self.load_model(self.model_selector.currentText())

    def load_model(self, model_name):
        """Charge le modèle sélectionné et configure la voix."""
        try:
            path = self.model_paths[model_name]
            self.agent = LlamaCppAgent(path)
            # Appliquer l'état de la voix dès le chargement du modèle
            self.agent.set_speech_enabled(self.voice_checkbox.isChecked())
            self.response_box.append(f"[INFO] Modèle chargé : {model_name}")
            self.settings.setValue("last_model", model_name)
        except Exception as e:
            self.response_box.append(f"[ERREUR] Problème lors du chargement du modèle : {str(e)}")

    def toggle_voice(self):
        """Active ou désactive la lecture vocale."""
        if self.agent:
            self.agent.set_speech_enabled(self.voice_checkbox.isChecked())
        self.settings.setValue("voice_enabled", self.voice_checkbox.isChecked())

    def send_prompt(self):
        """Envoie un prompt à l'agent, affiche la réponse et sauvegarde si mot-clé détecté."""
        prompt = self.input_box.toPlainText().strip()
        if not prompt:
            return

        # Affiche le message utilisateur
        self.response_box.append(f"\nVous : {prompt}")
        self.input_box.clear()
        self.send_button.setEnabled(False)

        # Sauvegarde automatique si un mot-clé est présent
        lower_prompt = prompt.lower()
        keywords = ["#save", "cree", "ajoute", "souviens-toi", "enregistre"]
        if any(keyword in lower_prompt for keyword in keywords):
            if self.agent and hasattr(self.agent, 'db_manager'):
                self.agent.db_manager.save_memory(prompt, "Ajout automatique via mot-clé")
                self.response_box.append("[INFO] Mémoire enregistrée automatiquement.")

        if self.agent:
            self.agent.set_speech_enabled(self.voice_checkbox.isChecked())

        self.thread = LlamaThread(self.agent, prompt)
        self.thread.response_ready.connect(self.display_response)
        self.thread.start()
  

    def display_response(self, response):
        """Affiche la réponse de l'agent."""
        if response.startswith("[ERREUR]"):
            self.response_box.append(response)
        else:
            # Affiche d'abord la question de l'utilisateur, puis la réponse d'Alice
            self.response_box.append(f"Alice : {response}")  # Affiche la réponse de l'agent
        self.send_button.setEnabled(True)

    def open_memory_window(self):
        """Ouvre la fenêtre de mémoire."""
        self.memory_window = MemoryViewer()
        self.memory_window.show()

    def save_prompt(self):
        """Sauvegarde la donnée si un mot-clé spécifique est détecté dans le prompt."""
        prompt = self.input_box.toPlainText().strip().lower()

        # Liste de mots-clés qui déclenchent la sauvegarde
        keywords = ["cree", "ajoute", "remplace", "souviens-toi", "enregistre", "#save"]

        if any(keyword in prompt for keyword in keywords):
            self.agent.db_manager.save_memory(prompt, "Donnée sauvegardée par l'utilisateur")
            self.response_box.append("[INFO] Donnée sauvegardée avec succès.")
        else:
            self.response_box.append("[INFO] Aucun mot-clé détecté pour la sauvegarde.")


    def closeEvent(self, event):
        """Enregistre les paramètres avant la fermeture de l'application."""
        self.settings.setValue("voice_enabled", self.voice_checkbox.isChecked())
        self.settings.setValue("last_model", self.model_selector.currentText())
        event.accept()
