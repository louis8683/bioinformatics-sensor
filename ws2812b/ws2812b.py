import machine
import neopixel
import uasyncio as asyncio

RED = (255, 0, 0)
ORANGE = (255, 165, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
OFF = (0, 0, 0)

class WS2812B:

    def __init__(self, pin=11, num_leds=8, brightness=0.02):
        self.pin = pin
        self.num_leds = num_leds
        self.brightness = brightness
        self.np = neopixel.NeoPixel(machine.Pin(self.pin), self.num_leds)
        self.blinking_task = None
        self.running = False

    def clear_strip(self):
        """Turn off all LEDs."""
        self.set_color(OFF)

    def apply_brightness(self, color):
        """Apply brightness to the color using the set brightness factor."""
        return tuple(min(255, max(0, int(c * self.brightness))) for c in color)

    def set_color(self, color):
        """Set the entire strip to one color."""
        dimmed_color = self.apply_brightness(color)
        for i in range(self.num_leds):
            self.np[i] = dimmed_color
        self.np.write()

    def start_blinking(self, color, interval=0.5):
        """Start a non-blocking blinking effect with the specified color."""
        if self.blinking_task:
            print("Stopping previous blinking task.")
            self.stop_blinking()

        print(f"Starting blinking: {color}")
        self.running = True
        self.blinking_task = asyncio.create_task(self._blink_loop(color, interval))

    async def _blink_loop(self, color, interval):
        """Internal coroutine to handle blinking without blocking the main thread."""
        while self.running:
            self.set_color(color)
            await asyncio.sleep(interval)
            self.clear_strip()
            await asyncio.sleep(interval)

    def stop_blinking(self):
        """Stop the blinking effect."""
        if self.blinking_task:
            self.running = False
            self.blinking_task.cancel()
            self.blinking_task = None
            self.clear_strip()

    # Explicit Methods for Use Cases
    def low_battery(self):
        print("Displaying Low Battery (Red)")
        self.set_color(RED)

    def medium_battery(self):
        print("Displaying Medium Battery (Orange)")
        self.set_color(ORANGE)

    def full_battery(self):
        print("Displaying Full Battery (Green)")
        self.set_color(GREEN)

    def connected(self):
        print("Displaying Connected (Solid Blue)")
        self.stop_blinking()
        self.set_color(BLUE)

    def disconnected(self):
        print("Displaying Disconnected (Flashing Blue)")
        self.start_blinking(BLUE)


async def main():
    print("Initializing LED strip...")
    led_strip = WS2812B(pin=11, num_leds=8, brightness=0.02)

    try:
        # Test Low Battery (Red)
        print("Testing Low Battery State (Red)")
        led_strip.low_battery()
        await asyncio.sleep(2)

        # Test Medium Battery (Orange)
        print("Testing Medium Battery State (Orange)")
        led_strip.medium_battery()
        await asyncio.sleep(2)

        # Test Full Battery (Green)
        print("Testing Full Battery State (Green)")
        led_strip.full_battery()
        await asyncio.sleep(2)

        # Test Connected State (Solid Blue)
        print("Testing Connected State (Solid Blue)")
        led_strip.connected()
        await asyncio.sleep(2)

        # Test Disconnected State (Flashing Blue)
        print("Testing Disconnected State (Flashing Blue)")
        led_strip.disconnected()
        await asyncio.sleep(5)

        # Stop Blinking and Clear
        print("Stopping Blink and Clearing LEDs")
        led_strip.stop_blinking()
        led_strip.clear_strip()

    except KeyboardInterrupt:
        print("Interrupted. Stopping and Clearing LEDs.")
        led_strip.stop_blinking()
        led_strip.clear_strip()


if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())