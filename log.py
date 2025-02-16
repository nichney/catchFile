import logging
from logging.handlers import RotatingFileHandler

class Logger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            log_handler = RotatingFileHandler('catchfile.log', maxBytes=1024*1024, backupCount=3)
            log_formatter = logging.Formatter('[%(asctime)s] %(message)s (%(funcName)s)')
            log_handler.setFormatter(log_formatter)
            log_handler.setLevel(logging.INFO)
            self.logger.addHandler(log_handler)

    def get_logger(self):
        return self.logger