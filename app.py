import sys
import os
import json
from main_window import MainWindow
from llama_cpp_agent import LlamaCppAgent
from PyQt5.QtWidgets import QApplication


def main():
    model_paths = {
        "Mistral-7B-Instruct": os.path.abspath("model/mistral-7b-instruct-v0.2.Q8_0.gguf"),
        "Nous-Hermes-2-Mixtral": os.path.abspath("model/nous-hermes-llama2-13b.Q8_0.gguf")
    }

    config_path = os.path.abspath("config.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError("Fichier config.json introuvable.")
    with open(config_path, "r") as f:
        config = json.load(f)

    last_model = config.get("last_model", "Mistral-7B-Instruct")
    if last_model not in model_paths:
        raise ValueError(f"Modèle sélectionné '{last_model}' invalide.")

    agent = LlamaCppAgent(model_paths=model_paths, selected_model=last_model)

    app = QApplication(sys.argv)
    window = MainWindow(model_paths, agent)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
