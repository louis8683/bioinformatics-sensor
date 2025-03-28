import asyncio

from ble_wrapper import BLEWrapper, BLECommands
from state import Context, AdvertiseState

from time import sleep
from machine import Pin

led = Pin('LED', Pin.OUT)

async def main():

    # Toggle the LED on
    led.value(1)

    # Instantiate a BLE wrapper
    print("Initialize the BLE...")
    ble_wrapper = BLEWrapper("MyDeviceName")

    # Instantiate the device context
    print("Initialize the context...")
    context = Context(AdvertiseState)

    # Start the application lifecycle
    print("Device starting...")
    await context.start()


try:
    print("Starting project...")
    asyncio.run(main())
except KeyboardInterrupt:
    print("Program terminated by user.")
