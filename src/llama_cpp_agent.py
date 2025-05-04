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
        try:
            # Assurez-vous de ne pas envoyer de prompt vide
            if self.prompt.strip():
                response = self.agent.generate(self.prompt)
                self.response_ready.emit(response)
            else:
                self.response_ready.emit("Aucune entrée valide détectée.")
        except Exception as e:
            self.response_ready.emit(f"[ERREUR] [AGENT] Erreur lors de la génération : {str(e)}")

class LlamaCppAgent:
    def __init__(self, model_path):
        self.model_path = model_path
        self.speech_enabled = True
        self.engine = pyttsx3.init()
        print(f"[AGENT] Chargement du modèle depuis {model_path}")
        self.model = Llama(model_path=model_path, n_ctx=2048)
        self.db_manager = MySQLManager(
            host="localhost",
            user="root",
            password="JOJOJOJO88",
            database="ia_alice"
        )
        self.first_interaction = True  # Variable pour vérifier si c'est la première interaction

    def set_speech_enabled(self, enabled: bool):
        self.speech_enabled = enabled

    def reset_memory(self):
        # Méthode pour nettoyer la mémoire
        self.db_manager.clear_memory()
        print("[AGENT] Mémoire réinitialisée.")

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

    def generate(self, prompt: str) -> str:
    # Vérifier si le prompt est vide ou contient uniquement des espaces
        prompt = prompt.strip()
        if not prompt and self.first_interaction:
            self.first_interaction = False
            print("[AGENT] Première interaction détectée, aucune réponse générée.")
            return "Bonjour ! Comment puis-je vous aider aujourd'hui ?"

        if not prompt:
            print("[AGENT] Aucune entrée utilisateur détectée. Aucun prompt généré.")
            return ""  # Rien à répondre si aucun prompt n'est donné.

        print(f"[AGENT] Génération de réponse pour le prompt: {prompt}")

        try:
            force_save = "#save" in prompt
            cleaned_prompt = prompt.replace("#save", "").strip()

            try:
                memory = self.db_manager.fetch_last_memories(5)
            except Exception as db_err:
                print(f"[ERREUR] [BDD] {db_err}")
                memory = []

            memory_context = ""
            for old_prompt, old_response in reversed(memory):
                # Inverser l'ordre : d'abord la réponse d'Alice, puis la question de l'utilisateur
                memory_context += f"Alice : {old_response}\nVous : {old_prompt}\n"

            full_prompt = (
                "Tu es une IA créative qui génère des réponses adaptées aux questions posées en français. "
                "Réponds de manière concise et pertinente, tout en utilisant des informations passées lorsque cela est utile. "
                "Tu es libre de donner des réponses créatives selon le contexte.\n\n"
                f"{memory_context}\n"
                f"Vous : {cleaned_prompt}\nAlice :"
            )

            # Augmenter max_tokens, temperature et top_p pour une réponse plus longue et créative
            response = self.model.create_completion(
                prompt=full_prompt,
                max_tokens=500,  # Augmenter le nombre de tokens pour permettre une réponse détaillée
                temperature=0.9,  # Plus créatif et varié
                top_p=0.95,
                stop=["</s>", "Alice:", "Vous:"]
            )

            answer = response['choices'][0]['text'].strip()

            if force_save or self.is_important(cleaned_prompt, answer):
                self.db_manager.save_memory(cleaned_prompt, answer)

            if self.speech_enabled:
                self.speak(answer)

            return answer

        except Exception as e:
            raise RuntimeError(f"[AGENT] Erreur lors de la génération : {str(e)}")

    def speak(self, text: str):
        try:
            if self.speech_enabled:
                self.engine.say(text)
                self.engine.runAndWait()
        except Exception as e:
            print(f"[ERREUR] [VOIX] {e}")
