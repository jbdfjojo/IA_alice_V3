# src/gui/main_window.py

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
            response = self.agent.generate(self.prompt)  # ← utilise .generate() pas .speak()
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

        self.layout.addWidget(self.model_selector)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.input_box)
        self.layout.addWidget(self.send_button)
        self.layout.addWidget(QLabel("Réponse :"))
        self.layout.addWidget(self.response_box)

        self.setLayout(self.layout)

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

        self.thread = LlamaThread(self.agent, prompt)
        self.thread.response_ready.connect(self.display_response)
        self.thread.start()

    def display_response(self, response):
        self.response_box.append(f"Alice : {response}")

    def open_memory_window(self):
        self.memory_window = MemoryViewer()
        self.memory_window.show()

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
