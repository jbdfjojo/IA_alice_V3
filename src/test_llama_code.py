from llama_cpp_agent import LlamaCppAgent

model_paths = {"Mistral-7B-Instruct": "G:/IA_alice_V3/model/mistral-7b-instruct-v0.2.Q8_0.gguf"}
agent = LlamaCppAgent(model_paths)
print(agent.generate_code("affiche l'heure actuelle", language="Python"))

