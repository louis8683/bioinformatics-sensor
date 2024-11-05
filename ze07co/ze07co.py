import time
import asyncio
import logging

from machine import UART, Pin

from .utilities import get_logger, config_logger

# Time to wait for the first character
TIMEOUT = 50

# Time to wait between characters
TIMEOUT_CHAR = 50

DEFAULT_INTERVAL = 1.0 # once every 1 second

INITIATIVE_UPLOAD_MODE_COMMAND = b'\xFF\x01\x78\x40\x00\x00\x00\x00\x47'


class ZE07CO:

    def __init__(self, uart=0, tx_pin=12, rx_pin=13, interval=DEFAULT_INTERVAL, debug=False) -> None:

        self.uart_port = uart
        self.tx_pin = tx_pin
        self.rx_pin = rx_pin
        self.uart = UART(uart, tx=Pin(tx_pin), rx=Pin(rx_pin), baudrate=9600, bits=8, stop=1, parity=None, timeout=TIMEOUT, timeout_char=TIMEOUT_CHAR)

        self._data = {
            "concentration": float("-inf"),
            "range": 500.0,
            "timestamp": time.ticks_ms()
        }

        # Config the logger
        if debug:
            config_logger(log_level=logging.DEBUG)
        else:
            config_logger(log_level=logging.ERROR)

        # Events
        self._destroy_signal = asyncio.Event()

        # Coroutine tasks
        self._data_update_task = None


    # *** PUBLIC GETTERS ***


    def get_latest(self):
        """
        Get the latest data.

        Fields:
        - "concentration" (float): concentration of CO in PPM. float("-inf") if no valid readings yet.
        - "range" (float): the range of measurement, from 0 to "range" PPM. Should be 500.0 for normal operations.
        - "timestamp" (int): timestamp of the latest reading. Acquired by time.tick_ms().

        Returns
            dict: The data dict.
        """
        return self._data.copy()
    

    # *** PUBLIC LIFECYCLE METHODS ***


    async def start(self):
        """
        Start the sensor in "initiative upload mode", in which the sensor sends value every 1 second.
        """
        
        # Initialize the sensor
        if not await self._init_sensor():
            return False
        
        # Start the task
        self._data_update_task = asyncio.create_task(self._data_update_service())
        
        return True


    async def destroy(self):
        """
        Destroy the ZE07CO instance and freeing up resources.
        """

        # Send a destroy signal
        get_logger().info("Sending destroy signal...")
        self._destroy_signal.set()

        # Wait for tasks to finish
        try:
            if isinstance(self._data_update_task, asyncio.Task):
                await asyncio.wait_for(self._data_update_task, timeout=10)

        except asyncio.TimeoutError:
            get_logger().warning("Destroy signal timed out, sending task cancel signal...")
            
            # cancel the tasks

            if isinstance(self._data_update_task, asyncio.Task):
                self._data_update_task.cancel()
            
            # wait for the tasks to be cancelled

            if isinstance(self._data_update_task, asyncio.Task):
                await asyncio.wait_for(self._data_update_task, timeout=10)


    # *** PRIVATE METHODS ***


    async def _init_sensor(self):
        """
        Initialize the sensor by explicitly setting to "initiative upload mode" with the command.
        """
        get_logger().info("Initializing...")
        bytes = self.uart.write(INITIATIVE_UPLOAD_MODE_COMMAND)
        if bytes is None:
            get_logger().error("Timout when sending init command")
            return False
        elif bytes != 9:
            get_logger().error("Failed to send init command correctly")
            return False
        get_logger().info("success")
        return True

    
    async def _data_update_service(self):
        
        try:
            while not self._destroy_signal.is_set():
                get_logger().info(f"starting a data cycle at timestamp {time.ticks_ms()}...")

                while self.uart.any() < 9:
                    await asyncio.sleep(0.3)

                # Read data
                raw_data = self.uart.read()
                get_logger().info(f"Received {len(raw_data)} bytes from sensor")
                if len(raw_data) < 9:
                    get_logger().warning(f"too short")
                    # TODO: realign data
                    continue

                # Validation: checksum
                checksum = self._caclulate_checksum(raw_data)
                if checksum != raw_data[8]:
                    get_logger().warning(f"invalid checksum, skipping frame (should be {checksum} but received {raw_data[8]})")
                    continue

                # Parse data
                concentration, full_range = self._parse_data(raw_data)
                get_logger().info(f"Parse result: {concentration} PPM")

                self._data["concentration"] = concentration
                self._data["range"] = full_range
                self._data["timestamp"] = time.ticks_ms()


            get_logger().info("data update service stopped via destroy signal")
        except asyncio.CancelledError:
            get_logger().info("data update service cancelled")


    def _parse_data(self, data):
        concentration = ((data[4] << 8) + data[5]) * 0.1    
        full_range = (data[6] * 256 + data[7]) * 0.1 # same as shifting 8 bits 
        return concentration, full_range
    

    def _caclulate_checksum(self, data):
        # Skip the first byte and take all except the last byte
        tempq = sum(data[1:8]) & 0xFF # Sum all bytes except the first and last

        # Two's complement
        tempq = (~tempq + 1) & 0xFF  # Keep it within 8 bits

        return tempq


