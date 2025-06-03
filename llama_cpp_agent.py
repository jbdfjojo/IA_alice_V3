import json
import pyttsx3
import subprocess
from llama_cpp import Llama
from db_mysql_Manager.mysql_manager import MySQLManager
import threading
from datetime import datetime
from imagesManager import generate 
from imagesManager.generate import generate_image
from diffusers import StableDiffusionPipeline
import torch_directml
import os

from erreurManager.error_handler import ErrorHandler


class LlamaCppAgent:
    def __init__(self, model_paths: dict, selected_model="Mistral-7B-Instruct", error_handler=None):
        self.error_handler = error_handler or ErrorHandler()

        self.model_paths = model_paths
        self.model_path = model_paths.get(selected_model)
        if not self.model_path or not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Modèle introuvable : {self.model_path}")

        print(f"[INFO] Chargement du modèle : {self.model_path}")
        try:
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=2048,            # Contexte plus large si utile (selon ta RAM)
                n_batch=512,           # Meilleure vitesse (valeurs entre 256 et 1024 selon la RAM)
                n_threads=6,           # Autant que ton nombre de cœurs CPU
                n_gpu_layers=0,        # Si tu veux tout sur CPU. Sinon adapte.
                seed=42,
                use_mmap=True,         # Chargement mémoire optimisé
                use_mlock=True,        # Évite le swap (garde en RAM)
                f16_kv=True,           # Active les clés/valeurs float16 (accélère le modèle)
                logits_all=False,      # Utile si tu n'as pas besoin de tous les logits
                verbose=False          # Optionnel : désactive les logs verbeux
            )

        except Exception as e:
            self.error_handler.handle_error(e, context="Chargement du modèle", user_message="Erreur lors du chargement du modèle")
            self.model = None

        self.engine = pyttsx3.init()
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if "french" in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break

        self.speech_enabled = True
        self.db_manager = MySQLManager("localhost", "root", "JOJOJOJO88", "ia_alice")
        self.first_interaction = True

    def set_speech_enabled(self, enabled: bool):
        self.speech_enabled = enabled

    def speak(self, text: str):
        if self.speech_enabled and text.strip():
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                self.error_handler.handle_error(e, context="Synthèse vocale", user_message="Erreur vocale")

    def generate(self, prompt: str) -> str:
        if not self.model:
            return "[ERREUR] Modèle non initialisé."
        prompt = prompt.strip()
        if not prompt:
            return "[ERREUR] Prompt vide."

        should_save = "#save" in prompt
        cleaned_prompt = prompt.replace("#save", "").strip()

        final_prompt = (
            "Tu es une IA qui parle exclusivement en français.\n"
            "Réponds toujours de façon claire et concise.\n"
            f"Utilisateur : {cleaned_prompt}\nAlice :"
        )

        try:
            result = self.model.create_completion(
                prompt=final_prompt,
                max_tokens=400,
                temperature=0.7,
                top_p=0.9,
                stop=["\nUtilisateur:", "\nAlice:", "\n"]
            )
            if isinstance(result, dict) and "choices" in result and result["choices"]:
                answer = result["choices"][0]["text"].strip()
            else:
                answer = "[ERREUR] Réponse invalide."

            if not answer or len(answer.split()) < 2:
                return "[ERREUR] Réponse trop courte ou vide."

            if should_save:
                self.save_to_memory(cleaned_prompt, answer)

            return answer
        except Exception as e:
            self.error_handler.handle_error(e, context="Génération texte", user_message="Erreur génération de texte")
            return "[ERREUR] Erreur interne lors de la génération."

    def generate_code(self, user_request: str, language: str = "Python") -> str:
        try:
            prompt = f"""Tu es un assistant expert en programmation. 
            Ne retourne que du code. Ne mets aucune explication. Réponds uniquement avec un bloc de code Markdown.

            ### Question
            {user_request.strip()}

            ### Réponse
            ```{language.lower()}
            """

            response = self.model.create_completion(
                prompt=prompt,
                max_tokens=400,
                temperature=0.1,
                top_p=1.0,
                stop=["```"]
            )

            if "choices" in response and response["choices"]:
                code = response["choices"][0]["text"].strip()
                if not code:
                    return "[ERREUR] Code vide ou invalide"
                if not code.startswith("```"):
                    code = f"```{language.lower()}\n{code}\n```"

                if "#save" in user_request:
                    self.save_to_memory(user_request.replace("#save", "").strip(), code)

                return code

            return "[ERREUR] Réponse invalide"

        except Exception as e:
            self.error_handler.handle_error(e, context="Génération code", user_message="Erreur génération de code")
            return "[ERREUR] Erreur interne lors de la génération de code."

    def generate_image(self, prompt: str) -> str:
        try:
            print("[INFO] Lancement de la génération via subprocess")
            script_path = os.path.abspath("imagesManager/generate.py")

            output = subprocess.check_output(
                ["python", script_path, "--prompt", prompt],
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120
            )

            for line in output.splitlines():
                if "#image" in line:
                    return line.strip()

            return "[ERREUR] Aucune image générée."

        except subprocess.TimeoutExpired as e:
            self.error_handler.handle_error(e, context="Génération image", user_message="Timeout génération image")
            return "[ERREUR] Timeout de génération."

        except subprocess.CalledProcessError as e:
            self.error_handler.handle_error(e, context="Génération image", user_message=f"Erreur subprocess : {e.output}")
            return "[ERREUR] Génération échouée."

        except Exception as e:
            self.error_handler.handle_error(e, context="Génération image", user_message="Erreur interne génération image")
            return "[ERREUR] Exception interne."

    def save_to_memory(self, prompt: str, response: str):
        try:
            if len(prompt) < 15 or len(response) < 5:
                return  # filtre basique
            self.db_manager.save_memory(prompt, response)
        except Exception as e:
            self.error_handler.handle_error(e, context="Sauvegarde mémoire", user_message="Erreur sauvegarde mémoire")

    def process_voice_input(self, voice_input: str):
        print(f"[VOICE INPUT] : {voice_input}")
        if not voice_input.strip():
            return "[ERREUR] Aucune entrée détectée."
        if "timeout" in voice_input.lower() or "audio incompréhensible" in voice_input.lower():
            return "[ERREUR] Entrée audio invalide."
        return self.generate(voice_input)
