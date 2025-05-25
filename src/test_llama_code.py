from llama_cpp_agent import LlamaCppAgent

model_paths = {
    "Mistral-7B-Instruct": "G:/IA_alice_V3/model/mistral-7b-instruct-v0.2.Q8_0.gguf"
}

# Initialise l'agent
agent = LlamaCppAgent(model_paths)

# Prompt de test
request = "Crée une fonction Python pour inverser une chaîne de caractères"
language = "Python"

# Appel de la génération de code
markdown_code = agent.generate_code(request, language=language)

# Affichage brut
print("[TEST] Code Markdown généré :\n")
print(markdown_code)

# Vérification format Markdown
if markdown_code.startswith("```python") and markdown_code.endswith("```"):
    print("\n✅ Le bloc de code est bien formaté en Markdown.")
else:
    print("\n❌ Le bloc de code n'est pas correctement encadré par des balises Markdown.")
