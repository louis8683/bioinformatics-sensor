import asyncio

from ble_wrapper import BLEEventHandler, BLECommands

from .utilities import get_logger


class State(BLEEventHandler):
    def __init__(self, context):
        self.context = context
        self.tasks = []  # Store references to spawned tasks


    def start_task(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.tasks.append(task)


    def cancel_tasks(self):
        for task in self.tasks:
            task.cancel()
        self.tasks.clear()


    def enter(self):
        """
        Important: Do NOT block this function. Use coroutines for blocking tasks.
        """
        get_logger().info(f"Entering {self.__class__.__name__}")


    def exit(self):
        self.cancel_tasks()
        get_logger().info(f"Exiting {self.__class__.__name__}")
    

    # *** OVERRIDES FOR THE BLEEventHandler INTERFACE ***


    def on_connect(self):
        pass

    def on_handshake_success(self):
        pass

    def on_disconnect(self):
        pass

    def on_bioinfo_data_updated(self):
        pass

    def on_command(self, command, argument):
        pass
