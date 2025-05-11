import sys
import json
from PyQt5.QtWidgets import QApplication
from llama_cpp_agent import LlamaCppAgent
from main_window import MainWindow

# Définir les chemins des modèles
model_paths = {
    "Mistral-7B-Instruct": "C:/Users/Blazufr/Desktop/IA_alice_V3/model/mistral-7b-instruct-v0.2.Q8_0.gguf",
    "Nous-Hermes-2-Mixtral": "C:/Users/Blazufr/Desktop/IA_alice_V3/model/nous-hermes-2-mixtral-8x7b-sft.Q8_0.gguf"
}

# Charger la configuration
try:
    with open("config.json", "r") as f:
        config = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError("Fichier config.json introuvable.")

# Récupérer le dernier modèle utilisé
last_model = config.get("last_model", "Mistral-7B-Instruct")

# Vérifier que le chemin du modèle existe
selected_model_path = model_paths.get(last_model)
if not selected_model_path:
    raise FileNotFoundError(f"Modèle manquant ou chemin invalide : {last_model} -> {selected_model_path}")

# Créer l'agent avec tous les chemins possibles
agent = LlamaCppAgent(model_paths)  # <-- PAS selected_model_path

# Lancer l'application
app = QApplication(sys.argv)
window = MainWindow(model_paths)
window.show()
sys.exit(app.exec_())
