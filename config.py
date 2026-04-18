import yaml
import os
import sys
from logger_config import setup_logger

logger = setup_logger(__name__)

def load_config():
    base_path = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_path, "config.yaml")
    if not os.path.exists(full_path):
        logger.error(f"Config file not found: {full_path}")
        sys.exit(1)
    logger.info(f"Loading configuration from: {full_path}")
    with open(full_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
        logger.info("Configuration loaded successfully")
        return config_data

config = load_config()
