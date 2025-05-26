import os
import argparse
from datetime import datetime
from diffusers import StableDiffusionPipeline
import torch

try:
    import torch_directml
    USE_DIRECTML = True
except ImportError:
    USE_DIRECTML = False


def generate_image(prompt: str, output_path: str = None):
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "stable-diffusion-v1-5"))
    if not os.path.exists(model_path):
        print(f"[ERREUR] Le modèle n'existe pas à : {model_path}")
        return "[ERREUR] Modèle introuvable"

    try:
        print(f"[INFO] Chargement du modèle depuis : {model_path}")
        pipe = StableDiffusionPipeline.from_pretrained(model_path, safety_checker=None)

        # 🧠 Tentative d'utilisation DirectML
        if USE_DIRECTML:
            try:
                device = torch_directml.device()
                pipe.to(device)
                print("[INFO] Utilisation de DirectML pour l’inférence.")
            except Exception as dml_error:
                print(f"[AVERTISSEMENT] DirectML indisponible : {dml_error}")
                pipe.to("cpu")
                print("[INFO] Repli sur CPU.")
        else:
            pipe.to("cpu")
            print("[INFO] DirectML non disponible → CPU utilisé.")

        # Génération de l’image
        image = pipe(prompt, height=384, width=384, num_inference_steps=25).images[0]

        filename = f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_path = os.path.join("images", filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        image.save(output_path)

        print(f"[SUCCÈS] Image sauvegardée : {output_path}")
        return f"[Image générée] #image {output_path}"

    except Exception as e:
        print(f"[ERREUR] Échec génération image : {str(e)}")
        return f"[ERREUR] {str(e)}"
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Générateur d'image Stable Diffusion")
    parser.add_argument("--prompt", type=str, required=True)
    parser.add_argument("--output", type=str, default="images/generated_image.png")
    args = parser.parse_args()

    result = generate_image(args.prompt, args.output)

    # 🔽 Toujours afficher le résultat final pour le subprocess
    print(result)


