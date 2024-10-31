import bluetooth
import aioble
import asyncio
import random
import struct
from micropython import const
import time

from .ble_event_handler import BLEEventHandler


# org.bluetooth.service.environmental_sensing
_ENV_SENSE_UUID = bluetooth.UUID(0x181A)
# org.bluetooth.characteristic.temperature
_ENV_SENSE_TEMP_UUID = bluetooth.UUID(0x2A6E)
# org.bluetooth.characteristic.gap.appearance.xml
_ADV_APPEARANCE_GENERIC_THERMOMETER = const(768)

# bioinfo-characteristics UUID
_BIO_INFO_CHARACTERISTICS_UUID = bluetooth.UUID("9fda7cce-48d4-4b1a-9026-6d46eec4e63a")
# request-characteristics UUID
_REQUEST_CHARACTERISTICS_UUID = bluetooth.UUID("4f2d7b8e-23b9-4bc7-905f-a8e3d7841f6a")
# response-characteristics UUID
_RESPONSE_CHARACTERISTICS_UUID = bluetooth.UUID("93e89c7d-65e3-41e6-b59f-1f3a6478de45")
# machine-time-characteristics UUID
_MACHINE_TIME_CHARACTERISTICS_UUID = bluetooth.UUID("4fd3a9d8-5e82-4c1e-a2d3-9bc23f3a8341")

# expected handshake message from client
HANDSHAKE_MSG = "hello"
HANDSHAKE_TIMEOUT_MS = 1000

# How frequently to send advertising beacons.
_ADV_INTERVAL_MS = 250_000


class BLEWrapper:
    """
    BLE wrapper for event-based interfaces.
    """
    
    def __init__(self, name="bioinfo", event_handler=None):
        """
        Initialize the BLE module with optional parameters.
        
        :param name: The BLE device name to be set on initialization.
        """

        print("BLEWrapper initializing...")

        self.name = name
        self.connection = None # Type of "aioble.DeviceConnection"
        self.service_uuids = [_ENV_SENSE_UUID]
        self.event_handler = event_handler
        self.data = {
            "temperature": float("-inf"), # float
            "humidity": float("-inf"), # float
            "pm2_5": float("-inf"), # float
            "co_concentration": float("-inf"), # float
            "last_update": -1 # int, time.tick_ms // 1000
        }

        # Events
        self.destroy_signal = asyncio.Event()
        self.handshake_event = asyncio.Event()

        # Tasks
        self.peripheral_task = None
        self.machine_time_task = None

        # Initialize BLE
        self._register_gatt_server()


        

        print("Init done.")

    
    def _register_gatt_server(self): # TODO: modify to fit our purposes
        # Register GATT server.
        self.bioinfo_service = aioble.Service(_ENV_SENSE_UUID)
        self.bioinfo_characteristic = aioble.Characteristic(
            service=self.bioinfo_service,
            uuid=_BIO_INFO_CHARACTERISTICS_UUID,
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
            uuid=_MACHINE_TIME_CHARACTERISTICS_UUID,
            read=True,
        )
        
        self.request_characteristic = aioble.Characteristic(
            service=self.bioinfo_service,
            uuid=_REQUEST_CHARACTERISTICS_UUID,
            write=True
        )

        self.response_characteristic = aioble.Characteristic(
            service=self.bioinfo_service,
            uuid=_RESPONSE_CHARACTERISTICS_UUID,
            indicate=True,
        )

        

        aioble.register_services(self.bioinfo_service)

    
    async def _handshake(self, connection):
        """
        Perform handshake procedure with client. Used to verify client legitimacy when establishing connection.

        Returns
            bool: True if success, False if failed.
        """
        print("Handshake in progress...")
        valid_handshake = False
        try:
            await self.request_characteristic.written(timeout_ms=HANDSHAKE_TIMEOUT_MS)
            data = self.request_characteristic.read()
            if len(data) > 0 and data.decode("utf-8") == HANDSHAKE_MSG:
                response_msg = "howdy".encode("utf-8")
                print("Responding to the handshake...")
                await self.response_characteristic.indicate(
                    connection, 
                    data=response_msg, 
                    timeout_ms=HANDSHAKE_TIMEOUT_MS
                )
                print("Handshake successful.")
                valid_handshake = True
            elif len(data) > 0:
                message = data.decode("utf-8")
                print(f"Bad handshake message: {message}. Closing connection...")
            else:
                print("Empty handshake, closing connection...")
        # except UnicodeDecodeError: # NameError: name 'UnicodeDecodeError' isn't defined
        #     print("Unable to decode handshake message. Closing connection...")
        except asyncio.TimeoutError:
            print("TIMEOUT on handshake. Closing connection...")
        except aioble.DeviceDisconnectedError:
            print("Device has disconnected prematurely. Closing connection...")
        except Exception as e:
            print(f"Unknown error of type {type(e).__name__}: {e}. Closing connection...")
        
        return valid_handshake


    # Serially wait for connections. Don't advertise while a central is
    # connected.
    async def _advertise_and_connect(self):
        """
        This private function handles the forever loop between advertisement and connection states.
        """
        print("Starting advertisment/connection loop...")
        try:
            while True:
                async with await aioble.advertise(
                    _ADV_INTERVAL_MS,
                    name=self.name,
                    services=self.service_uuids,
                    appearance=_ADV_APPEARANCE_GENERIC_THERMOMETER,
                ) as connection:
                    # Initialize the connection
                    self.connection = connection

                    print("Connection from", connection.device)

                    if self.event_handler is not None:
                        self.event_handler.on_connect()

                    # Handshake
                    valid_handshake = await self._handshake(connection)

                    # Either wait for disconnection or disconnect directly according to the handshake result.
                    if valid_handshake:
                        if self.event_handler is not None:
                            self.event_handler.on_handshake_success()
                        await connection.disconnected()
                    else:
                        await connection.disconnected(disconnect=True)

                    print("Disconnected")

                    if self.event_handler is not None:
                        self.event_handler.on_disconnect()


                    # clean up after disconnection
                    self.connection = None

                    # break from the loop if we want to destroy the BLEWrapper
                    if self.destroy_signal.is_set():
                        break
        except AttributeError as e:
            # the aioble.advertise returns a None
            print(f"advertise/connection loop failed: {e}")
        except asyncio.CancelledError:
            # task is cancelled through "task.cancel()", which is a backup plan for setting the destroy signal
            print("Peripheral task forced cancelled.")


    def _encode_int(self, val):
        return struct.pack("<i", val)
    
    
    def _encode_float(self, val):
        return struct.pack("<f", val)
    

    # update the time characteristics every one second
    async def _update_machine_time_characteristics(self):
        """
        Update the machine-time-characteristics every 1 second
        """

        # NOTE: we did not deal with the wrap-around issue with tick_ms (which occurs in roughly 24 days)
        try:
            while True:
                current_time = time.ticks_ms()
                time_data = self._encode_int(current_time // 1000)
                self.machine_time_characteristics.write(time_data)

                # sleep for a second
                await asyncio.sleep(1)

                # check for destroy signal
                if self.destroy_signal.is_set():
                    break
        except asyncio.CancelledError:
            pass

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


    async def start(self):
        """
        Start the BLE module (e.g., begin advertising).
        
        The advertisement/connection task is started in a coroutine with asyncio.
        """
        print("BLE started and advertising...")
        
        # create the task if not created yet
        if self.peripheral_task is None:
            self.peripheral_task = asyncio.create_task(self._advertise_and_connect())

        if self.machine_time_task is None:
            self.machine_time_task = asyncio.create_task(self._update_machine_time_characteristics())



    def stop(self):
        """Stop the BLE module."""
        pass


    def disconnect(self):
        """Disconnect the BLE device."""
        print("BLE disconnected.")
        if self.event_handler:
            self.event_handler.on_disconnect()


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
            for key in self.data:
                self.data[key] = float("-inf")
            
        # update the data
        if temperature:
            self.data["temperature"] = temperature
        if humidity:
            self.data["humidity"] = temperature
        if pm2_5:
            self.data["pm2_5"] = pm2_5
        if co_concentration:
            self.data["co_concentration"] = co_concentration

        self.data["last_update"] = time.ticks_ms() // 1000

        # write to the GATTS characteristics
        packed_data = struct.pack(
            '<ffffi',
            self.data["temperature"],
            self.data["humidity"],
            self.data["pm2_5"],
            self.data["co_concentration"],
            self.data["last_update"]
        )
        self.bioinfo_characteristic.write(packed_data)



    
    def is_connected(self):
        if self.connection is None:
            return False
        else:
            return self.connection.is_connected()
        
    
    async def destroy(self):
        """
        Destroy the BLE wrapper and freeing up resources.
        """

        # Send a destroy signal
        print("Sending destroy signal...")
        self.destroy_signal.set()

        # Wait for tasks to finish
        try:
            if isinstance(self.peripheral_task, asyncio.Task):
                await asyncio.wait_for(self.peripheral_task, timeout=10)

            if isinstance(self.machine_time_task, asyncio.Task):
                await asyncio.wait_for(self.machine_time_task, timeout=10)

        except asyncio.TimeoutError:
            print("Destroy signal timed out, sending task cancel signal...")
            if isinstance(self.peripheral_task, asyncio.Task):
                self.peripheral_task.cancel()
            
            if isinstance(self.machine_time_task, asyncio.Task):
                self.machine_time_task.cancel()
            
            if isinstance(self.peripheral_task, asyncio.Task):
                await asyncio.wait_for(self.peripheral_task, timeout=10)
            
            if isinstance(self.machine_time_task, asyncio.Task):
                await asyncio.wait_for(self.machine_time_task, timeout=10)
        
        print("All tasks finished")
        
            

    