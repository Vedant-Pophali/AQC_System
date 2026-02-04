import logging
import sys
from typing import Optional

def setup_logger(name: str, level: int = logging.INFO, log_file: Optional[str] = None) -> logging.Logger:
    """
    Configures a standardized logger for the AQC system.
    
    Args:
        name: The name of the module (usually __name__).
        level: Logging threshold (default: logging.INFO).
        log_file: Optional path to write logs to a file.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    
    # Prevent duplicate logs if logger is already configured
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(level)
    
    # Format: [2026-01-27 10:00:00] [INFO] [artifact_scorer] Loading model...
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File Handler (Optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger