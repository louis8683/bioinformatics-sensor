import asyncio
import time
from ble_wrapper import BLEWrapper, BLEEventHandler, BLECommands


connection_event = asyncio.Event()
handshake_success_event = asyncio.Event()
disconnect_event = asyncio.Event()
biodata_update_event = asyncio.Event()
command_event = asyncio.Event()
latest_command = None

class TestEventHandler(BLEEventHandler):
    def on_connect(self):
        connection_event.set()

    def on_handshake_success(self):
        print("received handshake success event")
        handshake_success_event.set()

    def on_disconnect(self):
        disconnect_event.set()

    def on_bioinfo_data_updated(self):
        biodata_update_event.set()

    def on_command(self, command):
        global latest_command
        command_event.set()
        latest_command = command

    def on_data_sent(self, data):
        pass


async def command_loop():
    try:
        while True:
            try:
                await asyncio.wait_for(command_event.wait(), 10)
                print(f"latest command: {latest_command}")
                command_event.clear()
            except asyncio.TimeoutError:
                pass
    except asyncio.CancelledError:
        pass


async def test_ble_handshake():
    print("(in test)")
    ble_wrapper = BLEWrapper()
    await ble_wrapper.start()
    ble_wrapper.set_event_handler(TestEventHandler())
    
    # wait for a connection
    print("(waiting for connection)")
    await asyncio.wait_for(connection_event.wait(), 60)

    # connected
    print("(connected)")

    # wait for the handshake to complete
    await asyncio.wait_for(handshake_success_event.wait(), 10)

    # start the command loop
    command_task = asyncio.create_task(command_loop())

    # wait for a disconnection
    print("(waiting for disconnection)")    
    await asyncio.wait_for(disconnect_event.wait(), 60)
    
    print("(disconnected)")

    # cleanup
    command_task.cancel()
    await ble_wrapper.destroy()


async def main():
    print("(in main)")
    await test_ble_handshake()


try:
    print("Testing BLE data update...")
    asyncio.run(main())
    print("SUCCESS")
except AssertionError:
    print("FAILED, handshake not successful")
except Exception as e:
    print(f"FAILED, exception: {e}")

