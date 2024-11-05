import asyncio

from ze07co import ZE07CO

async def test_ze07co():
    ze07co = ZE07CO(debug=True)
    assert await ze07co.start()

    await asyncio.sleep(10)

    await ze07co.destroy()


async def main():
    await test_ze07co()


asyncio.run(main())