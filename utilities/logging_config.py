# logging_config.py
import logging


def setup_logging():
    # Define the log format
    log_format = '[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s'
    # Configure the basic logging settings
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # Get the logger instance
    logger = logging.getLogger(__name__)
    return logger
