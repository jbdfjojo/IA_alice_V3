import json
import pyttsx3
import subprocess
from llama_cpp import Llama
from db_mysql.mysql_manager import MySQLManager
import threading
from datetime import datetime
from images import generate 
from images.generate import generate_image
from diffusers import StableDiffusionPipeline
import torch_directml
import os


class LlamaCppAgent:
    def __init__(self, model_paths: dict, selected_model="Mistral-7B-Instruct"):
        self.model_paths = model_paths
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
                print(f"[ERREUR VOCALE] : {e}")

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
            return f"[ERREUR] Erreur génération : {str(e)}"

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
            return f"[ERREUR] Exception : {e}"

    def generate_image(self, prompt: str) -> str:
        try:
            print("[INFO] Lancement de la génération via subprocess")
            script_path = os.path.abspath("images/generate.py")

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

        except subprocess.TimeoutExpired:
            return "[ERREUR] Timeout de génération."
        except subprocess.CalledProcessError as e:
            return f"[ERREUR] Génération échouée : {e.output}"
        except Exception as e:
            return f"[ERREUR] Exception : {str(e)}"

    def save_to_memory(self, prompt: str, response: str):
        try:
            if len(prompt) < 15 or len(response) < 5:
                return  # filtre basique
            self.db_manager.save_memory(prompt, response)
        except Exception as e:
            print(f"[ERREUR MÉMOIRE] : {e}")

    def process_voice_input(self, voice_input: str):
        print(f"[VOICE INPUT] : {voice_input}")
        if not voice_input.strip():
            return "[ERREUR] Aucune entrée détectée."
        if "timeout" in voice_input.lower() or "audio incompréhensible" in voice_input.lower():
            return "[ERREUR] Entrée audio invalide."
        return self.generate(voice_input)
