from ble_wrapper import BLEEventHandler, BLEWrapper

class Context(BLEEventHandler):
    

    def __init__(self, ble: BLEWrapper) -> None:
        super().__init__()

        # Pass itself to the BLEWrapper
        self.ble = ble
        self.ble.set_event_handler(self)

        # TODO


    # Override the BLEEventHandler functions

    # Lifecycle methods

    async def start(self):
        pass
    

    async def cleanup(self):
        self.ble.disconnect()
        self.ble.unregister_event_handler()
