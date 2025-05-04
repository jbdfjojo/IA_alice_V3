import sys
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow

if __name__ == "__main__":
    model_paths = {
        "Mistral-7B-Instruct": "C:/Users/Blazufr/Desktop/IA_alice_V3/model/mistral-7b-instruct-v0.2.Q8_0.gguf",
        "Nous-Hermes-2-Mixtral": "C:/Users/Blazufr/Desktop/IA_alice_V3/model/nous-hermes-2-mixtral-8x7b-sft.Q8_0.gguf"
    }

    app = QApplication(sys.argv)
    window = MainWindow(model_paths)
    window.show()
    sys.exit(app.exec_())
