import speech_recognition as sr

print("Liste des micros disponibles :")
for i, name in enumerate(sr.Microphone.list_microphone_names()):
    print(f"{i}: {name}")

mic_index = None  # ou mets un index ici si tu sais lequel utiliser

recognizer = sr.Recognizer()

try:
    with sr.Microphone(device_index=mic_index) as source:
        print("Calibrage du bruit ambiant...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Parle maintenant :")
        audio = recognizer.listen(source, timeout=5)
        print("Reconnaissance en cours...")
        texte = recognizer.recognize_google(audio, language="fr-FR")
        print("Texte reconnu :", texte)
except Exception as e:
    print("Erreur:", e)
