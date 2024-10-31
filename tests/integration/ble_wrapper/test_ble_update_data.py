import asyncio
import time
from ble_wrapper import BLEWrapper, BLEEventHandler


connection_event = asyncio.Event()
handshake_success_event = asyncio.Event()
disconnect_event = asyncio.Event()

class TestEventHandler(BLEEventHandler):
    def on_connect(self):
        connection_event.set()

    def on_handshake_success(self):
        print("received handshake success event")
        handshake_success_event.set()

    def on_disconnect(self):
        disconnect_event.set()

    def on_data_send(self):
        pass

    def on_command(self, command):
        pass

    def on_data_sent(self, data):
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

    # update the data periodically, and observe the change
    temperature = 0.0
    humidity = 0.0
    pm2_5 = 0.0
    co_concentration = 0.0
    
    for i in range(20):
        ble_wrapper.update_bioinfo_data(
            temperature=temperature,
            humidity=humidity,
            pm2_5=pm2_5,
            co_concentration=co_concentration,
            keep_old=False
        )

        temperature += 0.1
        humidity += 0.01
        pm2_5 += 0.1
        co_concentration += 0.1

        print(f"values: ({(temperature, humidity, pm2_5, co_concentration)})")
        await asyncio.sleep(0.5)

    # wait for a disconnection
    print("(waiting for disconnection)")    
    await asyncio.wait_for(disconnect_event.wait(), 60)
    
    print("(disconnected)")

    await ble_wrapper.destroy()


async def main():
    print("(in main)")
    await test_ble_handshake()


print("Testing BLE handshake...")
asyncio.run(main())
assert handshake_success_event.is_set()
print("SUCCESS")

# try:
#     print("Testing BLE handshake...")
#     asyncio.run(main())
#     assert handshake_success_event.is_set()
#     print("SUCCESS")
# except AssertionError:
#     print("FAILED, handshake not successful")
# except Exception as e:
#     print(f"FAILED, exception: {e}")

