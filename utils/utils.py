from PyQt5.QtCore import Qt, QRunnable
from PyQt5.QtWidgets import QLabel, QTextEdit


class RunnableFunc(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        self.fn()


class StyledLabel(QLabel):
    def __init__(self, html):
        super().__init__(html)
        self.setWordWrap(True)
        self.setStyleSheet(
            "margin-top: 2px; margin-bottom: 2px; line-height: 1.2em; padding: 0;"
        )


class InputTextEdit(QTextEdit):
    def __init__(self, parent=None, submit_callback=None):
        super().__init__(parent)
        self.submit_callback = submit_callback

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return and not event.modifiers() & Qt.ShiftModifier:
            if self.submit_callback:
                self.submit_callback()
            event.accept()  # Empêche le retour à la ligne
        else:
            super().keyPressEvent(event)
