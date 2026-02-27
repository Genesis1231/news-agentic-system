import logging
from pathlib import Path
from threading import Lock
from logging.handlers import RotatingFileHandler

_logger_lock = Lock()
_logger_initialized = False

def setup_logger(
    log_level: int = logging.DEBUG,  # or logging.ERROR
    log_file: str | None = None
) -> logging.Logger:
    """
    Configure and return a logger with both console and file handlers.
    
    Args:
        log_level: Logging level (default: logging.INFO)
        log_file: Path to log file (default: 'burst.log')
    """
    
    global _logger_initialized
    
    with _logger_lock:
        # Create a logger
        logger = logging.getLogger(__name__)
        if _logger_initialized:
            return logger

        logger.setLevel(log_level)
        logger.propagate = False
        logger.handlers = [] # Clear existing handlers

        # Create formatters
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(filename)s: %(funcName)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File Handler (Rotating)
        if log_file:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    _logger_initialized = True

    return logger

# Create default logger instance
logger = setup_logger()
