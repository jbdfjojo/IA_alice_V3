# src/agent/generate.py
import argparse
import os
from diffusers import StableDiffusionPipeline

def generate_image(prompt: str, output_path: str = "images/generated_image.png"):
    model_path = "C:/Users/Blazufr/Desktop/IA_alice_V3/src/agent/stable-diffusion-v1-5"
    pipe = StableDiffusionPipeline.from_pretrained(model_path, safety_checker=None)
    pipe.to("cpu")


    image = pipe(prompt).images[0]
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    image.save(output_path)
    print(f"[GENERATION] Image sauvegardée : {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", type=str, required=True)
    parser.add_argument("--output", type=str, default="images/generated_image.png")
    args = parser.parse_args()

    generate_image(args.prompt, args.output)
