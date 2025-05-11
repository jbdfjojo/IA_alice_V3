import speech_recognition as sr
from PyQt5.QtCore import QThread, pyqtSignal

class VoiceRecognitionThread(QThread):
    recognized = pyqtSignal(str)
    error = pyqtSignal(str)

    def run(self):
        recognizer = sr.Recognizer()
        mic = sr.Microphone()

        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.listen(source, timeout=5)

            text = recognizer.recognize_google(audio, language="fr-FR")
            self.recognized.emit(text)

        except sr.UnknownValueError:
            self.error.emit("⚠️ Je n'ai pas compris. Veuillez réessayer.")
        except sr.RequestError:
            self.error.emit("⚠️ Erreur avec le service de reconnaissance vocale.")
        except Exception as e:
            self.error.emit(f"[ERREUR micro] : {str(e)}")
