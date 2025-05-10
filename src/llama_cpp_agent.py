# src/agent/llama_cpp_agent.py
import os
import pyttsx3
from llama_cpp import Llama
from db.mysql_manager import MySQLManager
import re
import subprocess
from PyQt5.QtCore import QThread, pyqtSignal

class LlamaThread(QThread):
    response_ready = pyqtSignal(str)

    def __init__(self, agent, prompt):
        super().__init__()
        self.agent = agent
        self.prompt = prompt

    def run(self):
        try:
            if self.prompt.strip():
                response = self.agent.generate(self.prompt)
                self.response_ready.emit(response)
            else:
                self.response_ready.emit("Aucune entrée valide détectée.")
        except Exception as e:
            self.response_ready.emit(f"[ERREUR] [AGENT] Erreur lors de la génération : {str(e)}")

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

        if "image" in prompt.lower():
            return self.generate_image(prompt)

        cleaned_prompt = prompt.replace("#save", "").strip()
        force_save = "#save" in prompt
        memory = self.db_manager.fetch_last_memories(5)

        memory_context = ""
        for old_prompt, old_response in reversed(memory):
            memory_context += f"Alice : {old_response}\nVous : {old_prompt}\n"

        full_prompt = (
            "Tu es une IA créative qui génère des réponses adaptées aux questions posées en français.\n\n"
            f"{memory_context}\nVous : {cleaned_prompt}\nAlice :"
        )

        response = self.model.create_completion(
            prompt=full_prompt,
            max_tokens=500,
            temperature=0.9,
            top_p=0.95,
            stop=["</s>", "Alice:", "Vous:"]
        )
        answer = response['choices'][0]['text'].strip()

        if force_save or self.is_important(cleaned_prompt, answer):
            self.db_manager.save_memory(cleaned_prompt, answer)

        if self.speech_enabled:
            self.speak(answer)

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

    def is_important(self, prompt: str, response: str) -> bool:
        return len(prompt) >= 15
