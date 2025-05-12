import sys
import os
import json
import pyttsx3
import speech_recognition as sr
import time
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMutex
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QCheckBox, QComboBox,
    QScrollArea
)
from gui.memory_window import MemoryViewer  # fenêtre mémoire
from llama_cpp import Llama
from db.mysql_manager import MySQLManager



# Simuler un agent pour test
class LlamaCppAgent:
    def __init__(self, model_paths: dict, selected_model="Mistral-7B-Instruct"):
        model_path = model_paths.get(selected_model)

        if not model_path:
            raise ValueError(f"Aucun chemin vers le modèle '{selected_model}' fourni.")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Le modèle spécifié est introuvable : {model_path}")

        # Chargement du modèle Llama
        self.model_path = model_path
        self.model = Llama(model_path=self.model_path, n_ctx=2048)
        if not self.model:  # Vérification si le modèle est bien chargé
            raise ValueError("Le modèle n'a pas été chargé correctement.")

        self.speech_enabled = True
        self.engine = pyttsx3.init()
        self.db_manager = MySQLManager("localhost", "root", "JOJOJOJO88", "ia_alice")
        self.first_interaction = True # Charge le modèle lors de l'initialisation

    def load_model(self):
        # Charge le modèle ici à partir du chemin spécifié
        if "model_path" in self.model_paths:
            # Remplacer par le code qui charge réellement le modèle
            self.model = some_library.load(self.model_paths["model_path"])  # Remplace par la bonne méthode
            print(f"Modèle chargé depuis {self.model_paths['model_path']}")
        else:
            print("❌ Aucun chemin vers le modèle fourni.")

    def set_speech_enabled(self, enabled):
        self.speech_enabled = enabled

    def generate(self, prompt):
        return f"Réponse générée pour: {prompt}"

    def get_all_memory(self):
        return "Mémoire d'exemple."

    def predict(self, input_text):
        if not self.model:
            raise ValueError("Le modèle n'a pas été chargé correctement.")
        # Code pour générer une réponse en utilisant le modèle
        response = self.model.create_completion(
            prompt=f"Vous : {input_text}\nAlice :",
            max_tokens=200,
            temperature=0.7,
            top_p=0.9,
            stop=["\nVous:", "\nAlice:", "\n"]
        )
  # Utilise la méthode predict du modèle
        return response

def load_config():
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, "r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as e:
                print(f"[ERREUR] config.json malformé: {e}")
    return {}

def save_config(config):
    with open("config.json", "w") as file:
        json.dump(config, file, indent=4)

# THREAD POUR LE MICRO
class VoiceRecognitionThread(QThread):
    result_signal = pyqtSignal(str)

    def __init__(self, model):
        super().__init__()
        self.running = True
        self.is_paused = False
        self.is_processing_response = False
        self.mutex = QMutex()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone(device_index=1)
        self.model = model  # Le modèle que nous devons utiliser pour la réponse
        print("Liste des microphones disponibles :")
        for i, name in enumerate(sr.Microphone.list_microphone_names()):
            print(f"{i}: {name}")

    def run(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            while self.running:
                self.mutex.lock()
                if self.is_paused or self.is_processing_response:
                    self.mutex.unlock()
                    time.sleep(0.1)
                    continue

                self.mutex.unlock()

                try:
                    print("🎤 En écoute...")
                    audio = self.recognizer.listen(source, timeout=10)
                    print("🔊 Audio capté. Traitement...")
                    text = self.recognizer.recognize_google(audio, language="fr-FR")
                    print(f"✅ Texte reconnu : {text}")
                    self.is_processing_response = True  # Le modèle est en train de répondre
                    self.result_signal.emit(text)  # Émettre le texte reconnu

                    # Envoi de la requête au modèle
                    if hasattr(self, 'model'):  # Vérifie si le modèle est bien défini
                        # Utilisation de la méthode 'predict' pour obtenir une réponse
                        response = self.model.predict(text)  # Utiliser 'predict' pour obtenir une réponse
                        print(f"✅ Réponse générée : {response}")

                        # Extraire le texte de la réponse générée
                        if isinstance(response, dict) and 'choices' in response:
                            response_text = response['choices'][0]['text']
                        else:
                            response_text = str(response)  # Si la réponse n'est pas un dict, la convertir en string

                        self.result_signal.emit(response_text)  # Émettre le texte de la réponse générée
                    else:
                        print("❌ Le modèle n'est pas défini.")

                except sr.WaitTimeoutError:
                    print("⏱️ Timeout sans son.")
                    self.result_signal.emit("[Timeout sans son]")
                    self.reset_recognition()
                except sr.UnknownValueError:
                    print("🤷 Audio incompréhensible")
                    self.result_signal.emit("[Audio incompréhensible]")
                    self.reset_recognition()
                except sr.RequestError as e:
                    print(f"❌ Erreur API : {e}")
                    self.result_signal.emit("[Erreur API de reconnaissance vocale]")
                    self.reset_recognition()

    def send_to_model(self, text):
        try:
            # Appel à la méthode correcte pour générer la réponse
            response = self.model.generate(text)  # Utilisation de la méthode `generate` (à ajuster selon le modèle)
            self.display_response(response)
        except Exception as e:
            print(f"Erreur lors de l'envoi au modèle: {e}")

    def process_model_response(self, response):
        """Traite la réponse du modèle (par exemple, pour l'afficher ou la faire parler)."""
        print(f"Réponse du modèle : {response}")
        self.result_signal.emit(response)
        self.is_processing_response = False  # On a reçu la réponse, on peut relancer l'écoute

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

    def reset_recognition(self):
        """Redémarre proprement la reconnaissance vocale."""
        print("🔄 Redémarrage de la reconnaissance vocale.")
        self.stop()
        self.wait()
        self.__init__()  # Réinitialiser le thread pour tout remettre à zéro
        self.start()

    def on_response_received(self):
        """Méthode appelée après la réception de la réponse du modèle."""
        self.is_processing_response = False

class MainWindow(QWidget):
    def __init__(self, model_paths: dict):
        super().__init__()
        self.setWindowTitle("Alice - Interface")
        self.setGeometry(100, 100, 800, 600)

        self.model_paths = model_paths
        self.agent = None

        self.config = load_config()
        self.voice_input_enabled = False
        self.tts_engine = pyttsx3.init()

        self.voice_recognition_thread = None
        # Initialisation de l'interface
        self.setup_ui()

        # Initialisation du modèle à ce moment-là
        self.load_model(self.config.get("last_model", "Mistral-7B-Instruct"))

        # Initialisation du thread de reconnaissance vocale avec le modèle
        if self.agent:  # Vérifie si self.agent est bien initialisé avant de démarrer le thread
            self.voice_recognition_thread = VoiceRecognitionThread(self.agent)  # Remplacer self.model par self.agent
            self.voice_recognition_thread.result_signal.connect(self.on_text_recognized)
            self.voice_recognition_thread.start()
        else:
            print("[ERREUR] Le modèle n'a pas pu être initialisé.")

        last_model = self.config.get("last_model", "Mistral-7B-Instruct")
        index = self.model_selector.findText(last_model)
        self.model_selector.setCurrentIndex(index if index != -1 else 0)
        self.load_model(self.model_selector.currentText())

        self.voice_checkbox.setChecked(self.config.get("voice_enabled", True))

    def setup_ui(self):
        main_layout = QVBoxLayout()
        controls_layout = QHBoxLayout()

        self.voice_checkbox = QCheckBox("Voix")
        self.voice_checkbox.setChecked(True)
        self.voice_checkbox.stateChanged.connect(self.toggle_voice)

        self.memory_button = QPushButton("Mémoire")
        self.memory_button.clicked.connect(self.open_memory_window)

        self.model_selector = QComboBox()
        self.model_selector.addItems(self.model_paths.keys())
        self.model_selector.currentTextChanged.connect(self.load_model)

        self.voice_button = QPushButton("🎤 Micro: OFF")
        self.voice_button.setCheckable(True)
        self.voice_button.clicked.connect(self.toggle_voice_input)

        controls_layout.addWidget(self.voice_checkbox)
        controls_layout.addWidget(self.memory_button)
        controls_layout.addWidget(self.model_selector)
        controls_layout.addWidget(self.voice_button)

        main_layout.addLayout(controls_layout)

        self.response_box = QTextEdit()
        self.response_box.setReadOnly(True)
        main_layout.addWidget(self.response_box)

        self.waiting_label = QLabel("Alice travaille sur votre demande...")
        self.waiting_label.setAlignment(Qt.AlignCenter)
        self.waiting_label.setVisible(False)
        main_layout.addWidget(self.waiting_label)

        input_layout = QVBoxLayout()
        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Entrez votre message pour Alice...")

        buttons_layout = QHBoxLayout()
        self.send_button = QPushButton("Envoyer")
        self.send_button.clicked.connect(self.send_prompt)
        self.save_button = QPushButton("#save")
        self.save_button.clicked.connect(self.save_prompt)
        buttons_layout.addWidget(self.send_button)
        buttons_layout.addWidget(self.save_button)

        self.explanation_label = QLabel("Tapez '#save' pour enregistrer la donnée dans la mémoire.")
        self.explanation_label.setAlignment(Qt.AlignCenter)

        input_layout.addWidget(self.input_box)
        input_layout.addLayout(buttons_layout)
        input_layout.addWidget(self.explanation_label)

        main_layout.addLayout(input_layout)

        self.scroll_area = QScrollArea()
        self.image_label = QLabel()
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setVisible(False)
        main_layout.addWidget(self.scroll_area)

        self.setLayout(main_layout)

    def load_model(self, model_name):
        self.config["last_model"] = model_name
        save_config(self.config)
        model_path = self.model_paths.get(model_name)
        if model_path:
            self.agent = LlamaCppAgent(self.model_paths)
            self.agent.set_speech_enabled(self.voice_checkbox.isChecked())
        else:
            print(f"[ERREUR] Modèle introuvable: {model_name}")

    def toggle_voice(self):
        if self.agent:
            self.agent.set_speech_enabled(self.voice_checkbox.isChecked())
        self.config["voice_enabled"] = self.voice_checkbox.isChecked()
        save_config(self.config)

    def toggle_voice_input(self):
        if self.voice_input_enabled:
            self.voice_input_enabled = False
            self.voice_button.setText("🎤 Micro: OFF")
            if self.voice_recognition_thread:
                self.voice_recognition_thread.stop()
                self.voice_recognition_thread = None
        else:
            self.voice_input_enabled = True
            self.voice_button.setText("🎤 Micro: ON")
            self.voice_recognition_thread = VoiceRecognitionThread()
            self.voice_recognition_thread.result_signal.connect(self.on_text_recognized)
            self.voice_recognition_thread.start()

    def handle_voice_input(self, text):
        print(f"[VOICE INPUT] Texte reçu : {text}")
        self.input_box.setPlainText(text)
        self.send_prompt()

    def send_prompt(self):
        prompt = self.input_box.toPlainText().strip()
        if prompt:
            self.response_box.append(f"Vous: {prompt}")
            self.input_box.clear()
            self.waiting_label.setVisible(True)

            # Désactiver la reconnaissance vocale pendant que le modèle génère la réponse
            if self.voice_recognition_thread and self.voice_recognition_thread.isRunning():
                self.voice_recognition_thread.pause()  # Mettre en pause le thread de reconnaissance vocale

            response = self.agent.generate(prompt)
            self.response_box.append(f"Alice: {response}")
            self.waiting_label.setVisible(False)

            # Réactiver la reconnaissance vocale après la réponse
            if self.voice_recognition_thread and self.voice_recognition_thread.isRunning():
                self.voice_recognition_thread.resume()  # Reprendre la reconnaissance vocale

    def save_prompt(self):
        prompt = self.input_box.toPlainText().strip()
        if prompt:
            print(f"Prompt sauvegardé: {prompt}")  # à remplacer

    def open_memory_window(self):
        memory_data = self.agent.get_all_memory()
        self.memory_window = MemoryViewer(memory_data)
        self.memory_window.show()

    def start_listening(self):
        self.voice_recognition_thread.start()

    def stop_listening(self):
        self.voice_recognition_thread.pause()  # Mettre le microphone en pause
        self.text_edit.append("Microphone mis en pause.")

    def update_text(self, text):
        self.text_edit.append(f"Utilisateur : {text}")
        if text.lower() == "stop":
            self.stop_listening()
            self.text_edit.append("Reconnaissance terminée.")

    def closeEvent(self, event):
        if self.voice_recognition_thread is not None:
            self.voice_recognition_thread.stop()
        event.accept()

    def on_text_recognized(self, text):
        print(f"[VOICE INPUT] Texte reçu : {text}")

        # Vérifiez que le thread de reconnaissance vocale est bien initialisé et en cours d'exécution
        if self.voice_recognition_thread and self.voice_recognition_thread.isRunning():
            # Mettre en pause la reconnaissance vocale avant de traiter
            self.voice_recognition_thread.pause()
            
            # Traiter le texte
            if "image" in text.lower():
                self.generate_image_from_text(text)
            elif "code" in text.lower():
                self.generate_code_from_text(text)
            else:
                self.response_box.append(f"[Vous] {text}")
            
            # Ajouter un délai avant de reprendre la reconnaissance vocale
            QThread.sleep(2)  # Délai d'attente pour que le traitement se termine
            self.voice_recognition_thread.resume()  # Reprend l'écoute
        else:
            print("❌ Erreur: Le thread de reconnaissance vocale n'est pas initialisé ou non en cours d'exécution.")



if __name__ == "__main__":
    model_paths = {
        "Mistral-7B-Instruct": "C:/Users/Blazufr/Desktop/IA_alice_V3/model/mistral-7b-instruct-v0.2.Q8_0",
        "Nous-Hermes-2-Mixtral": "C:/Users/Blazufr/Desktop/IA_alice_V3/model/nous-hermes-llama2-13b.Q8_0"
    }
    app = QApplication(sys.argv)
    window = MainWindow(model_paths)
    window.show()
    sys.exit(app.exec_())
