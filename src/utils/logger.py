"""
Production logging system
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

class ProductionLogger:
    def __init__(self, log_file: Path = None, level: str = "INFO"):
        self.logger = logging.getLogger("audio2cinema")
        self.logger.setLevel(getattr(logging, level.upper()))

        # Prevent duplicate handlers
        if self.logger.handlers:
            return

        # Console handler
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
        console.setFormatter(console_fmt)
        self.logger.addHandler(console)

        # File handler
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            file_handler.setFormatter(file_fmt)
            self.logger.addHandler(file_handler)

    def info(self, msg: str):
        self.logger.info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def debug(self, msg: str):
        self.logger.debug(msg)

    def stage_start(self, stage_num: int, description: str):
        self.logger.info(f"{'='*60}")
        self.logger.info(f"STAGE {stage_num}: {description}")
        self.logger.info(f"{'='*60}")

    def stage_complete(self, stage_num: int):
        self.logger.info(f"STAGE {stage_num} COMPLETE")
        self.logger.info(f"{'='*60}")
