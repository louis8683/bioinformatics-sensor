from mode import ModeController
from ble import BLE

ble = BLE()
controller = ModeController(ble=ble)
controller.run()
