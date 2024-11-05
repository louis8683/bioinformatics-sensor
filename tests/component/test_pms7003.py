import asyncio

from pms7003 import PMS7003

async def test_pms7003():
    pms7003 = PMS7003(debug=True)
    assert await pms7003.start()

    await asyncio.sleep(10)

    await pms7003.destroy()


async def main():
    await test_pms7003()


asyncio.run(main())