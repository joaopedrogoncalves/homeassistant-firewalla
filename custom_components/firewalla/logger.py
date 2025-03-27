"""Logging utilities for Firewalla integration."""
import logging
from typing import Any, Callable, Optional

# Create a module level logger
_LOGGER = logging.getLogger(__name__)


def get_logger() -> logging.Logger:
    """Get the logger instance for the integration."""
    return logging.getLogger(__name__.split('.')[0])


def log_config_entry_setup(logger: logging.Logger, entry_id: str) -> None:
    """Log the start of config entry setup."""
    logger.info("Setting up Firewalla integration for config entry: %s", entry_id)


def log_exception(
    logger: logging.Logger, 
    message: str, 
    exception: Exception, 
    level: int = logging.ERROR
) -> None:
    """Log an exception with consistent formatting."""
    logger.log(
        level, 
        "%s: %s (%s)", 
        message, 
        str(exception), 
        type(exception).__name__
    )


def log_api_error(
    logger: logging.Logger, 
    endpoint: str, 
    status_code: int, 
    response_text: str
) -> None:
    """Log API errors with consistent formatting."""
    logger.error(
        "Error calling Firewalla API endpoint '%s': HTTP %s - %s",
        endpoint,
        status_code,
        response_text
    )


def create_device_entity_logger(device_name: str, entity_type: str) -> Callable:
    """Create a logger function for device entities.
    
    Returns a function that can be used to log messages with device context.
    """
    def log_func(logger: logging.Logger, message: str, *args: Any, 
                level: int = logging.INFO) -> None:
        """Log a message with device context."""
        logger.log(level, f"[{device_name}] [{entity_type}] {message}", *args)
    
    return log_func