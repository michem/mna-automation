# utils/logger.py

import logging


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Sets up and returns a logger with the specified name and level.

    Args:
        name (str): The name of the logger.
        level (int): The logging level. Defaults to logging.INFO.

    Returns:
        logging.Logger: The configured logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)

    logger.addHandler(ch)

    return logger
