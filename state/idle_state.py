from .state import State
from ble_wrapper import BLECommands


class IdleState(State):

    def enter(self):
        super().enter()

    def exit(self):
        super().exit()


    # *** OVERRIDES FOR THE BLEEventHandler INTERFACE ***


    def on_connect(self):
        pass

    def on_handshake_success(self):
        pass

    def on_disconnect(self):
        pass

    def on_bioinfo_data_updated(self):
        pass

    def on_command(self, command, argument):
        pass
