# logging_config.py
import os
import logging
import colorlog


def get_module_names(root_directory):
    module_names = []
    for root, dirs, files in os.walk(root_directory):
        for file in files:
            if file.endswith(".py"):
                # Extract just the base file name (without .py extension)
                module_name = os.path.splitext(file)[0]
                module_names.append(module_name)
    return module_names


def get_max_module_length(directory):
    module_names = get_module_names(directory)
    return max(len(module) for module in module_names) if module_names else 0


def setup_logging():
    # Example: Use the project root directory (one level above src, api, utilities, etc.)
    root_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    # Find the maximum module length so that we can define log module field width
    max_module_length = get_max_module_length(root_directory)
    # Define the log format with color applied to the whole message
    log_format = (
        f"%(log_color)s[%(asctime)s] [%(levelname)-8s] "
        f"[%(module)-{max_module_length}s]: %(message)s%(reset)s"
    )

    # Define the color scheme for different log levels
    log_colors = {
        'DEBUG': 'bold_green',
        'INFO': 'bold_blue',
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
