
# === logger.py ===
"""
Logging Configuration Module
"""

import logging
from datetime import datetime
from loguru import logger as loguru_logger
import sys

def setup_logger():
    """Setup logging configuration"""
    # Configure loguru for file logging
    loguru_logger.remove()  # Remove default handler
    
    # Add file handler
    loguru_logger.add(
        "vpn_simulator.log",
        rotation="10 MB",
        retention="1 week",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="INFO"
    )
    
    # Add console handler for development
    loguru_logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        level="INFO"
    )
    
    return loguru_logger

def log_event(message):
    """Log VPN events"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[VPN EVENT] {message}"
    loguru_logger.info(log_message)

