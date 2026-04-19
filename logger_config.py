"""
Logger configuration module.

This module provides a centralized logger setup function with consistent
formatting across all application modules.
"""
import logging


def setup_logger(name: str) -> logging.Logger:
    """
    Creates and configures a logger with consistent formatting.

    Args:
        name: The name of the module (usually __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Avoid adding multiple handlers if logger already has them
    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
