import asyncio
import time

from ble_wrapper import BLEWrapper, BLECommands
from state import Context


async def test_context_cleanup():

    ble_wrapper = BLEWrapper("MyDeviceName")

    context = Context(ble_wrapper)

    asyncio.run(context.start())

    # wait for 1 seconds
    time.sleep(1)

    asyncio.run(context.cleanup())

    assert ble_wrapper.connected == False
    assert ble_wrapper._event_handler is not None


async def main():
    await test_context_cleanup()


try:
    print("Testing context cleanup...")
    asyncio.run(main())
    print("PASS")
except AssertionError:
    print("FAIL")
