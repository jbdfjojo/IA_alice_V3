import os
import pyttsx3
from llama_cpp import Llama
from db.mysql_manager import MySQLManager
import re
import subprocess
from PyQt5.QtCore import QThread, pyqtSignal

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
                # Émettre le signal avec deux arguments : prompt et response
                self.response_ready.emit(self.prompt, response)  # Passe aussi le prompt et la réponse
            else:
                self.response_ready.emit(self.prompt, "Aucune entrée valide détectée.")
        except Exception as e:
            self.response_ready.emit(self.prompt, f"[ERREUR] [AGENT] Erreur lors de la génération : {str(e)}")

class LlamaCppAgent:
    def __init__(self, model_paths: dict):
        # Récupération du chemin du modèle "Mistral" par défaut
        model_path = model_paths.get("Mistral-7B-Instruct") or model_paths.get("Nous-Hermes-2-Mixtral")
        if not isinstance(model_path, str):
            raise ValueError("Le chemin du modèle doit être une chaîne de caractères.")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modèle introuvable : {model_path}")

        self.model_path = model_path
        self.speech_enabled = True
        self.engine = pyttsx3.init()
        self.model = Llama(model_path=self.model_path, n_ctx=2048)
        self.db_manager = MySQLManager("localhost", "root", "JOJOJOJO88", "ia_alice")
        self.first_interaction = True

    def set_speech_enabled(self, enabled: bool):
        self.speech_enabled = enabled

    def generate(self, prompt: str) -> str:
        prompt = prompt.strip()

        # Vérifier si le prompt contient "#save" et l'enlever de la chaîne de texte
        if "#save" in prompt:
            cleaned_prompt = prompt.replace("#save", "").strip()
            self.save_to_memory(cleaned_prompt, "Réponse sauvegardée sans génération.")  # Sauvegarder uniquement
            return "L'interaction a été sauvegardée."

        # Continuer la génération de réponse comme d'habitude
        cleaned_prompt = prompt  # Pas de changement, car #save a été géré précédemment

        response = self.model.create_completion(
            prompt=f"Vous : {cleaned_prompt}\nAlice :",
            max_tokens=500,
            temperature=0.9,
            top_p=0.95,
            stop=["</s>", "Alice:", "Vous:"]
        )
        answer = response['choices'][0]['text'].strip()

        # Sauvegarder la mémoire après la génération de la réponse
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

            # Ajout de la référence à l'image dans le fil de discussion
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
        """Sauvegarde le prompt et la réponse dans la base de données MySQL"""
        try:
            self.db_manager.save_memory(prompt, response)
        except Exception as e:
            print(f"[ERREUR] [MÉMOIRE] Échec de la sauvegarde en base de données : {str(e)}")

    def is_important(self, prompt: str, response: str) -> bool:
        return len(prompt) >= 15

    def save_interaction(self):
        """Sauvegarde uniquement l'interaction actuelle sans génération de réponse"""
        prompt = self.text_input.toPlainText()  # Ou tout autre mécanisme pour récupérer l'entrée
        if prompt.strip():
            self.agent.save_to_memory(prompt, "Réponse sauvegardée sans génération.")
            self.display_message("L'interaction a été sauvegardée.")
        else:
            self.display_message("Aucune interaction à sauvegarder.")

    def display_message(self, message: str):
        """Affiche un message dans l'interface"""
        self.output_text.setPlainText(message)