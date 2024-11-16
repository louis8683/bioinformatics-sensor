from .state import State
from .utilities import get_logger

from ble_wrapper import BLECommands


class SetupState(State):

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
        from .advertise_state import AdvertiseState
        self.context.transition(AdvertiseState)


    def on_bioinfo_data_updated(self):
        raise NotImplementedError


    def on_command(self, command, argument):
    
        if command == BLECommands.DATA_MODE:
            from .data_state import DataState
            self.context.transition(DataState)
        if command == BLECommands.UPDATE_NAME:
            if argument is not None and len(argument) > 0:
                self.context.update_name(argument)
        else:
            get_logger().warning(f"Cannot process {command} command in data state")
