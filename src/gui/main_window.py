from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QComboBox
from PyQt5.QtCore import QThread, pyqtSignal
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
            response = self.agent.generate(self.prompt)  # Utilise .generate()
            self.response_ready.emit(response)
        except Exception as e:
            self.response_ready.emit(f"[ERREUR] [AGENT] Erreur lors de la génération : {e}")


class MainWindow(QWidget):
    def __init__(self, model_paths: dict):
        super().__init__()

        self.setWindowTitle("Alice - Interface")
        self.setGeometry(100, 100, 600, 400)

        self.model_paths = model_paths
        self.agent = None

        self.layout = QVBoxLayout()

        # Bouton pour voir la mémoire
        self.memory_button = QPushButton("Voir mémoire")
        self.memory_button.clicked.connect(self.open_memory_window)
        self.layout.addWidget(self.memory_button)

        # Étiquette et boîte de saisie
        self.label = QLabel("Entrez un message pour Alice :")
        self.input_box = QTextEdit()
        self.response_box = QTextEdit()
        self.response_box.setReadOnly(True)

        # Sélecteur de modèle
        self.model_selector = QComboBox()
        self.model_selector.addItems(model_paths.keys())
        self.model_selector.currentTextChanged.connect(self.load_model)

        # Boutons d'envoi et de sauvegarde
        self.send_button = QPushButton("Envoyer")
        self.send_button.clicked.connect(self.send_prompt)

        self.save_button = QPushButton("Sauvegarder #save")
        self.save_button.clicked.connect(self.save_prompt)

        # Texte explicatif sur la sauvegarde
        self.explanation_label = QLabel("Tapez '#save' pour enregistrer la donnée dans la mémoire.")

        # Ajouter les éléments à l'interface
        self.layout.addWidget(self.model_selector)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.input_box)
        self.layout.addWidget(self.send_button)
        self.layout.addWidget(self.save_button)  # Bouton de sauvegarde
        self.layout.addWidget(self.explanation_label)  # Texte explicatif
        self.layout.addWidget(QLabel("Réponse :"))
        self.layout.addWidget(self.response_box)

        self.setLayout(self.layout)

        # Charger le modèle initial
        self.load_model(self.model_selector.currentText())

    def load_model(self, model_name):
        path = self.model_paths[model_name]
        self.agent = LlamaCppAgent(path)
        self.response_box.append(f"[INFO] Modèle chargé : {model_name}")

    def send_prompt(self):
        prompt = self.input_box.toPlainText().strip()
        if not prompt:
            return
        self.response_box.append(f"Vous : {prompt}")
        self.input_box.clear()

        # Démarrer un thread pour générer la réponse
        self.thread = LlamaThread(self.agent, prompt)
        self.thread.response_ready.connect(self.display_response)
        self.thread.start()

    def display_response(self, response):
        self.response_box.append(f"Alice : {response}")

    def open_memory_window(self):
        self.memory_window = MemoryViewer()
        self.memory_window.show()

    def save_prompt(self):
        prompt = self.input_box.toPlainText().strip()
        if "#save" in prompt:
            # Sauvegarder la donnée avec #save
            self.agent.db_manager.save_memory(prompt, "Donnée sauvegardée par l'utilisateur")
            self.response_box.append("[INFO] Donnée sauvegardée avec succès.")
        else:
            self.response_box.append("[INFO] Tapez '#save' pour enregistrer la donnée.")


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)

    model_paths = {
        "Mistral": "C:/Users/Blazufr/Desktop/IA_alice_V3/model/mistral-7b-instruct-v0.2.Q8_0.gguf",
        "Nous-Hermes": "C:/Users/Blazufr/Desktop/IA_alice_V3/model/nous-hermes-2-mixtral-8x7b-sft.Q8_0.gguf"
    }

    window = MainWindow(model_paths)
    window.show()
    sys.exit(app.exec_())
