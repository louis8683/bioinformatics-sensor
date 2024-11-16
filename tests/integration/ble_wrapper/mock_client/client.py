# This is the client that is supposed to be run on a normal Python environment

import asyncio
import bleak
import struct
from bleak import BleakScanner, BleakClient


DEVICE_NAMES = ("bioinfo", "my-device") # Max length is 15 characters

# bioinfo-characteristics UUID
_BIO_INFO_CHARACTERISTICS_UUID = "9fda7cce-48d4-4b1a-9026-6d46eec4e63a"
# request-characteristics UUID
_REQUEST_CHARACTERISTICS_UUID = "4f2d7b8e-23b9-4bc7-905f-a8e3d7841f6a"
# response-characteristics UUID
_RESPONSE_CHARACTERISTICS_UUID = "93e89c7d-65e3-41e6-b59f-1f3a6478de45"
# machine-time-characteristics UUID
_MACHINE_TIME_CHARACTERISTICS_UUID = "4fd3a9d8-5e82-4c1e-a2d3-9bc23f3a8341"

SCAN_DURATION = 3
HANDSHAKE_MSG = "hello"
HANDSHAKE_TIMEOUT = 3
HANDSHAKE_RESPONSE = "howdy"


uuid_to_name = {
    "00001800-0000-1000-8000-00805f9b34fb": "Generic Access",
    "00001801-0000-1000-8000-00805f9b34fb": "Generic Attribute",
    "0000180a-0000-1000-8000-00805f9b34fb": "Device Information",
    "0000180f-0000-1000-8000-00805f9b34fb": "Battery Service",
    "0000181a-0000-1000-8000-00805f9b34fb": "Environmental Sensing",
    # Add other known service UUIDs here

    _BIO_INFO_CHARACTERISTICS_UUID: "bioinfo-characteristics"
}


class Client:

    def __init__(self) -> None:
        self.server_uuid: str = ""
        self.response_event = asyncio.Event()
        self.response_msg = None

        # Events
        self.stop_event = asyncio.Event()


    async def scan(self):
        # Scan for 5 seconds
        devices_and_adv_data = await BleakScanner.discover(timeout=SCAN_DURATION, return_adv=True)

        # List discovered devices
        if len(devices_and_adv_data) == 0:
            print("No device discovered.")
            return

        valid_uuids = []
        for device, adv_data in devices_and_adv_data.values():
            if device.name in DEVICE_NAMES:
                valid_uuids.append(device.address)
                print(f"({len(valid_uuids)}) Found Device: {device.name}, Address: {device.address}")
                print(f"Advertising Services:")
                for uuid in adv_data.service_uuids:
                    if uuid in uuid_to_name:
                        print("-", uuid_to_name[uuid])
                    else:
                        print("-", uuid)
                print(f"Manufacturer Data: {adv_data.manufacturer_data}") 
        
        if len(valid_uuids) == 0:
            print("No bioinformatics device found")
            return

        while True:
            selection = input(f"Please select a device from 1 to {len(valid_uuids)}: ")
            try:
                selection = int(selection)
                if 1 <= selection <= len(valid_uuids):
                    break
            except TypeError:
                selection = ""
            print("invalid input")
        
        print(f"Selected device: {valid_uuids[selection - 1]}")
        self.server_uuid = valid_uuids[selection - 1]
        return self.server_uuid
    

    def response_handler(self, sender, data):
        print("Received response")

        try:
            msg = data.decode("utf-8")
            self.response_msg = msg
            print(f"response: {msg}")
        except UnicodeDecodeError:
            self.response_msg = None
            print("Unable to decode response")
        
        self.response_event.set()
    

    async def connect(self):
        if self.server_uuid == "":
            return False
        
        async with BleakClient(self.server_uuid) as client:
            if client.is_connected:
                print(f"Connected to {self.server_uuid}")

                # Start subscribing to indications from the characteristic
                await client.start_notify(
                    _RESPONSE_CHARACTERISTICS_UUID, 
                    self.response_handler
                )
                print("Subscribed to the response indication") 

                try:
                    # Write the handshake message to the request characteristic 
                    message = HANDSHAKE_MSG.encode("utf-8")
                    await client.write_gatt_char(_REQUEST_CHARACTERISTICS_UUID, message, response=True)
                    print("Initiated handshake.")
                except Exception as e:
                    print(f"Failed to write to characteristic: {e}")

                try:                
                    await asyncio.wait_for(self.response_event.wait(), timeout=HANDSHAKE_TIMEOUT)
                    if self.response_msg == HANDSHAKE_RESPONSE:
                        print("Handshake success.")
                    else:
                        print(f"Handshake failed (Bad response). Response: {self.response_msg}")
                except asyncio.TimeoutError:
                    print("Handshake failed (TIMEOUT)")
                
                # Console loop
                await self.ui_loop(client)
                        
                
            else:
                print(f"Failed to connect to {self.server_uuid}")
        
        return True
    

    async def ui_loop(self, client: BleakClient):
        while client.is_connected:
            self.stop_event.clear()
            selection = input("Choose a characteristics to monitor (1-3) or (4) to send commands: ")

            if selection == "1":
                print("You've chosen the 'Machine-time characteristics'")
            elif selection == "2":
                print("You've chosen the  'Bioinfo characteristics'")
            elif selection == "4":
                self.response_event.clear()
                cmd_str = input(f"Please enter the command string: (MTU={client.mtu_size})")
                await client.write_gatt_char(_REQUEST_CHARACTERISTICS_UUID, cmd_str.encode("utf-8"), response=True)

                try:
                    await asyncio.wait_for(self.response_event.wait(), timeout=HANDSHAKE_TIMEOUT)
                except asyncio.TimeoutError:
                    print("Response timed out")

            else:
                print("Invalid task selection. Please try again.")
                continue
            
            selection = int(selection)
            if 1 <= selection <= 3:

                duration = input("How long would you like to monitor? (default is 10s)")
                try:
                    duration = int(duration)
                    if duration < 0:
                        duration = 10
                except ValueError:
                    duration = 10
                
                task = asyncio.create_task(self.monitor_time(client)) if selection == "1" else asyncio.create_task(self.monitor_bioinfo(client)) 
                await asyncio.sleep(duration)
                self.stop_event.set()
                await task


    async def monitor_time(self, client: BleakClient):
        while client.is_connected and not self.stop_event.is_set():
            data = await client.read_gatt_char(_MACHINE_TIME_CHARACTERISTICS_UUID)
            time_stamp = struct.unpack("<i", data)[0]
            print(f"machine-time-characteristics: {time_stamp}")
            await asyncio.sleep(1)

    
    async def monitor_bioinfo(self, client: BleakClient):
        while client.is_connected and not self.stop_event.is_set():
            data = await client.read_gatt_char(_BIO_INFO_CHARACTERISTICS_UUID)
            # Unpack the data using the same format string used to pack it
            unpacked_data = struct.unpack('<ffffI', data)
            # Assign unpacked values to meaningful variables
            temperature, humidity, pm2_5, co_concentration, last_update = unpacked_data
            print(f"bioinfo-characteristics: {unpacked_data}")
            await asyncio.sleep(1)

    
    def send_data(self, data):
        pass

    def receive_data(self, data):
        pass

    def _handshake(self):
        pass


async def main():
    client = Client()
    await client.scan()
    await client.connect()


if __name__ == "__main__":
    asyncio.run(main())
