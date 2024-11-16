class BLECommands:
    # TODO: add to this list and make sure to keep the COMMAND_MAP synced
    
    # *** STATE RELATED ***

    # RESET = "reset"
    SETUP_MODE = "setup_mode"
    DATA_MODE = "data_mode"
    # DISCONNECT = "disconnect" # NOTE: we remove this for now and rely on BLE's own disconnect pathway

    # *** SETUP RELATED

    UPDATE_NAME = "name"


    # Map command strings to constants
    COMMAND_MAP = {
        # RESET: RESET,
        SETUP_MODE: SETUP_MODE,
        DATA_MODE: DATA_MODE,
        # DISCONNECT: DISCONNECT, 
        UPDATE_NAME: UPDATE_NAME
    }
