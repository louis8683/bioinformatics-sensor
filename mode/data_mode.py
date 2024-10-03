from .mode import Mode
from .mode_type import ModeType

class DataMode(Mode):

    def start(self) -> ModeType:
        while True:
            # Ensure the connection is active
            if self._ble.isConnected() == False:
                return ModeType.ADVERTISING
            
            # Here, we follow the BLE standard to stage the data for each characteristics
            pass
