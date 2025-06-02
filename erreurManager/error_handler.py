import logging
import traceback
from PyQt5.QtWidgets import QMessageBox

# Configurer un logger simple
logger = logging.getLogger("AliceErrorHandler")
logger.setLevel(logging.DEBUG)  # À changer selon besoin
fh = logging.FileHandler("alice_errors.log", encoding="utf-8")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

class ErrorHandler:
    def __init__(self, parent_widget=None):
        self.parent_widget = parent_widget  # Pour afficher des messages QMessageBox dans l'interface

    def log_error(self, err: Exception, context: str = ""):
        err_msg = f"Exception: {str(err)}"
        if context:
            err_msg = f"{context} | {err_msg}"
        # Trace complète pour debug
        tb_str = traceback.format_exc()
        logger.error(f"{err_msg}\nTraceback:\n{tb_str}")

    def show_error_dialog(self, err: Exception, title="Erreur", user_message="Une erreur est survenue"):
        if self.parent_widget:
            QMessageBox.critical(self.parent_widget, title, f"{user_message} :\n{str(err)}")
        else:
            print(f"{title}: {user_message} : {err}")

    def handle_error(self, err: Exception, context: str = "", show_dialog=True, user_message="Une erreur est survenue"):
        self.log_error(err, context)
        if show_dialog:
            self.show_error_dialog(err, user_message=user_message)
