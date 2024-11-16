import logging
import struct

from .ble_commands import BLECommands

LOG_LEVEL = logging.DEBUG
LOG_FORMAT = "[%(name)s] <%(levelname)s> %(message)s"
NAME = "BLE logger"

def get_logger(name=NAME):
    """
    Returns a logger with the specified name, configured with standard settings.
    """
    # Create or get an existing logger
    logger = logging.getLogger(name)
    
    # Check if the logger is already configured
    if not logger.hasHandlers():
        # Set the logging level and format from config
        logger.setLevel(LOG_LEVEL)
        
        # Create a console handler and set its format
        handler = logging.StreamHandler()
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        
        # Add the handler to the logger
        logger.addHandler(handler)

    return logger


def encode_int(val):
    return struct.pack("<i", val)


def encode_float(val):
    return struct.pack("<f", val)


def parse_command(cmd_str):
    """
    Return the parsed command in (BLECommand, arguments).
    """
    tokens = cmd_str.split(" ")
    try:
        if len(tokens) == 1:
            return (BLECommands.COMMAND_MAP[tokens[0]], None) 
        elif len(tokens) == 2:
            return (BLECommands.COMMAND_MAP[tokens[0]], tokens[1])
        raise ValueError
    except KeyError:
        raise ValueError(f"Unrecognizable command string: {cmd_str}")
