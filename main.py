import asyncio

from ble_wrapper import BLEWrapper, BLECommands
from state import Context


async def main():

    # Instantiate a BLE wrapper
    print("Initialize the BLE...")
    ble_wrapper = BLEWrapper("MyDeviceName")

    # Instantiate the device context
    print("Initialize the context...")
    context = Context(ble_wrapper)

    # Start the application lifecycle
    print("Device starting...")
    await context.start()


try:
    print("Starting project...")
    asyncio.run(main())
except KeyboardInterrupt:
    print("Program terminated by user.")
