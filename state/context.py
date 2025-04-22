import asyncio
import logging

from ble_wrapper import BLEEventHandler, BLEWrapper
from dht20 import DHT20
from pms7003 import PMS7003
from ze07co import ZE07CO

from .state import State
from .advertise_state import AdvertiseState
from .data_state import DataState
from .utilities import get_logger, config_logger
from ws2812b import WS2812B

FILE_NAME = "config.txt"
DEFAULT_DEVICE_NAME = "bioinfo"

UPDATE_INTERVAL = 5 # seconds

class Context(BLEEventHandler):
    def __init__(self, initial_state_class, debug=False, debug_sensor=False):

        self.debug = debug
        self.debug_sensor = debug_sensor
        
        # Read from the config file
        self.device_name = DEFAULT_DEVICE_NAME
        with open(FILE_NAME, "r") as file:
            while True:
                line = file.readline()
                if not line:
                    break
                name, _, value = line.strip().split(" ")
                if name == "device_name":
                    self.device_name = value
                if name == "debug":
                    self.debug = (value == "true" or value == "True")
                if name == "debug_sensor":
                    self.debug_sensor = (value == "true" or value == "True")

        
        get_logger().info(f"Logging: debug={self.debug}, debug_sensor={self.debug_sensor}")
        

        get_logger().info(f"Device name: {self.device_name}")

        # Initialize BLE
        self.ble_wrapper = BLEWrapper(name=self.device_name)

        # Initialize sensors
        self.dht20 = DHT20(debug=self.debug_sensor)
        self.pms7003 = PMS7003(debug=self.debug_sensor)
        self.ze07co = ZE07CO(debug=self.debug_sensor)

        # Initialize LEDs
        self.rgb_led = WS2812B(brightness=0.1)
        self.rgb_led.clear_strip()

        # Initialize state
        self._state: State = initial_state_class(self)  # Pass self as context

        # Events
        self._transition_event = asyncio.Event()
        self._stop_signal = asyncio.Event()

        # Flags
        self._state_running = asyncio.Event()

        # Config the logger
        if self.debug:
            config_logger(log_level=logging.DEBUG)
        else:
            config_logger(log_level=logging.INFO)

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
        """Update the value in the BLE characteristic. Might contain invalid values if data isn't ready.
        
        Invalid values:
        - PM2.5: -1
        - CO: float("-inf")
        - Temperature: float("-inf")
        - Humidity: float("-inf")
        """

        dht_data = self.dht20.get_latest()
        humidity = dht_data["humidity"] 
        temperature = dht_data["temperature"]
        pms_data = self.pms7003.get_latest()
        pm2_5 = pms_data["concentration_atm"]["pm2_5"]
        co_data = self.ze07co.get_latest()
        co_concentration = co_data["concentration"]

        get_logger().info(f"PM2.5: {pm2_5}")
        
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
            self.dht20.pause()
            await self.pms7003.start()
            self.pms7003.pause()
            await self.ze07co.start()
            self.ze07co.pause()

            # Start first state
            self.rgb_led.disconnected()
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
                self.rgb_led.clear_strip()

                if self._next_state == DataState:
                    self._state = DataState(self, self.dht20, self.pms7003, self.ze07co)
                else:
                    self._state = self._next_state(self)
                
                self._state.enter()
                self.ble_wrapper.set_event_handler(self._state)
                self._state_running.set()
                if isinstance(self._state, DataState):
                    self.rgb_led.connected()
                elif isinstance(self._state, AdvertiseState):
                    self.rgb_led.disconnected()

        except Exception as e:
            # free up resources on unknown error
            await self.destroy()
            get_logger().error(f"Unknown error: {e}")
            raise e
    

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

