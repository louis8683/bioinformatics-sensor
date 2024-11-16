import logging

LOG_LEVEL = logging.DEBUG
LOG_FORMAT = "[%(name)s] <%(levelname)s> %(message)s"
NAME = "STATE"


def config_logger(name=NAME, log_level=logging.DEBUG):

    # Create or get an existing logger
    logger = logging.getLogger(name)

    # Set the logging level and format from config
    logger.setLevel(log_level)
    
    # Create a console handler and set its format
    handler = logging.StreamHandler()
    formatter = logging.Formatter(LOG_FORMAT)
    handler.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(handler)


def get_logger(name=NAME):
    """
    Returns a logger with the specified name, configured with standard settings.
    """
    # Create or get an existing logger
    logger = logging.getLogger(name)
    
    # Check if the logger is already configured
    if not logger.hasHandlers():
        config_logger(name=name)

    return logger
