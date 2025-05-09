import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import torch
from diffusers import StableDiffusionPipeline

# Chemin du modèle
MODEL_PATH = "C:/Users/Blazufr/Desktop/IA_alice_V3/src/agent/stable-diffusion-v1-5"

# Détection de l'accélérateur
device = "cuda" if torch.cuda.is_available() else "cpu"

# Charger sans float16 si on est sur CPU
if device == "cuda":
    pipe = StableDiffusionPipeline.from_pretrained(MODEL_PATH, torch_dtype=torch.float16)
else:
    pipe = StableDiffusionPipeline.from_pretrained(MODEL_PATH)

pipe = pipe.to(device)

def generate_image(prompt: str, output_path: str = "images/output.png"):
    print(f"[IMAGE] Génération pour : {prompt}")
    image = pipe(prompt).images[0]
    image.save(output_path)
    print(f"[IMAGE] Image enregistrée à : {output_path}")
    return output_path


if __name__ == "__main__":
    generate_image("chat cybernétique dans une ville futuriste", "test_image.png")
