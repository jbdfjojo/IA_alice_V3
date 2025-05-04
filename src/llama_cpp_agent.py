import os
import pyttsx3
from llama_cpp import Llama
from db.mysql_manager import MySQLManager

class LlamaCppAgent:
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = None
        self.engine = pyttsx3.init()
        self.db_manager = MySQLManager(
            host="localhost",
            user="root",
            password="votre_mot_de_passe",
            database="ia_alice"
        )
        self.load_model()

    def load_model(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Le modèle n'a pas été trouvé à l'emplacement : {self.model_path}")
        self.model = Llama(model_path=self.model_path)
        print(f"[AGENT] Modèle chargé depuis {self.model_path}")

    def speak(self, text):
        self.engine.say(text)
        self.engine.runAndWait()

    def generate_response(self, prompt):
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
                max_tokens=150,
                temperature=0.7,
                top_p=0.95,
                stop=["</s>", "Alice:", "Vous:"]
            )

            answer = response['choices'][0]['text'].strip()

            self.db_manager.save_memory(prompt, answer)
            self.speak(answer)

            return answer

        except Exception as e:
            raise RuntimeError(f"[AGENT] Erreur lors de la génération : {str(e)}")
