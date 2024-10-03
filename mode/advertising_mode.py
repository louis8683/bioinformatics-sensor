from .mode import Mode
from .mode_type import ModeType
from data_processing import Command

import logging

class AdvertisingMode(Mode):

    def start(self) -> ModeType:
        while True:
            # Ensure advertisement is active
            if self._ble.isAdvertising() == False:
                self._ble.startAdvertising()
                continue
            
            # Wait for command
            command = self._wait_for_command()
            if command == Command.SETUP:
                return ModeType.SETUP
            elif command == Command.DATA:
                return ModeType.DATA
            else: # invalid command
                logging.warning(f"Invalid command: {command}")
                self._ble.disconnect()