import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow
from gui.styles import apply_dark_theme

if __name__ == "__main__":
    model_paths = {
        "Mistral-7B-Instruct": "C:/Users/Blazufr/Desktop/IA_alice_V3/model/mistral-7b-instruct-v0.2.Q8_0.gguf",
        "Nous-Hermes-2-Mixtral": "C:/Users/Blazufr/Desktop/IA_alice_V3/model/nous-hermes-llama2-13b.Q8_0.gguf"
    }

    app = QApplication(sys.argv)
    apply_dark_theme(app)
    window = MainWindow(model_paths)
    window.show()
    sys.exit(app.exec_())
