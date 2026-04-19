"""
Configuration management for DozerX Modular Service.

This module loads and provides access to application configuration from YAML file.
"""
import os
import sys
import yaml
from logger_config import setup_logger

logger = setup_logger(__name__)


def load_config():
    """
    Load configuration from YAML file.

    Returns:
        dict: Configuration data from config.yaml

    Raises:
        SystemExit: If config file is not found
    """
    base_path = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_path, "config.yaml")
    if not os.path.exists(full_path):
        logger.error("Config file not found: %s", full_path)
        sys.exit(1)
    logger.info("Loading configuration from: %s", full_path)
    with open(full_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
        logger.info("Configuration loaded successfully")
        return config_data


config = load_config()
