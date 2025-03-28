import machine
import neopixel
import time

# Configuration
NUM_LEDS = 1
LED_PIN = 11
BRIGHTNESS = 0.02  # Adjust between 0 (off) to 1 (full brightness)

# Initialize NeoPixel
np = neopixel.NeoPixel(machine.Pin(LED_PIN), NUM_LEDS)

def clear_strip():
    for i in range(NUM_LEDS):
        np[i] = (0, 0, 0)
    np.write()

def apply_brightness(color):
    return tuple(int(c * BRIGHTNESS) for c in color)

def set_color(color):
    dimmed_color = apply_brightness(color)
    for i in range(NUM_LEDS):
        np[i] = dimmed_color
    np.write()

def flash_color(color, interval=0.5, repeats=5):
    for _ in range(repeats):
        set_color(color)
        time.sleep(interval)
        clear_strip()
        time.sleep(interval)


def main():
    colors = [
        (255, 0, 0),    # Red - Low Battery
        (255, 165, 0),  # Orange - Medium Battery
        (0, 255, 0),    # Green - Full Battery
        (0, 0, 255),    # Solid Blue - Connected
        (0, 0, 255)     # Flashing Blue - Disconnected
    ]

    while True:
        print("Displaying: Red (Low Battery)")
        set_color(colors[0])
        time.sleep(2)

        print("Displaying: Orange (Medium Battery)")
        set_color(colors[1])
        time.sleep(2)

        print("Displaying: Green (Full Battery)")
        set_color(colors[2])
        time.sleep(2)

        print("Displaying: Solid Blue (Connected)")
        set_color(colors[3])
        time.sleep(2)

        print("Displaying: Flashing Blue (Disconnected)")
        flash_color(colors[4])

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting. Clearing LEDs.")
        clear_strip()