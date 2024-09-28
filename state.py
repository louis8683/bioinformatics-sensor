STATE_SETUP = 0
STATE_ADVERTISE = 1
STATE_DATA = 2

class State:

    def __init__(self) -> None:
        self.current = STATE_ADVERTISE
        self.ble = BLE()
