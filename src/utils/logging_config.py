"""Logging configuration for S3MANAGER"""
import logging
import logging.handlers
from pathlib import Path

from src.utils.paths import log_file_path


def setup_logging(log_level=logging.INFO, log_file=None):
    """
    Setup logging configuration for the application

    Args:
        log_level: Logging level (default: INFO)
        log_file: Path to log file (default: ~/.s3manager/app.log)

    Returns:
        Logger instance
    """
    if log_file is None:
        log_file = log_file_path()
    else:
        log_file = Path(log_file)
    
    # Create logs directory if it doesn't exist
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create root logger
    logger = logging.getLogger('s3manager')
    logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler - RotatingFileHandler (max 10MB, keep 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # File gets all logs
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Console handler - only INFO and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger

def get_logger(name=None):
    """
    Get a logger instance
    
    Args:
        name: Logger name (default: 's3manager')
    
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f's3manager.{name}')
    return logging.getLogger('s3manager')
