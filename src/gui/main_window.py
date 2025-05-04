from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QApplication
)
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPixmap
from llama_cpp_agent import LlamaCppAgent


class LlamaThread(QThread):
    response_ready = pyqtSignal(str)

    def __init__(self, model: LlamaCppAgent, prompt: str):
        super().__init__()
        self.model = model
        self.prompt = prompt
        layout = QVBoxLayout()
        logo = QLabel()
        logo.setPixmap(QPixmap("assets/logo.png").scaledToHeight(80))
        layout.addWidget(logo)

    def run(self):
        try:
            response = self.model.generate_response(self.prompt)
            if isinstance(response, dict) and 'choices' in response:
                self.response_ready.emit(response['choices'][0]['text'].strip())
            elif isinstance(response, str):
                self.response_ready.emit(response.strip())
            else:
                self.response_ready.emit("Réponse invalide.")
        except Exception as e:
            self.response_ready.emit(f"Erreur : {str(e)}")


class MainWindow(QWidget):
    def __init__(self, model_paths: dict):
        super().__init__()
        self.setWindowTitle("Alice - Interface")
        self.setGeometry(100, 100, 600, 400)

        self.model_paths = model_paths
        self.agent = None

        self.layout = QVBoxLayout()
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
