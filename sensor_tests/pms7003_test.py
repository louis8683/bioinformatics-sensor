import time
from machine import Pin, Timer, UART, I2C

# Custom package

from pms7003 import Pms7003

# SETTINGS

LOGGING = True

# PINS (GPxx on the datasheet)

LED_PIN = 'LED'

PMS7003_UART = 1
PMS7003_TX_PIN = 8
PMS7003_RX_PIN = 9

# LED BLINK FOR MAKING SURE THE CODE IS RUNNING

led = Pin(LED_PIN, Pin.OUT)
timer = Timer()
led.toggle()
time.sleep(0.5)
led.toggle()
time.sleep(0.5)
led.toggle()

# PMS7003

class Pms7003Timeout(Pms7003):
    def __init__(self, uart):
        self.uart = machine.UART(uart, baudrate=9600, bits=8, parity=None, stop=1, timeout=10, timeout_char=10)

pms = Pms7003(PMS7003_UART)
pms.uart.init(tx=Pin(PMS7003_TX_PIN), rx=Pin(PMS7003_RX_PIN))

# TODO: remove this when testing PMS7003
# Also, fix the bug when PMS7003 is not connected, it gets stuck.
# pms = None

def get_pms7003_data(logging=LOGGING):
    print("PMS")
    try:
        if pms and pms.uart.any():
            data = pms.read()
            if logging:
                print(data)
            return data
        else:
            return None
    except Exception as e:
        print(f"PMS read error: {e.value}")
    
# MAIN LOOP
last_tick_time = time.time()
while True:
    try:
        if get_pms7003_data():
            pass
        else:
            if time.time() - last_tick_time >= 1:
                last_tick_time = time.time()
                print("Tick (per second)")
                
            led.toggle()
            time.sleep(0.25)
            led.toggle()
    except TypeError as e:
        print(f"Error: {e.value}")
        continue
    # get_ze07_data()
    # get_dht20_data()
    # get_pms7003_data()


