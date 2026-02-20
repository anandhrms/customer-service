import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler


class LoggerFactory:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(LoggerFactory, cls).__new__(cls)
        return cls._instance

    def __init__(self, file_name: str, maxMB: int, backup_count: int):
        if not hasattr(self, "_initialized"):
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.DEBUG)

            size_handler = RotatingFileHandler(
                filename=file_name,
                mode="a",
                maxBytes=maxMB * 1024 * 1024,
                backupCount=backup_count,
            )

            stream_handler = logging.StreamHandler(sys.stdout)

            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            size_handler.setFormatter(formatter)
            stream_handler.setFormatter(formatter)

            logger.addHandler(size_handler)
            logger.addHandler(stream_handler)

            self.logger = logger
            self._initialized = True

    def info(self, message):
        self.logger.info(msg=message)

    def error(self, message):
        self.logger.error(msg=message)

    def log_err_with_line(self, e: Exception):
        tb = traceback.extract_tb(e.__traceback__)

        # pick the deepest frame that is NOT from site-packages (i.e., likely your code)
        chosen = None
        for frame in reversed(tb):
            path = frame.filename.replace("\\", "/")
            if "/site-packages/" not in path and "/dist-packages/" not in path:
                chosen = frame
                break

        # fallback to last frame
        if chosen is None:
            chosen = tb[-1] if tb else None

        line_no = chosen.lineno if chosen else "NA"
        filename = os.path.basename(chosen.filename) if chosen else "NA"
        func = frame.name if frame else "NA"
        code_line = (frame.line or "").strip() if frame else ""

        msg = str(e)

        self.logger.error(
            f"Error -  {filename}:{line_no} | message - {msg} | function - {func}() | {code_line}"
        )


class TelegramLogger:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(TelegramLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self, file_name: str, maxMB: int, backup_count: int):
        if not hasattr(self, "_initialized"):
            logger = logging.getLogger("telegram_logger")
            logger.setLevel(logging.DEBUG)

            size_handler = RotatingFileHandler(
                filename=file_name,
                mode="a",
                maxBytes=maxMB * 1024 * 1024,
                backupCount=backup_count,
            )

            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            size_handler.setFormatter(formatter)

            logger.addHandler(size_handler)

            self.logger = logger
            self._initialized = True

    def info(self, message):
        self.logger.info(msg=message)

    def error(self, message):
        self.logger.error(msg=message)
