import os
import pyttsx3
from llama_cpp import Llama
from db.mysql_manager import MySQLManager
import subprocess
from PyQt5.QtCore import QThread, pyqtSignal
import json

class LlamaThread(QThread):
    response_ready = pyqtSignal(str, str)  # Signal avec deux arguments

    def __init__(self, agent, prompt):
        super().__init__()
        self.agent = agent
        self.prompt = prompt

    def run(self):
        try:
            if self.prompt.strip():
                response = self.agent.generate(self.prompt)
                self.response_ready.emit(self.prompt, response)
            else:
                self.response_ready.emit(self.prompt, "Aucune entrée valide détectée.")
        except Exception as e:
            self.response_ready.emit(self.prompt, f"[ERREUR] [AGENT] Erreur lors de la génération : {str(e)}")

class LlamaCppAgent:
    def __init__(self, model_paths: dict, config_file="C:/Users/Blazufr/Desktop/IA_alice_V3/config.json"):
        self.config = self.load_config(config_file)
        self.model_paths = model_paths  # Stocke les chemins pour potentiellement changer de modèle à chaud

        # Récupère le modèle à partir de la configuration
        last_model = self.config.get("last_model", "Mistral-7B-Instruct")
        model_path = model_paths.get(last_model)

        if not model_path:
            raise ValueError(f"Modèle '{last_model}' non trouvé dans les chemins fournis.")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modèle introuvable : {model_path}")

        self.model_path = model_path
        self.speech_enabled = True
        self.engine = pyttsx3.init()
        self.model = Llama(model_path=self.model_path, n_ctx=2048)
        self.db_manager = MySQLManager("localhost", "root", "JOJOJOJO88", "ia_alice")
        self.first_interaction = True

    def load_config(self, config_file):
        try:
            with open(config_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERREUR] Impossible de charger le fichier de configuration : {e}")
            return {}

    def set_speech_enabled(self, enabled: bool):
        self.speech_enabled = enabled

    def generate(self, prompt: str) -> str:
        prompt = prompt.strip()

        if "#save" in prompt:
            cleaned_prompt = prompt.replace("#save", "").strip()
            self.save_to_memory(cleaned_prompt, "Réponse sauvegardée sans génération.")
            return "L'interaction a été sauvegardée."

        cleaned_prompt = prompt
        response = self.model.create_completion(
            prompt=f"Vous : {cleaned_prompt}\nAlice :",
            max_tokens=200,
            temperature=0.7,
            top_p=0.9,
            stop=["\nVous:", "\nAlice:", "\n"]
        )

        answer = response['choices'][0]['text'].strip()
        self.save_to_memory(cleaned_prompt, answer)
        return answer

    def generate_image(self, prompt: str) -> str:
        try:
            description = prompt.lower().split("image", 1)[-1].strip()
            if not description:
                return "[ERREUR] Veuillez décrire l'image après le mot-clé 'image'."

            model_path = "C:/Users/Blazufr/Desktop/IA_alice_V3/src/agent"
            output_path = "images/generated_image.png"

            result = subprocess.run(
                ["python", os.path.join(model_path, "generate.py"),
                 "--prompt", description,
                 "--output", output_path],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"[ERREUR] Génération image : {result.stderr}")
                return "[ERREUR] Échec lors de la génération de l'image."

            return f"#image {output_path}"

        except Exception as e:
            return f"[ERREUR] Exception lors de la génération de l'image : {str(e)}"

    def speak(self, text: str):
        try:
            if self.speech_enabled:
                self.engine.say(text)
                self.engine.runAndWait()
        except Exception as e:
            print(f"[ERREUR] [VOIX] {e}")

    def save_to_memory(self, prompt: str, response: str):
        try:
            self.db_manager.save_memory(prompt, response)
        except Exception as e:
            print(f"[ERREUR] [MÉMOIRE] Échec de la sauvegarde en base de données : {str(e)}")

    def is_important(self, prompt: str, response: str) -> bool:
        return len(prompt) >= 15

    def save_interaction(self):
        prompt = self.text_input.toPlainText()
        if prompt.strip():
            self.agent.save_to_memory(prompt, "Réponse sauvegardée sans génération.")
            self.display_message("L'interaction a été sauvegardée.")
        else:
            self.display_message("Aucune interaction à sauvegarder.")

    def display_message(self, message: str):
        self.output_text.setPlainText(message)
