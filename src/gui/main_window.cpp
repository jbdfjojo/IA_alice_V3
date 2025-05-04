from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel, QComboBox
from PyQt5.QtCore import QThread, pyqtSignal

from llama_cpp_agent import LlamaCppAgent  # uniquement cette ligne est nécessaire

class LlamaThread(QThread):
    finished = pyqtSignal(str)

    def __init__(self, agent, prompt):
        super().__init__()
        self.agent = agent
        self.prompt = prompt

    def run(self):
        print(f"[THREAD] Exécution du thread avec le prompt : {self.prompt}")
        try:
            response = self.agent.generate_response(self.prompt)
            print(f"[THREAD] Réponse générée : {response}")
            self.finished.emit(response)
        except Exception as e:
            self.finished.emit(f"[Erreur] {str(e)}")

class MainWindow(QWidget):
    def __init__(self, model_paths):
        super().__init__()
        self.setWindowTitle("Alice - Interface IA")
        self.resize(600, 400)

        self.model_paths = model_paths
        self.agent = None
        self.thread = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.combo_model = QComboBox()
        self.combo_model.addItems(self.model_paths.keys())
        self.combo_model.currentTextChanged.connect(self.load_model)
        layout.addWidget(QLabel("Choisir un modèle :"))
        layout.addWidget(self.combo_model)

        self.input_text = QTextEdit()
        layout.addWidget(QLabel("Vous :"))
        layout.addWidget(self.input_text)

        self.button_send = QPushButton("Envoyer")
        self.button_send.clicked.connect(self.send_prompt)
        layout.addWidget(self.button_send)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        layout.addWidget(QLabel("Alice :"))
        layout.addWidget(self.output_text)

        self.setLayout(layout)
        self.load_model(self.combo_model.currentText())

    def load_model(self, model_name):
        model_path = self.model_paths[model_name]
        self.agent = LlamaCppAgent(model_path)

    def send_prompt(self):
        prompt = self.input_text.toPlainText().strip()
        if not prompt or not self.agent:
            return
        self.output_text.append(f"Vous : {prompt}")
        self.thread = LlamaThread(self.agent, prompt)
        self.thread.finished.connect(self.display_response)
        self.thread.start()

    def display_response(self, response):
        self.output_text.append(f"Alice : {response}")
