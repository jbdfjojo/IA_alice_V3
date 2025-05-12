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

# Vérifier que le modèle sélectionné est valide
if last_model not in model_paths:
    raise ValueError(f"Le modèle sélectionné '{last_model}' est invalide dans la configuration.")

# Récupérer le chemin du modèle sélectionné
selected_model_path = model_paths[last_model]
selected_model = "Mistral-7B-Instruct"
# Créer l'agent avec le modèle sélectionné
agent = LlamaCppAgent(model_paths=model_paths, selected_model=selected_model) # Passer uniquement le chemin du modèle sélectionné

# Lancer l'application
app = QApplication(sys.argv)
window = MainWindow(model_paths)  # Passer les chemins des modèles à la fenêtre
window.show()
sys.exit(app.exec_())
