# utils/logger.py
import logging
from datetime import datetime
from config import LOG_FILE


# Configure logging
def configure_logger():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Add a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s",
                                      datefmt="%Y-%m-%d %H:%M:%S", )
    console_handler.setFormatter(console_format)
    logging.getLogger('').addHandler(console_handler)

def log(message, level=logging.INFO):
    """Logs a message to the console and the log file."""
    logging.log(level, message)


def log_exception(e, message):
    """Logs an exception with a formatted message."""
    log(f"{message}: {e}", level=logging.ERROR)