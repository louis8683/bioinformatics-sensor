import asyncio
import logging

from ble_wrapper import BLEEventHandler, BLEWrapper
from dht20 import DHT20
from pms7003 import PMS7003
from ze07co import ZE07CO

from .state import State
from .utilities import get_logger, config_logger

FILE_NAME = "config.txt"
DEFAULT_DEVICE_NAME = "bioinfo"

UPDATE_INTERVAL = 1 # seconds

class Context(BLEEventHandler):
    def __init__(self, initial_state_class, debug=False, debug_sensor=False):
        # Read from the config file
        self.device_name = DEFAULT_DEVICE_NAME
        with open("config.txt", "r") as file:
            while True:
                line = file.readline()
                if not line:
                    break
                name, _, value = line.strip().split(" ")
                if name == "device_name":
                    self.device_name = value

        # Initialize BLE
        self.ble_wrapper = BLEWrapper(name=self.device_name)

        # Initialize sensors
        self.dht20 = DHT20(debug=debug_sensor)
        self.pms7003 = PMS7003(debug=debug_sensor)
        self.ze07co = ZE07CO(debug=debug_sensor)

        # Initialize state
        self._state: State = initial_state_class(self)  # Pass self as context

        # Events
        self._transition_event = asyncio.Event()
        self._stop_signal = asyncio.Event()

        # Flags
        self._state_running = asyncio.Event()

        # Config the logger
        if debug:
            config_logger(log_level=logging.DEBUG)
        else:
            config_logger(log_level=logging.ERROR)

        # Other Attributes
        self.update_interval = UPDATE_INTERVAL


    # *** PUBLIC METHODS (USED BY STATES) ***


    def transition(self, state_class):
        self._next_state = state_class
        self._transition_event.set()

    
    def get_data(self):
        return {
            "dht20": self.dht20.get_latest(),
            "pms7003": self.pms7003.get_latest(),
            "ze07co": self.ze07co.get_latest()
        }

    
    def send_data(self):
        """Update the value in the BLE characteristic. Raises ValueError if one of the value is not ready yet."""
        
        # TODO: should we include the timestamps for the individual sensor data?
        
        dht_data = self.dht20.get_latest()
        if dht_data["humidity"] == float("-inf"):
            raise ValueError
        else:
            humidity = dht_data["humidity"] 
        if dht_data["temperature"] == float("-inf"):
            raise ValueError
        else:
            temperature = dht_data["temperature"]

        pms_data = self.pms7003.get_latest()
        if pms_data["concentration_atm"]["pm2_5"] == -1:
            raise ValueError
        else:
            pm2_5 = pms_data["concentration_atm"]["pm2_5"]
        
        co_data = self.ze07co.get_latest()
        if co_data["concentration"] == float("-inf"):
            raise ValueError
        else:
            co_concentration = co_data["concentration"]
        
        self.ble_wrapper.update_bioinfo_data(temperature, humidity, pm2_5, co_concentration, keep_old=True)
    

    def update_name(self, name):
        """Update the device name. Will take effect on the next advertising cycle."""

        with open("config.txt", "w") as file:
            content = f"device_name = {name}"
            file.write(content)
        self.device_name = name
        self.ble_wrapper.name = name


    # *** LIFECYCLE METHODS (USED BY THE MAIN FUNCTION) ***


    async def start(self):
        """Start the application and run indefinitely."""

        try:        
            # Start BLE
            await self.ble_wrapper.start()

            # Start sensors
            await self.dht20.start()
            await self.pms7003.start()
            await self.ze07co.start()

            # Start first state
            self._state.enter()
            self.ble_wrapper.set_event_handler(self._state)

            while True:
                # wait for transition
                await self._transition_event.wait()
                self._transition_event.clear()

                # is there a stop signal?
                if self._stop_signal.is_set():
                    break

                # transition 
                # TODO: this part might cause the main thread to block, maybe add a timeout exception
                # NOTE: the order of these operations should be carefully considered.
                self._state_running.clear()
                self._state.exit()
                self.ble_wrapper.unregister_event_handler()
                self._state = self._next_state(self)
                self._state.enter()
                self.ble_wrapper.set_event_handler(self._state)
                self._state_running.set()

        except Exception:
            # free up resources on unknown error
            await self.destroy()
            raise Exception
    

    async def stop(self):
        """Stop the application"""
        self._stop_signal.set()
        self._transition_event.set()
        self._state.exit()

    
    async def destroy(self):
        """Free up the resources."""
        # stop the application
        await self.stop()

        # call destroy on the ble and sensor classes
        await self.ble_wrapper.destroy()
        await self.dht20.destroy()
        await self.pms7003.destroy()
        await self.dht20.destroy()


    