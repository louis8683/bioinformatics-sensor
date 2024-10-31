class BLEEventHandler:
    """
    Interface for BLE event handlers.
    """

    def on_connect(self):
        pass

    def on_handshake_success(self):
        pass

    def on_disconnect(self):
        pass

    def on_bioinfo_data_updated(self):
        pass

    def on_command(self, command):
        pass

    def on_data_sent(self, data):
        pass

