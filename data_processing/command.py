from enum import Enum, auto

class Command(Enum):
    # Commands valid during connection
    SETUP = 0
    DATA = 1

    # Commands valid in both modes
    DISCONNECT = 2

    # Commands valid only in setup mode
    SET_NAME = 3
    SET_FREQ = 4

    # Commands valid only in data mode
