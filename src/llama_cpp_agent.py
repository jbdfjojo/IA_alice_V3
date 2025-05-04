import os
import pyttsx3
from llama_cpp import Llama
from db.mysql_manager import MySQLManager
import re
from PyQt5.QtCore import QThread, pyqtSignal

class LlamaThread(QThread):
    response_ready = pyqtSignal(str)

    def __init__(self, agent, prompt):
        super().__init__()
        self.agent = agent
        self.prompt = prompt

    def run(self):
        """Exécute la génération de la réponse dans un thread séparé."""
        try:
            response = self.agent.generate(self.prompt)  # appel à generate (corrigé)
            self.response_ready.emit(response)
        except Exception as e:
            self.response_ready.emit(f"[ERREUR] [AGENT] Erreur lors de la génération : {str(e)}")


class LlamaCppAgent:
    def __init__(self, model_path):
        self.model_path = model_path
        self.engine = pyttsx3.init()
        print(f"[AGENT] Chargement du modèle depuis {model_path}")
        self.model = Llama(model_path=model_path, n_ctx=2048)
        self.db_manager = MySQLManager(
            host="localhost",
            user="root",
            password="JOJOJOJO88",
            database="ia_alice"
        )

    def is_important(self, prompt: str, response: str) -> bool:
        prompt = prompt.strip().lower()

        banal = ["bonjour", "salut", "yo", "ok", "d'accord", "merci", "au revoir", "oui", "non", "ça va", "super", "cool"]

        keywords = ["faire", "créer", "projet", "problème", "résoudre", "code", "expliquer", "fonction", "installer", "comment", "aide", "python", "qt", "mysql"]

        if len(prompt) < 15 or any(b in prompt for b in banal):
            return False

        if re.search(r"\b(je|tu|il|elle|nous|vous|ils|elles|peux|veux|sais|dois|fais|est|as|ai|vais|serai|aurai)\b", prompt):
            return True

        if any(k in prompt for k in keywords) or "?" in prompt:
            return True

        return False

    def generate(self, prompt):
        print(f"[AGENT] Génération de réponse pour le prompt: {prompt}")
        try:
            if "bonjour" in prompt.lower() or "salut" in prompt.lower():
                return "Bonjour ! Comment puis-je vous aider ?"

            full_prompt = (
                "Tu es une IA qui répond uniquement aux questions posées en français. "
                "Ne réponds pas par des monologues ou des réponses non demandées.\n\n"
                f"{prompt}"
            )

            response = self.model.create_completion(
                prompt=full_prompt,
                max_tokens=1500,
                temperature=0.7,
                top_p=0.95,
                stop=["</s>", "Alice:", "Vous:"]
            )

            answer = response['choices'][0]['text'].strip()

            if self.is_important(prompt, answer):
                self.db_manager.save_memory(prompt, answer)

            self.speak(answer)
            return answer

        except Exception as e:
            raise RuntimeError(f"[AGENT] Erreur lors de la génération : {str(e)}")

    def speak(self, text):
        self.engine.say(text)
        self.engine.runAndWait()
