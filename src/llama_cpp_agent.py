import os
from llama_cpp import Llama

class LlamaCppAgent:
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = None
        self.load_model()

    def load_model(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Le modèle n'a pas été trouvé à l'emplacement : {self.model_path}")
        self.model = Llama(model_path=self.model_path)
        print(f"[AGENT] Modèle chargé depuis {self.model_path}")

    def generate_response(self, prompt):
            print(f"[AGENT] Génération de réponse pour le prompt: {prompt}")
            try:
                # Ajout d'une instruction pour donner un ton plus amical et naturel
                full_prompt = f"Tu es Alice, une intelligence artificielle avancée. Tu dois répondre de manière courtoise et humaine.\n\nUtilise un langage naturel, et réponds de manière cohérente à ce qui est demandé. Si quelqu'un te dit 'bonjour', réponds poliment.\n\n{prompt}"

                # Génération avec la bonne méthode et bons arguments
                response = self.model.create_completion(
                    prompt=full_prompt,
                    max_tokens=150,
                    temperature=0.7,
                    top_p=0.95,
                    stop=["</s>", "Alice:", "Vous:"]
                )

                return response['choices'][0]['text'].strip()

            except Exception as e:
                raise RuntimeError(f"[AGENT] Erreur lors de la génération : {str(e)}")
