import asyncio

from state import Context
from state import AdvertiseState


context = Context(AdvertiseState, debug=True)
asyncio.run(context.start())
