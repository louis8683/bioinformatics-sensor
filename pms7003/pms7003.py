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

# TODO: explicitly set to active mode
ACTIVE_MODE_COMMAND = b''


class PMS7003:
    def __init__(self, uart=1, tx_pin=8, rx_pin=9, interval=DEFAULT_INTERVAL, debug=False) -> None:

        self.uart_port = uart
        self.tx_pin = tx_pin
        self.rx_pin = rx_pin
        self.uart = UART(uart, tx=Pin(tx_pin), rx=Pin(rx_pin), baudrate=9600, bits=8, stop=1, parity=None, timeout=TIMEOUT, timeout_char=TIMEOUT_CHAR)

        self._data = {
            "concentration_cf1": {
                "pm1": -1,
                "pm2_5": -1,
                "pm10": -1
            },
            "concentration_atm": {
                "pm1": -1,
                "pm2_5": -1,
                "pm10": -1
            },
            "n_particles": {
                "0_3um": -1,
                "0_5um": -1,
                "1um": -1,
                "2_5um": -1,
                "5um": -1,
                "10um": -1,
            },
            "timestamp": time.ticks_ms()
        }

        # Config the logger
        if debug:
            config_logger(log_level=logging.DEBUG)
        else:
            config_logger(log_level=logging.ERROR)

        # Events
        self._destroy_signal = asyncio.Event()
        self._pause_signal = asyncio.Event()
        self._resume_signal = asyncio.Event()

        # Coroutine tasks
        self._data_update_task = None


    # *** PUBLIC GETTERS ***


    def get_latest(self):
        """
        Get the latest data.

        Fields:
        - "concentration_cf1" (dict): concentration of PM1.0, PM2.5, and PM10 in CF=1 conditions.
            - "pm1" (int): PM1.0
            - "pm2_5" (int): PM2.5
            - "pm10" (int): PM10
        - "concentration_atm" (dict): concentration of PM1.0, PM2.5, and PM10 in atmospheric conditions. Use these values for typical use cases. -1 if no data yet.
            - "pm1" (int): PM1.0
            - "pm2_5" (int): PM2.5
            - "pm10" (int): PM10
        - "n_particles" (dict): number of particles with diameter beyond ? um in 0.1 L of air. -1 if no data yet.
                "0_3um" (int): beyond 0.3um
                "0_5um" (int): beyond 0.5um
                "1um" (int): beyond 1um
                "2_5um" (int): beyond 2.5um
                "5um" (int): beyond 5um
                "10um" (int): beyond 10um
        - "timestamp" (int): timestamp of the latest reading. Acquired by time.tick_ms().

        Returns
            dict: The data dict.
        """
        return self._data.copy()
    

    # *** PUBLIC LIFECYCLE METHODS ***


    async def start(self):
        """
        Start the sensor in "active mode", in which the sensor sends value periodically.
        """

        # TODO: can we read slower? will the data pile up?
        
        # TODO: now we skip init since default is active mode.
        # Initialize the sensor
        # if not await self._init_sensor():
        #     return False
        
        # Start the task
        self._data_update_task = asyncio.create_task(self._data_update_service())
        
        return True


    def pause(self):
        """Pause data collection."""
        get_logger().info("Pausing data collection...")
        self._pause_signal.set()


    def resume(self):
        """Resume data collection."""
        get_logger().info("Resuming data collection...")
        self._pause_signal.clear()
        self._resume_signal.set()


    async def destroy(self):
        """
        Destroy this class instance and freeing up resources.
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
        Initialize the sensor by explicitly setting to "active mode" with the command.
        """

        # TODO: explicitly set to active mode. Right now we're relying on the default being the active mode.

        get_logger().info("Initializing...")
        bytes = self.uart.write(ACTIVE_MODE_COMMAND)
        if bytes is None:
            get_logger().error("Timout when sending init command")
            return False
        elif bytes != len(ACTIVE_MODE_COMMAND):
            get_logger().error("Failed to send init command correctly")
            return False
        get_logger().info("success")
        return True

    
    async def _data_update_service(self):
        
        try:
            while not self._destroy_signal.is_set():

                if self._pause_signal.is_set():
                    get_logger().info("Data collection paused. Waiting to resume...")
                    await self._resume_signal.wait()
                    self._resume_signal.clear()

                get_logger().info(f"starting a data cycle at timestamp {time.ticks_ms()}...")

                nRetries = 5
                while self.uart.any() < 32 and nRetries > 0:
                    await asyncio.sleep(0.3)
                    nRetries -= 1
                    get_logger().debug(f"Retrying... Remaining retries: {nRetries}")
                    if nRetries == 0:
                        if self.uart.any() > 0:
                            self.uart.read()  # Clear buffer
                        await self._init_sensor() # reset the sensor
                        self._data = self._invalid_data()
                        get_logger().debug(f"Resetting...")

                # Read data
                raw_data = self.uart.read()

                if raw_data is None: # timeout
                    await asyncio.sleep(1)
                    continue # skip this data

                get_logger().info(f"Received {len(raw_data)} bytes from sensor")
                if len(raw_data) < 32:
                    get_logger().warning(f"too short")
                    # TODO: realign data
                    continue

                # Validation: checksum
                checksum = self._caclulate_checksum(raw_data)
                if checksum != (raw_data[30] << 8) | raw_data[31]:
                    get_logger().warning(f"invalid checksum, skipping frame (should be {checksum} but received {raw_data[8]})")
                    continue

                # Parse data
                try:
                    self._data = self._parse_data(raw_data)
                    self._data["timestamp"] = time.ticks_ms()
                    get_logger().info(f"Parsed result: {self._data}")
                except ValueError as e:
                    get_logger().error(f"Invalid data, clearing buffer")
                    self._data = self._parse_data(raw_data)
                    if self.uart.any() > 0:
                        self.uart.read()  # Clear buffer
                    await self._init_sensor() # reset the sensor\

            get_logger().info("data update service stopped via destroy signal")
        except asyncio.CancelledError:
            get_logger().info("data update service cancelled")


    def _parse_data(self, data):
        # Start characters validation
        if data[0] != 0x42 or data[1] != 0x4d:
            raise ValueError("Invalid start characters")
        
        # Frame length (2 bytes, skip for now)
        frame_length = (data[2] << 8) | data[3]

        return {
            "concentration_cf1": {
                "pm1": (data[4] << 8) | data[5],
                "pm2_5": (data[6] << 8) | data[7],
                "pm10": (data[8] << 8) | data[9]
            },
            "concentration_atm": {
                "pm1": (data[10] << 8) | data[11],
                "pm2_5": (data[12] << 8) | data[13],
                "pm10": (data[14] << 8) | data[15]
            },
            "n_particles": {
                "0_3um": (data[16] << 8) | data[17],
                "0_5um": (data[18] << 8) | data[19],
                "1um": (data[20] << 8) | data[21],
                "2_5um": (data[22] << 8) | data[23],
                "5um": (data[24] << 8) | data[25],
                "10um": (data[26] << 8) | data[27],
            },
            "timestamp": time.ticks_ms()
        }

    
    def _invalid_data(self):
        return {
            "concentration_cf1": {
                "pm1": -1,
                "pm2_5": -1,
                "pm10": -1
            },
            "concentration_atm": {
                "pm1": -1,
                "pm2_5": -1,
                "pm10": -1
            },
            "n_particles": {
                "0_3um": -1,
                "0_5um": -1,
                "1um": -1,
                "2_5um": -1,
                "5um": -1,
                "10um": -1,
            },
            "timestamp": time.ticks_ms()
        }
    

    def _caclulate_checksum(self, data):
        return sum(data[:-2]) & 0xFFFF