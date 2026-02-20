from core.config import config

from .logging import LoggerFactory, TelegramLogger

LOG_FILE = config.LOG_FILE
TELEGRAM_LOG_FILE = config.TELEGRAM_LOG_FILE
MAX_MB = config.LOG_MAX_MB
BACKUP_COUNT = config.LOG_BACKUP_COUNT

logger = LoggerFactory(
    file_name=LOG_FILE,
    maxMB=MAX_MB,
    backup_count=BACKUP_COUNT,
)

telegram_logger = TelegramLogger(
    file_name=TELEGRAM_LOG_FILE,
    maxMB=MAX_MB,
    backup_count=BACKUP_COUNT,
)
