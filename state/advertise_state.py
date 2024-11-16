from .state import State

from ble_wrapper import BLECommands


class AdvertiseState(State):

    def enter(self):
        super().enter()

    def exit(self):
        super().exit()

    def run(self):
        raise NotImplementedError("Subclasses should implement this method")
    

    # *** OVERRIDES FOR THE BLEEventHandler INTERFACE ***


    def on_connect(self):
        pass

    def on_handshake_success(self):
        from .data_state import DataState
        self.context.transition(DataState)

    def on_disconnect(self):
        pass

    def on_bioinfo_data_updated(self):
        pass

    def on_command(self, command: BLECommands):
        pass
