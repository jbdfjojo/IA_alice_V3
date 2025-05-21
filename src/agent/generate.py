import argparse
import os
from diffusers import StableDiffusionPipeline
import torch_directml

def generate_image(prompt: str, output_path: str = "images/generated_image.png"):
    model_path = os.path.abspath("src/agent/stable-diffusion-v1-5")

    if not os.path.exists(model_path):
        print(f"[ERREUR] Le modèle n'existe pas à : {model_path}")
        return

    try:
        print(f"[INFO] Chargement du modèle depuis : {model_path}")
        pipe = StableDiffusionPipeline.from_pretrained(model_path, safety_checker=None)

        device = torch_directml.device()
        pipe.to(device)

        print(f"[INFO] Génération avec DirectML (AMD GPU) pour : {prompt}")
        image = pipe(prompt).images[0]

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        image.save(output_path)
        print(f"[SUCCÈS] Image sauvegardée : {output_path}")

    except Exception as e:
        print(f"[ERREUR] Échec génération image : {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Générateur d'image Stable Diffusion")
    parser.add_argument("--prompt", type=str, required=True)
    parser.add_argument("--output", type=str, default="images/generated_image.png")
    args = parser.parse_args()

    generate_image(args.prompt, args.output)
