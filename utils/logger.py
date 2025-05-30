# Outils de journalisation des évolutions
import logging

class Logger:
    def __init__(self, log_file='evolution.log'):
        self.logger = logging.getLogger('AI Evolution')
        self.logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def log(self, message):
        self.logger.info(message)
