import asyncio

from ble_wrapper import BLEWrapper, BLECommands
from state import Context, AdvertiseState

from time import sleep
from machine import Pin

led = Pin('LED', Pin.OUT) 

EN_PIN = Pin(2, Pin.OUT) 
EN_PIN.high()

async def main():

    # Toggle the LED on
    led.value(1)

    # Instantiate a BLE wrapper
    ble_wrapper = BLEWrapper()

    # Instantiate the device context
    context = Context(AdvertiseState)

    # Start the application lifecycle
    await context.start()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Program terminated by user.")
