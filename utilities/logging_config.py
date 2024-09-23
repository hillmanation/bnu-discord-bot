# logging_config.py
import logging
import colorlog


def setup_logging():
    # Define the log format with color applied to the whole message
    log_format = (
        '%(log_color)s[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s%(reset)s'
    )

    # Define the color scheme for different log levels
    log_colors = {
        'DEBUG': 'bold_blue',
        'INFO': 'bold_green',
        'WARNING': 'bold_yellow',
        'ERROR': 'bold_red',
        'CRITICAL': 'bold_red,bg_white',
    }

    # Configure the basic logging settings with color
    formatter = colorlog.ColoredFormatter(
        log_format,
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors=log_colors
    )

    # Create a handler and set the formatter
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # Get the logger instance
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Add the handler to the logger
    if not logger.hasHandlers():
        logger.addHandler(handler)

    # Configure the discord logger
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.INFO)

    # Remove existing handlers from the discord logger
    if discord_logger.hasHandlers():
        discord_logger.handlers.clear()

    # Apply the same handler to the discord logger
    discord_logger.addHandler(handler)

    return logger
