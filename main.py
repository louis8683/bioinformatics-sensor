# We always start in advertising mode

# Commands valid during connection
CMD_MODE_SETUP = 0
CMD_MODE_DATA = 1

# Commands valid in both modes
CMD_DISCONNECT = 2

# Commands valid only in setup mode
CMD_SET_NAME = 3
CMD_SET_FREQ = 4

# Commands valid only in data mode

class BLE:

    def __init__(self):
        pass

    def start(self):
        pass

    def isAdvertising(self):
        pass

    def startAdvertising(self):
        pass

    def disconnect(self):
        pass

    def isConnected(self):
        pass

    def hasPendingCommand(self):
        pass


class Mode:
    # we can use this as an abstraction to reuse some of the common functions

    # Description: each Mode has full control of the BLE functionality, and is responsible
    #   for ensuring that BLE is running as expected.
    #   As we develop, we can abstract the control of the BLE process and segment the "start"
    #   function into smaller ones that fit into the lifecycle of BLE connections.

    def __init__(self, ble: BLE):
        self._ble = ble

    def _awaitCommand(self):
        # TODO: maybe we can use coroutine for this?
        pass


class SetupMode(Mode):
    
    def start(self):
        while True:
            # Ensure the connection is active
            if self._ble.isConnected() == False:
                return
            
            try:
                command = self._awaitCommand()
                if command == CMD_DISCONNECT:
                    self._ble.disconnect()
                elif command == CMD_SET_NAME:
                    pass
                elif command == CMD_SET_FREQ:
                    pass
                else:
                    # invalid command, ignore
                    print("invalid command")
            except IOError:
                # disconnected unexpectedly
                return


class DataMode(Mode):

    def start(self):
        while True:
            # Ensure the connection is active
            if self._ble.isConnected() == False:
                return
            
            # Here, we follow the BLE standard to stage the data for each characteristics
            pass


class AdvertisingMode(Mode):

    def start(self):
        while True:
            # Ensure advertisement is active
            if self._ble.isAdvertising() == False:
                self._ble.startAdvertising()
                continue
            
            # Wait for command
            command = self._awaitCommand()
            if command == CMD_MODE_SETUP:
                # enter setup mode
                setup_mode = SetupMode(self._ble)
                setup_mode.start()
            elif command == CMD_MODE_DATA:
                # enter data mode
                data_mode = DataMode(self._ble)
                data_mode.start()
            else:
                # invalid command, drop connection
                # (NOTE: alternatively, we can drop the connection in the _awaitCommand method. However, it would become a side effect.)
                self._ble.disconnect()


advertising_mode = AdvertisingMode(ble=BLE())
advertising_mode.start()
