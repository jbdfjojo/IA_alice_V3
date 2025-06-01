from PyQt5.QtCore import QRunnable
from PyQt5.QtWidgets import QLabel

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
