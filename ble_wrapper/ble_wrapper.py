import aioble
import asyncio
import struct
import time

from .ble_event_handler import BLEEventHandler
from .constants import ENV_SENSE_UUID, BIO_INFO_CHARACTERISTICS_UUID, REQUEST_CHARACTERISTICS_UUID, RESPONSE_CHARACTERISTICS_UUID, MACHINE_TIME_CHARACTERISTICS_UUID
from .constants import HANDSHAKE_MSG, HANDSHAKE_TIMEOUT_MS
from .constants import ADV_APPEARANCE_GENERIC_THERMOMETER, ADV_INTERVAL_MS
from .constants import RESPONSE_TIMEOUT_MS, BAD_RESPONSE, OK_RESPONSE

from .utilities import get_logger
from . import utilities


class BLEWrapper:
    """
    BLEWrapper is an event-based wrapper for handling Bluetooth Low Energy (BLE) communications. It simplifies the setup and management of BLE services, characteristics, and connection state, as well as the data handling for a bioinformatics device.

    This class is designed to work with BLEEventHandler to handle asynchronous BLE events, 
    such as connection, disconnection, and data updates. It includes a GATT server setup 
    with services and characteristics necessary for bioinformatics sensor data communication.

    Processing of all commands are delegated to the event handler. This includes commands related to BLE functionality, such as the "disconnect" command.

    Attributes:
        _name (str): The name of the BLE device.
        _data (dict): Sensor data including temperature, humidity, PM2.5, CO concentration, and timestamp of last update.
    """
    
    def __init__(self, name="bioinfo", event_handler=None):
        """
        Initialize the BLE module with optional parameters.
        
        :param name: The BLE device name to be set on initialization.
        """

        get_logger().info("BLEWrapper initializing...")

        self._name = name
        self._connection = None # Type of "aioble.DeviceConnection"
        self._service_uuids = [ENV_SENSE_UUID]
        self._event_handler = event_handler
        self._data = {
            "temperature": float("-inf"), # float
            "humidity": float("-inf"), # float
            "pm2_5": float("-inf"), # float
            "co_concentration": float("-inf"), # float
            "last_update": -1 # int, time.tick_ms // 1000
        }

        # Events
        self._destroy_signal = asyncio.Event()
        self._handshake_event = asyncio.Event()

        # Tasks
        self._peripheral_task = None
        self._machine_time_task = None
        self._request_task = None

        # Initialize BLE
        self._register_gatt_server()

        get_logger().info("Init done.")


    # *** PRIVATE GATT/BLE METHODS ***

    
    def _register_gatt_server(self):
        """
        Register GATT server.
        
        One service
        - Environment sensing service

        Four characteristics
        - Bioinfo
        - Machine time
        - Request
        - Response
        """
        self.bioinfo_service = aioble.Service(ENV_SENSE_UUID)
        self.bioinfo_characteristic = aioble.Characteristic(
            service=self.bioinfo_service,
            uuid=BIO_INFO_CHARACTERISTICS_UUID,
            read=True,
            write=False,
            write_no_response=False,
            notify=True,
            indicate=False,
            initial=None,
            capture=False
        )

        self.machine_time_characteristics = aioble.Characteristic(
            service=self.bioinfo_service,
            uuid=MACHINE_TIME_CHARACTERISTICS_UUID,
            read=True,
        )
        
        self.request_characteristic = aioble.Characteristic(
            service=self.bioinfo_service,
            uuid=REQUEST_CHARACTERISTICS_UUID,
            write=True
        )

        self.response_characteristic = aioble.Characteristic(
            service=self.bioinfo_service,
            uuid=RESPONSE_CHARACTERISTICS_UUID,
            indicate=True,
        )

        aioble.register_services(self.bioinfo_service)

    
    async def _handshake(self, connection):
        """
        Perform handshake procedure with client. Used to verify client legitimacy when establishing connection.

        Returns
            bool: True if success, False if failed.
        """
        get_logger().info("Handshake in progress...")
        valid_handshake = False
        try:
            await self.request_characteristic.written(timeout_ms=HANDSHAKE_TIMEOUT_MS)
            data = self.request_characteristic.read()
            if len(data) > 0 and data.decode("utf-8") == HANDSHAKE_MSG:
                response_msg = "howdy".encode("utf-8")
                get_logger().info("Responding to the handshake...")
                await self.response_characteristic.indicate(
                    connection, 
                    data=response_msg, 
                    timeout_ms=HANDSHAKE_TIMEOUT_MS
                )
                get_logger().info("Handshake successful.")
                valid_handshake = True
            elif len(data) > 0:
                message = data.decode("utf-8")
                get_logger().warning(f"Bad handshake message: {message}. Closing connection...")
            else:
                get_logger().warning("Empty handshake, closing connection...")
        except asyncio.TimeoutError:
            get_logger().warning("TIMEOUT on handshake. Closing connection...")
        except aioble.DeviceDisconnectedError:
            get_logger().warning("Device has disconnected prematurely. Closing connection...")
        except Exception as e:
            get_logger().warning(f"Unknown error of type {type(e).__name__}: {e}. Closing connection...")
        
        return valid_handshake


    async def _advertise_and_connect(self):
        """
        Handles the forever loop between advertisement and connection states.
        """
        get_logger().info("Starting advertisment/connection loop...")
        try:
            while True:
                async with await aioble.advertise(
                    ADV_INTERVAL_MS,
                    name=self._name,
                    services=self._service_uuids,
                    appearance=ADV_APPEARANCE_GENERIC_THERMOMETER,
                ) as connection:
                    # Initialize the connection
                    self._connection = connection

                    get_logger().info(f"Connection from {connection.device}")

                    if self._event_handler is not None:
                        self._event_handler.on_connect()

                    # Handshake
                    valid_handshake = await self._handshake(connection)

                    # Either wait for disconnection or disconnect directly according to the handshake result.
                    if valid_handshake:
                        if self._event_handler is not None:
                            self._event_handler.on_handshake_success()

                        # Start the request service
                        if self._request_task is None:
                            self._request_task = asyncio.create_task(self._request_service())

                        await connection.disconnected()
                    else:
                        await connection.disconnected(disconnect=True)

                    get_logger().info("Disconnected")

                    if self._event_handler is not None:
                        self._event_handler.on_disconnect()

                    # clean up after disconnection
                    self._connection = None
                    if self._request_task is not None:
                        self._request_task.cancel()

                    # break from the loop if we want to destroy the BLEWrapper
                    if self._destroy_signal.is_set():
                        break
        except AttributeError as e:
            # the aioble.advertise returns a None
            get_logger().warning(f"advertise/connection loop failed: {e}")
        except asyncio.CancelledError:
            # task is cancelled through "task.cancel()", which is a backup plan for setting the destroy signal
            get_logger().warning("Peripheral task forced cancelled.")
    

    async def _update_machine_time_characteristics(self):
        """
        Update the machine-time-characteristics every 1 second
        """

        # NOTE: we did not deal with the wrap-around issue with tick_ms (which occurs in roughly 24 days)
        try:
            while True:
                current_time = time.ticks_ms()
                time_data = utilities.encode_int(current_time // 1000)
                self.machine_time_characteristics.write(time_data)

                # sleep for a second
                await asyncio.sleep(1)

                # check for destroy signal
                if self._destroy_signal.is_set():
                    break
        except asyncio.CancelledError:
            pass
    

    async def _request_service(self):
        """
        Receive requests from clients. Loops until a destroy signal or cancel signal is sent.
        """
        
        get_logger().info("Request service started...")

        try:
            while not self._destroy_signal.is_set():
                try:
                    await self.request_characteristic.written()
                    data = self.request_characteristic.read()
                    request = data.decode("utf-8")
                    try:
                        command = utilities.parse_command(request)
                        
                    except ValueError as e:
                        get_logger().error(f"Request service: ValueError {e}")

                        # write a BAD response
                        if self.is_connected():
                            await self.response_characteristic.indicate(
                                self._connection, 
                                data=BAD_RESPONSE, 
                                timeout_ms=RESPONSE_TIMEOUT_MS
                            )
                        continue

                    get_logger().info(f"Received command: {command}")

                    # write a OK response
                    if self.is_connected():
                        await self.response_characteristic.indicate(
                            self._connection, 
                            data=OK_RESPONSE, 
                            timeout_ms=RESPONSE_TIMEOUT_MS
                        )
                    
                    # send the command as an event
                    if self._event_handler is not None:
                        self._event_handler.on_command(command)
                    
                except Exception as e:
                    get_logger().error(f"Request Service: Unknown error of type {type(e).__name__}: {e}.")
            get_logger().info("Request service stopped via destroy signal")

        except asyncio.CancelledError:
            get_logger().info("Request service stopped via cancel()")


    # *** EVENT HANDLER REGISTRATION METHODS ***


    def set_event_handler(self, event_handler: BLEEventHandler):
        """
        Set the event handler for BLEWrapper.
        
        :param event_handler: An instance implementing the BLEEventHandler interface.
        """
        self._event_handler = event_handler


    def unregister_event_handler(self):
        """
        Unregister the current event handler.
        """
        self._event_handler = None
        get_logger().info("Event handler unregistered.")


    # *** PUBLIC LIFECYCLE METHODS ***


    async def start(self):
        """
        Start the BLE module (e.g., begin advertising).
        
        The advertisement/connection task is started in a coroutine with asyncio.
        """
        get_logger().info("BLE started and advertising...")
        
        # create the task if not created yet
        if self._peripheral_task is None:
            self._peripheral_task = asyncio.create_task(self._advertise_and_connect())

        if self._machine_time_task is None:
            self._machine_time_task = asyncio.create_task(self._update_machine_time_characteristics())


    def stop(self):
        """Stop the BLE module."""
        pass


    def disconnect(self):
        """Disconnect the BLE device."""
        get_logger().info("BLE disconnected.")
        if self._event_handler:
            self._event_handler.on_disconnect()


    def update_bioinfo_data(
            self,
            temperature=None,
            humidity=None,
            pm2_5=None,
            co_concentration=None,
            keep_old=True):
        """
        Update the bioinfo characteristics with the provided values.

        Args:
            temperature (Optional[float]): The temperature data.
            humidity (Optional[float]): The humidity data. Within 0.0 .. 1.0. Raises ValueError if out of range.
            pm2_5 (Optional[float]): PM2.5 concentration in µg/m³. Raises ValueError if less than 0.
            co_concentration (Optional[float]): CO concentration in PPM. Raises ValueError if less than 0.
            keep_old (Optional[bool]): True to keep old values for missing fields, False to set missing fields to None.

        Returns:
            bool: True if successful, False otherwise.
        """


        # clear self.data if not keep old
        if not keep_old:
            for key in self._data:
                self._data[key] = float("-inf")
            
        # update the data
        if temperature:
            self._data["temperature"] = temperature
        if humidity:
            self._data["humidity"] = temperature
        if pm2_5:
            self._data["pm2_5"] = pm2_5
        if co_concentration:
            self._data["co_concentration"] = co_concentration

        self._data["last_update"] = time.ticks_ms() // 1000

        # write to the GATTS characteristics
        packed_data = struct.pack(
            '<ffffi',
            self._data["temperature"],
            self._data["humidity"],
            self._data["pm2_5"],
            self._data["co_concentration"],
            self._data["last_update"]
        )
        self.bioinfo_characteristic.write(packed_data)

        if self._event_handler is not None:
            self._event_handler.on_bioinfo_data_updated()

    
    def get_bioinfo_data(self):
        """
        Getter for bioinfo data.

        Fields:
            - temperature (float): The latest recorded temperature in degrees Celsius.
            - humidity (float): The relative humidity as a value between 0.0 and 1.0.
            - pm2_5 (float): PM2.5 concentration in micrograms per cubic meter (µg/m³).
            - co_concentration (float): Carbon monoxide (CO) concentration in parts per million (PPM).
            - last_update (int): The timestamp of the last data update in seconds.

        Returns:
            dict: A dictionary containing the latest bioinformatics data advertised.
        """
        return self._data
    

    async def send_response(self, msg):
        """
        Send a response to the client.

        Args:
            msg (str): the message to send to the client.
        
        Returns:
            bool: True if success, False otherwise.
        """
        try:
            if self.is_connected():
                await self.response_characteristic.indicate(
                    self._connection, 
                    data=msg.encode("utf-8"), 
                    timeout_ms=RESPONSE_TIMEOUT_MS
                )
                get_logger().info(f"Sent response: {msg}")
                return True
            else:
                get_logger().warning("Attempted to send response while no client connected")
                return False
        except asyncio.TimeoutError:
            get_logger().warning("Timed out on send response")
            return False

    
    def is_connected(self):
        """
        Whether a client is connected.

        Returns
            bool: True if there is a client connected, False otherwise.
        """
        if self._connection is None:
            return False
        else:
            return self._connection.is_connected()
        
    
    async def destroy(self):
        """
        Destroy the BLE wrapper and freeing up resources.
        """

        # Send a destroy signal
        get_logger().info("Sending destroy signal...")
        self._destroy_signal.set()

        # Wait for tasks to finish
        try:
            if isinstance(self._peripheral_task, asyncio.Task):
                await asyncio.wait_for(self._peripheral_task, timeout=10)

            if isinstance(self._machine_time_task, asyncio.Task):
                await asyncio.wait_for(self._machine_time_task, timeout=10)

            if isinstance(self._request_task, asyncio.Task):
                await asyncio.wait_for(self._request_task, timeout=10)

        except asyncio.TimeoutError:
            get_logger().warning("Destroy signal timed out, sending task cancel signal...")
            
            # cancel the tasks

            if isinstance(self._peripheral_task, asyncio.Task):
                self._peripheral_task.cancel()
            
            if isinstance(self._machine_time_task, asyncio.Task):
                self._machine_time_task.cancel()
            
            if isinstance(self._request_task, asyncio.Task):
                self._request_task.cancel()
            
            # wait for the tasks to be cancelled

            if isinstance(self._peripheral_task, asyncio.Task):
                await asyncio.wait_for(self._peripheral_task, timeout=10)
            
            if isinstance(self._machine_time_task, asyncio.Task):
                await asyncio.wait_for(self._machine_time_task, timeout=10)
            
            if isinstance(self._request_task, asyncio.Task):
                await asyncio.wait_for(self._request_task, timeout=10)
        
        get_logger().info("All tasks finished")
        
    