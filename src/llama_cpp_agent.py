import os
import pyttsx3
from llama_cpp import Llama

class LlamaCppAgent:
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = None
        self.engine = pyttsx3.init()
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
            # Si le prompt est une salutation, répondre uniquement par une salutation.
            if "bonjour" in prompt.lower() or "salut" in prompt.lower():
                return "Bonjour ! Comment puis-je vous aider ?"

            # Spécification d'une réponse uniquement pour les questions posées.
            full_prompt = f"Tu es une IA qui répond uniquement aux questions posées en français. Ne réponds pas par des monologues ou des réponses non demandées.\n\n{prompt}"

            # Génération de la réponse avec les bons paramètres
            response = self.model.create_completion(
                prompt=full_prompt,
                max_tokens=150,
                temperature=0.7,
                top_p=0.95,
                stop=["</s>", "Alice:", "Vous:"]
            )

            # Récupération de la réponse
            answer = response['choices'][0]['text'].strip()

            # Lire la réponse à haute voix
            self.speak(answer)

            return answer

        except Exception as e:
            raise RuntimeError(f"[AGENT] Erreur lors de la génération : {str(e)}")








