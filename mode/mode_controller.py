from .mode_type import ModeType
from .advertising_mode import AdvertisingMode
from .data_mode import DataMode
from .setup_mode import SetupMode

class ModeController:
    
    def __init__(self, ble) -> None:
        self._mode = ModeType.ADVERTISING
        self._instances = {
            ModeType.ADVERTISING: AdvertisingMode(ble),
            ModeType.DATA: DataMode(ble),
            ModeType.SETUP: SetupMode(ble)
        }

    def run(self) -> None:
        while True:
            self._mode = self._instances[self._mode].start() 
