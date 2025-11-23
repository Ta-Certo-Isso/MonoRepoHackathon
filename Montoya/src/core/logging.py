import logging
import sys
from src.core.config import settings

def setup_logging():
    """
    Configure logging for the application.
    """
    log_level = logging.INFO
    if settings.ENVIRONMENT == "development":
        log_level = logging.DEBUG
        
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set lower level for some noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    """
    return logging.getLogger(name)
