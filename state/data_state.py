import asyncio

from .state import State

from ble_wrapper import BLECommands
from .utilities import get_logger


class DataState(State):

    def __init__(self, context, dht20, pms7003, ze07co):
        super().__init__(context)
        self.dht20 = dht20
        self.pms7003 = pms7003
        self.ze07co = ze07co

    def enter(self):
        super().enter()
        self.dht20.resume()
        self.pms7003.resume()
        self.ze07co.resume()

        # TODO: start the data update coroutine
        self.start_task(self._data_service(self.context.update_interval))
    


    def exit(self):
        super().exit()
        self.dht20.pause()
        self.pms7003.pause()
        self.ze07co.pause()

    
    # *** COROUTINES ***


    async def _data_service(self, interval):

        try:
            while True:
                # update the data
                try:
                    self.context.send_data()
                except ValueError as e:
                    get_logger().exception(f"Data not ready: {e}")

                # wait
                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            pass


    # *** OVERRIDES FOR THE BLEEventHandler INTERFACE ***


    def on_connect(self):
        pass

    def on_handshake_success(self):
        pass

    def on_disconnect(self):
        # NOTE: import in the function scope to avoid circular imports
        from .advertise_state import AdvertiseState
        self.context.transition(AdvertiseState)

    def on_bioinfo_data_updated(self):
        pass

    def on_command(self, command, argument):

        if command == BLECommands.SETUP_MODE:
            from .setup_state import SetupState
            self.context.transition(SetupState)
        else:
            get_logger().warning(f"Cannot process {command} command in data state")

