from machine import Pin, I2C
import time
import asyncio
import logging

from .utilities import get_logger, config_logger

ADDRESS = 0x38 # 7-bit I2C device address
MEASUREMENT_COMMAND = b'\xAC'
MEASUREMENT_PARAM_1 = b'\x33'
MEASUREMENT_PARAM_2 = b'\x00'
STATUS_WORD_COMMAND = b'\x71'

INIT_TIMEOUT = 5 # seconds
DATA_TIMEOUT = 1 # seconds
DEFAULT_INTERVAL = 1.0 # once every 1 second


class DHT20:

    def __init__(self, i2c=0, sda_pin=20, scl_pin=21, interval=DEFAULT_INTERVAL, debug=False):
        
        self.i2c_port = i2c
        self.sda_pin = sda_pin
        self.scl_pin = scl_pin
        self._i2c = I2C(self.i2c_port, sda=Pin(self.sda_pin), scl=Pin(self.scl_pin))
        self.interval = interval
        self._data = {
            "humidity": float("-inf"),
            "temperature": float("-inf"),
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
        - "humidity" (float): relative humidity from 0 to 1. float("-inf") if no valid readings yet.
        - "temperature" (float): temperature in celcius. float("-inf") if no valid readings yet.
        - "timestamp" (int): timestamp of the latest reading. Acquired by time.tick_ms().

        Returns
            dict: The data dict.
        """
        return self._data.copy()


    # *** PUBLIC LIFECYCLE METHODS ***


    async def start(self):
        """
        Start the sensor by following the sensor reading process in the documentation. https://aqicn.org/air/sensor/spec/asair-dht20.pdf

        Returns:
            bool: True if successful. False if failed.
        """
        get_logger().info("Start: starting DHT20...")

        # STEP 1: initialization

        try:
            if not await asyncio.wait_for(self._init_sensor(), INIT_TIMEOUT):
                get_logger().warning("failed")
                return False
        except asyncio.TimeoutError:
            get_logger().error("timeout")
        
        get_logger().info("Initialization completed")

        # Start the data service

        self._data_update_task = asyncio.create_task(self._data_update_service())
        # await self._data_update_service()

        get_logger().info("start success")
        return True


    async def destroy(self):
        """
        Destroy the DHT20 instance and freeing up resources.
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
        Initialize the sensor. Only required when first starting up.

        Returns:
            bool: True if successful, False if failed.
        """

        get_logger().info("_init_sensor: initializing DHT20...")

        # wait a minimum of 100ms after power on
        await asyncio.sleep(0.1)

        get_logger().info("_init_sensor: slept 100ms...")
        
        # verify that the status word is set to 0x18 by sending 0x71
        try:
            get_logger().info("Sending command to get the status word...")

            # Send the command to get the status word
            n_bytes = self._i2c.writeto(ADDRESS, STATUS_WORD_COMMAND)

            if n_bytes < 1:
                get_logger().error("Initialization: failed to send STATUS command")

            # Check the status word
            status_word = self._i2c.readfrom(ADDRESS, 1)

            if status_word != b'\x18':
                #  TODO: if not 0x18, set 0x1B, 0x1C, and 0x1E registers (manual lacks clarity for values)
                get_logger().error(f"Initialization: status word not 0x18, instead is {status_word}. Aborting process.")
            else:
                get_logger().info("Initialization: success")
                return True
        except OSError as e:
            get_logger().error("Initialization: OSError")

        return False
    

    async def _trigger_measurement(self):
        """
        Trigger the sensor to start a measurement.

        Returns:
            bool: True if successful, False if failed.
        """
        # wait 10ms
        await asyncio.sleep(0.01)

        # send the 0xAC command (trigger measurement) this command has two bytes, the first is 0x33, and the second is 0x00.
        if self._i2c.writeto(ADDRESS, bytearray(MEASUREMENT_COMMAND + MEASUREMENT_PARAM_1 + MEASUREMENT_PARAM_2)) != 3:
            get_logger().warning("Failed to send measurement command")
            return False
        else:
            get_logger().info("Measurement command successfully sent.")
            return True
        
    
    async def _get_raw_data(self):
        """
        Get the raw data from the sensor. Retries untill success. Throws OSError on unexpected disconnection.
        
        Returns
            data (bytearray): the raw data.
        """

        get_logger().info("Reading raw data from sensor...")

        # wait 80ms for the measurement to complete
        await asyncio.sleep(0.08)

        read_successful = False
        data = None
        while not read_successful:
            # if read status word Bit[7] is 0, the measurement is completed.
            if self._i2c.writeto(ADDRESS, STATUS_WORD_COMMAND):
                get_logger().info("waiting for status word...")
                response = self._i2c.readfrom(ADDRESS, 1)
                status_word = response[0]
                get_logger().info(f"status word: {response}")
                if ~status_word & (1 << 7):
                    # if completed, read six bytes continuously
                    get_logger().info("reading data...")
                    data = self._i2c.readfrom(ADDRESS, 6)

                    # STEP 4: data validation

                    # TODO: CRC data validation. 
                    # NOTE: Right now, everytime we read another byte, we receive \x18, which seems to be the status code.
                    # after receiving six bytes, the next byte is the CRC check data.
                    # - to perform CRC check, an ACK can be sent after the sixth byth is received
                    # - otherwise, send NACK to end
                    # print("reading crc...")
                    # crc = self.i2c.readfrom(ADDRESS, 1)

                    # set the read_successful to True
                    read_successful = True
                else:
                    get_logger().warning("not ready")
            else:
                get_logger().warning("cannot send status word command")
        
        return data
    

    async def _data_update_service(self):
        """
        Updates the data periodically.
        """
        
        get_logger().info("data update service started")

        try:
            while not self._destroy_signal.is_set():
                get_logger().info(f"starting a data cycle at timestamp {time.ticks_ms()}...")
                # wait for the next interval's start time
                wait_time = self.interval - (time.ticks_ms() - self._data["timestamp"]) / 1000
                get_logger().info(f"waiting for {wait_time} seconds")
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

                # STEP 2: trigger measurement

                get_logger().info("Triggering measurement...")
                if not await self._trigger_measurement():
                    # TODO: set the sensor into a warning status signalling that there is problem retrieving data
                    continue

                # STEP 3: read data

                get_logger().info("Reading data from sensor...")
                try:
                    data = await asyncio.wait_for(self._get_raw_data(), DATA_TIMEOUT)
                except OSError:
                    # TODO: set sensor to warning
                    get_logger().error("OSError, retry")
                    continue
                except asyncio.TimeoutError:
                    # TODO: set sensor to warning status
                    continue

                # STEP 5: parse data

                # calculate the temperature and humidity value

                get_logger().info("Parsing data...")
                if data is not None:
                    humidity, temperature = self._parse_data(data)
                    self._data["humidity"] = humidity
                    self._data["temperature"] = temperature
                    self._data["timestamp"] = time.ticks_ms()

                    get_logger().info(f"Humidity = {humidity}")
                    get_logger().info(f"Temperature = {temperature}")

            get_logger().info("data update service stopped via destroy signal")
        except asyncio.CancelledError:
            get_logger().info("data update service cancelled")
            

    def _parse_data(self, data):
        """
        Parse the binary sensor data into a tuple of humidity and temperature.

        Args:
            data (bytearray): the raw data from the sensor

        Returns:
            Tuple[Double, Double]: tuple of humidity (0-1) and temperature (celcius)
        """

        data_int = int.from_bytes(data, 'big')

        # Extract the first 8 bits for 'state'
        state = (data_int >> (20 + 20)) & 0xFF  # Shift to the right and mask with 0xFF for 8 bits

        # Extract the next 20 bits for 'humidity'
        humidity = (data_int >> 20) & 0xFFFFF  # Mask with 0xFFFFF for 20 bits
        humidity /= (2**20)

        # Extract the final 20 bits for 'temperature'
        temperature = data_int & 0xFFFFF  # Mask with 0xFFFFF for 20 bits
        temperature = temperature / (2**20) * 200 - 50

        return (humidity, temperature)
