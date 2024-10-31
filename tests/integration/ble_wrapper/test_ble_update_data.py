import asyncio
import time
from ble_wrapper import BLEWrapper, BLEEventHandler


connection_event = asyncio.Event()
handshake_success_event = asyncio.Event()
disconnect_event = asyncio.Event()
biodata_update_event = asyncio.Event()

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
        pass

    def on_data_sent(self, data):
        pass


async def compare_updated_values(ble_wrapper, data_container):
    try:
        while True:
            try:
                await asyncio.wait_for(biodata_update_event.wait(), 10)
                ble_data = ble_wrapper.get_bioinfo_data()

                for key in ble_data:
                    if key != "last_update":
                        assert ble_data[key] == data_container[key]

            except asyncio.TimeoutError:
                continue
    except asyncio.CancelledError:
        return
    


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
    data = {
        "temperature": 0.0,
        "humidity": 0.0,
        "pm2_5": 0.0,
        "co_concentration": 0.0,
        "last_update": 0
    }
    
    assert_task = asyncio.create_task(compare_updated_values(ble_wrapper, data))

    for i in range(20):
        ble_wrapper.update_bioinfo_data(
            temperature=data["temperature"],
            humidity=data["humidity"],
            pm2_5=data["pm2_5"],
            co_concentration=data["co_concentration"],
            keep_old=False
        )

        data["temperature"] += 0.1
        data["humidity"] += 0.01
        data["pm2_5"] += 0.1
        data["co_concentration"] += 0.1

        print(f"values: {data}")
        await asyncio.sleep(0.5)


    # kill the assert task
    assert_task.cancel()
    await asyncio.wait_for(assert_task, timeout=10)

    # wait for a disconnection
    print("(waiting for disconnection)")    
    await asyncio.wait_for(disconnect_event.wait(), 60)
    
    print("(disconnected)")

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

