class BLECommands:
    # TODO: add to this list and make sure to keep the COMMAND_MAP synced
    
    RESET = "reset"
    SETUP_MODE = "setup_mode"
    DATA_MODE = "data_mode"
    DISCONNECT = "disconnect"

    # Map command strings to constants
    COMMAND_MAP = {
        RESET: RESET,
        SETUP_MODE: SETUP_MODE,
        DATA_MODE: DATA_MODE,
        DISCONNECT: DISCONNECT,
    }
