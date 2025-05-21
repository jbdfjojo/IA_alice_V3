import os
import json
import pyttsx3
import subprocess
from llama_cpp import Llama
from PyQt5.QtCore import QThread, pyqtSignal
from db.mysql_manager import MySQLManager


class LlamaThread(QThread):
    response_ready = pyqtSignal(str, str)

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
            self.response_ready.emit(self.prompt, f"[ERREUR] [AGENT] : {str(e)}")


class LlamaCppAgent:
    def __init__(self, model_paths: dict, selected_model="Mistral-7B-Instruct"):
        self.model_path = model_paths.get(selected_model)
        if not self.model_path or not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Modèle introuvable : {self.model_path}")
        
        print(f"[INFO] Chargement du modèle : {self.model_path}")
        try:
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=1024,
                n_threads=6,
                n_gpu_layers=0,
                seed=42,
                verbose=True
            )
        except Exception as e:
            print(f"[ERREUR] Chargement du modèle : {e}")
            self.model = None

        self.engine = pyttsx3.init()
        self.speech_enabled = True
        self.db_manager = MySQLManager("localhost", "root", "JOJOJOJO88", "ia_alice")
        self.first_interaction = True

    def set_speech_enabled(self, enabled: bool):
        self.speech_enabled = enabled

    def speak(self, text: str):
        """ Synthèse vocale avec gestion des erreurs """
        if self.speech_enabled and text.strip():
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"[ERREUR VOCALE] : {e}")

    def generate(self, prompt: str) -> str:
        """ Génère une réponse à partir du prompt donné """
        if not self.model:
            return "[ERREUR] Modèle non initialisé."
        prompt = prompt.strip()
        if not prompt:
            return "[ERREUR] Prompt vide."

        try:
            result = self.model.create_completion(
                prompt=f"Vous : {prompt}\nAlice :",
                max_tokens=200,
                temperature=0.7,
                top_p=0.9,
                stop=["\nVous:", "\nAlice:", "\n"]
            )

            # Afficher la réponse brute (utile pour debug)
            print(f"[DEBUG] Réponse brute : {result}")

            if isinstance(result, dict) and "choices" in result and result["choices"]:
                answer = result["choices"][0]["text"].strip()
            else:
                answer = "[ERREUR] Réponse invalide."

            if not answer or len(answer.split()) < 2:
                return "[ERREUR] Réponse trop courte ou vide."

            self.save_to_memory(prompt, answer)
            return answer
        except Exception as e:
            return f"[ERREUR] Erreur génération : {str(e)}"

    def process_voice_input(self, voice_input: str):
        """ Traitement de l'entrée vocale """
        print(f"[VOICE INPUT] : {voice_input}")
        if not voice_input.strip():
            return "[ERREUR] Aucune entrée détectée."
        if "timeout" in voice_input.lower() or "audio incompréhensible" in voice_input.lower():
            return "[ERREUR] Entrée audio invalide."
        return self.generate(voice_input)

    def generate_image(self, prompt: str) -> str:
        """ Génère une image à partir d'un prompt """
        try:
            description = prompt.lower().split("image", 1)[-1].strip()
            if not description:
                return "[ERREUR] Veuillez décrire l'image."

            script_path = os.path.abspath("src/agent/generate.py")
            output_path = os.path.abspath("images/generated_image.png")

            result = subprocess.run(
                ["python", script_path, "--prompt", description, "--output", output_path],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"[ERREUR IMAGE] : {result.stderr}")
                return "[ERREUR] Échec génération d'image."

            return f"#image {output_path}"
        except Exception as e:
            return f"[ERREUR] Exception génération image : {str(e)}"

    def save_to_memory(self, prompt: str, response: str):
        """ Enregistre l'échange dans la mémoire MySQL """
        try:
            self.db_manager.save_memory(prompt, response)
        except Exception as e:
            print(f"[ERREUR MÉMOIRE] : {e}")

    def is_important(self, prompt: str, response: str) -> bool:
        return len(prompt) >= 15
