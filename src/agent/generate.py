# src/agent/generate.py
import argparse
import os
import torch
from diffusers import StableDiffusionPipeline

def generate_image(prompt: str, output_path: str = "images/generated_image.png"):
    model_path = os.path.abspath("src/agent/stable-diffusion-v1-5")

    # Vérifie l'existence du modèle
    if not os.path.exists(model_path):
        print(f"[ERREUR] Le modèle n'existe pas à l'emplacement : {model_path}")
        return

    try:
        print(f"[INFO] Chargement du modèle depuis : {model_path}")
        pipe = StableDiffusionPipeline.from_pretrained(model_path, safety_checker=None)

        # CPU ou GPU selon disponibilité
        device = "cuda" if torch.cuda.is_available() else "cpu"
        pipe.to(device)
        print(f"[INFO] Utilisation de l'appareil : {device}")

        # Génération
        print(f"[INFO] Génération de l'image à partir du prompt : {prompt}")
        image = pipe(prompt).images[0]

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        image.save(output_path)
        print(f"[SUCCÈS] Image sauvegardée dans : {output_path}")

    except Exception as e:
        print(f"[ERREUR] Exception lors de la génération d'image : {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Générateur d'images Stable Diffusion")
    parser.add_argument("--prompt", type=str, required=True, help="Prompt textuel pour générer l'image.")
    parser.add_argument("--output", type=str, default="images/generated_image.png", help="Chemin du fichier de sortie")
    args = parser.parse_args()

    generate_image(args.prompt, args.output)
