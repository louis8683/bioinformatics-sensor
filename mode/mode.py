from ble import BLE
from .mode_type import ModeType

class Mode():
    """
    The base type for a mode of the micro-controller unit. Each mode has full control of the BLE functionality, and is responsible for ensuring that BLE is running as expected.

    Note:
        This class is meant to be inherited, and thus, should not be instantiated directly.

    Args:
        ble: a BLE (Bluetooth Low Energy) object instance
    """

    def __init__(self, ble: BLE):
        """
        Initialize a Mode instance.

        Args:
            ble: A Bluetooth Low Energy instance
        """
        self._ble = ble

    
    def start(self) -> ModeType:
        """
        Start the mode.

        Returns:
            ModeType: the mode type to transition to.
        """
        raise NotImplementedError


    def _wait_for_command(self):
        # TODO: maybe we can use coroutine for this?
        pass