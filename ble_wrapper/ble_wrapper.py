import aioble
from .ble_event_handler import BLEEventHandler

class BLEWrapper:
    """
    BLE wrapper for event-based interfaces.
    """
    
    def __init__(self, name="MyDevice", security_level=None):
        """
        Initialize the BLE module with optional parameters.
        
        :param name: The BLE device name to be set on initialization.
        :param security_level: The security level to set for BLE communication (if applicable).
        """
        self.name = name
        self.security_level = security_level
        self.connected = False
        self.advertising = False

        # Initialize BLE setup
        self._initialize_ble()


    def _initialize_ble(self): # TODO
        """
        Set up the BLE interface, including the device name and security level.
        """
        print(f"Initializing BLE with name: {self.name}")
        if self.security_level:
            print(f"Setting security level to: {self.security_level}")


    # Event Handler registration methods


    def set_event_handler(self, event_handler: BLEEventHandler):
        """
        Set the event handler for BLEWrapper.
        
        :param event_handler: An instance implementing the BLEEventHandler interface.
        """
        self.event_handler = event_handler


    def unregister_event_handler(self):
        """
        Unregister the current event handler.
        """
        self.event_handler = None
        print("Event handler unregistered.")


    # Other public BLE methods


    def start(self):
        """Start the BLE module (e.g., begin advertising)."""
        print("BLE started and advertising...")
        if self.event_handler:
            self.event_handler.on_connect()


    def disconnect(self):
        """Disconnect the BLE device."""
        print("BLE disconnected.")
        if self.event_handler:
            self.event_handler.on_disconnect()


    def sendData(self, data):
        """Send data to the connected BLE device."""
        print(f"Sending data: {data}")
        if self.event_handler:
            self.event_handler.on_data_sent(data)
            
    