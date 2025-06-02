import speech_recognition as sr
from PyQt5.QtCore import QThread, pyqtSignal

class VoiceRecognitionThread(QThread):
    recognized = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._running = True  # Flag pour contrôler la boucle
    
    def run(self):
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone(device_index=1) as source:
                recognizer.adjust_for_ambient_noise(source)
                while self._running:
                    try:
                        audio = self.recognizer.listen(source, timeout=30, phrase_time_limit=15)
                        text = recognizer.recognize_google(audio, language="fr-FR")
                        self.recognized.emit(text)
                    except sr.WaitTimeoutError:
                        # Timeout d'écoute, on continue la boucle
                        continue
                    except sr.UnknownValueError:
                        self.error.emit("⚠️ Je n'ai pas compris. Veuillez réessayer.")
                    except sr.RequestError:
                        self.error.emit("⚠️ Erreur avec le service de reconnaissance vocale.")
                    except Exception as e:
                        self.error.emit(f"[ERREUR micro] : {str(e)}")
        except Exception as e:
            self.error.emit(f"[ERREUR initialisation micro] : {str(e)}")
    
    def stop(self):
        self._running = False
        self.wait()  # Attend que le thread se termine proprement
