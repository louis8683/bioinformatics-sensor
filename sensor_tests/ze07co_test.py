import time
from machine import Pin, Timer, UART, I2C

# SETTINGS

LOGGING = True

# PINS (GPxx on the datasheet)

LED_PIN = 'LED'

ZE07_UART = 0
ZE07_TX_PIN = 12
ZE07_RX_PIN = 13

# LED BLINK FOR MAKING SURE THE CODE IS RUNNING

led = Pin(LED_PIN, Pin.OUT)
timer = Timer()
led.toggle()
time.sleep(0.5)
led.toggle()
time.sleep(0.5)
led.toggle()

# ZE07-CO

uart_ZE07 = UART(ZE07_UART, baudrate=9600, timeout=50, timeout_char=50)
uart_ZE07.init(bits=8, parity=None, stop=1, tx=Pin(ZE07_TX_PIN), rx=Pin(ZE07_RX_PIN))

def get_ze07_data(logging=LOGGING):
    print("ZE07")
    # if there is data
    if not uart_ZE07.any():
        return None
    
    # read and parse the data
    data = uart_ZE07.read()
    try:
        concentration = ((data[4] << 8) + data[5]) * 0.1    
        full_range = (data[6] * 256 + data[7]) * 0.1 # same as shifting 8 bits
        # log to STDOUT
        if logging:
            print("-----LOG ZE07----")
            print("LOG: ZE07 DATA")
            print(f"Data Frame: {data}")
            print(f"Concentration = {concentration} ppm") 
            print(f"Full Range = {full_range} ppm")
            print("-----END LOG-----")
        return (concentration, full_range)
    except IndexError as e:
        print("ZE07 read error: bad data")
    
# MAIN LOOP
last_tick_time = time.time()
while True:
    try:
        if get_ze07_data():
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


