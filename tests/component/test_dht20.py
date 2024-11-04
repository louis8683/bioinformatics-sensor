import asyncio
import time

from dht20 import DHT20


RUN_TIME = 10


async def test_dht20_start():
    dht20 = DHT20(debug=False)
    assert await dht20.start()
    assert isinstance(dht20._data_update_task, asyncio.Task)
    assert not dht20._data_update_task.done()
    await dht20.destroy()


async def test_dht20_destroy():
    dht20 = DHT20(debug=False)
    await dht20.start()
    await dht20.destroy()
    assert isinstance(dht20._data_update_task, asyncio.Task)
    assert dht20._data_update_task.done() or dht20._data_update_task.cancelled()


async def test_dht20_get_latest_immutable():
    """
    Test that we won't change the internal data by changing the output data.
    """
    dht20 = DHT20(debug=False)
    data = dht20.get_latest()
    data["test"] = False
    assert dht20.get_latest().get("test", True)


async def test_dht20_data_update_service():
    # TODO: create a Fake I2C for testing these functions
    pass


async def test_dht20():
    print("Starting test: test_dht20")
    dht20 = DHT20(interval=0.5, debug=False)
    assert await dht20.start()
    
    # read out 10 seconds of data
    print("reading data...")
    results = []
    start_time = time.ticks_ms()
    end_time = start_time + RUN_TIME * 1000
    while time.ticks_ms() < end_time:
        # if dht20._data_update_task:
        #     print(dht20._data_update_task.done())

        data = dht20.get_latest()

        # did the data updated?
        if results and results[-1]["timestamp"] == data["timestamp"]:
            continue
        else:
            print(f"Received new data: {data}")
            results.append(data)
        
        await asyncio.sleep(1)
    # print the results
    print(results)

    # destroy the DHT20
    print("terminating the class...")
    await dht20.destroy()


async def main():
    await test_dht20_start()
    await test_dht20_destroy()
    await test_dht20_get_latest_immutable()
    await test_dht20_data_update_service()

    await test_dht20()

asyncio.run(main())
