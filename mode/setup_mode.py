from ble import BLE
from .mode import Mode
from .mode_type import ModeType
from data_processing import Command
import logging

class SetupMode(Mode):
    
    def start(self):
        while True:
            # Ensure the connection is active
            if self._ble.isConnected() == False:
                return
            
            try:
                command = self._wait_for_command()
                if command == Command.DISCONNECT:
                    self._ble.disconnect()
                    return ModeType.ADVERTISING
                elif command == Command.SET_NAME:
                    pass
                elif command == Command.SET_FREQ:
                    pass
                else:
                    # invalid command, ignore
                    logging.warning(f"invalid command: {command}")
            except IOError:
                # disconnected unexpectedly
                return
            