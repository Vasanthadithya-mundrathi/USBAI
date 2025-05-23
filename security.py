import os
import configparser
import logging
from pathlib import Path

class SecurityManager:
    def __init__(self, base_path: str = "F:\\USBAI"):
        self.base_path = Path(base_path)
        self.config = configparser.ConfigParser()
        self.load_config()

    def load_config(self):
        try:
            self.config.read(self.base_path / "config.ini")
            self.pin = self.config.get("Security", "pin")
        except Exception as e:
            logging.error(f"Config loading error: {e}")
            raise

    def authenticate(self, entered_pin: str) -> bool:
        return entered_pin == self.pin

    def wipe_logs(self):
        try:
            log_file = self.base_path / "logs" / "usbai.log"
            if log_file.exists():
                os.remove(log_file)
        except Exception as e:
            logging.error(f"Log wiping error: {e}")
