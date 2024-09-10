import time
from machine import Pin, Timer, UART, I2C

# Custom package

from dht20 import DHT20

# SETTINGS

LOGGING = True

# PINS (GPxx on the datasheet)

LED_PIN = 'LED'

DHT20_I2C = 0
DHT20_SDA_PIN = 20
DHT20_SCL_PIN = 21

# LED BLINK FOR MAKING SURE THE CODE IS RUNNING

led = Pin(LED_PIN, Pin.OUT)
timer = Timer()
led.toggle()
time.sleep(0.5)
led.toggle()
time.sleep(0.5)
led.toggle()

# DHT20

i2c_dht20 = I2C(DHT20_I2C, sda=Pin(DHT20_SDA_PIN), scl=Pin(DHT20_SCL_PIN))
dht20 = None
try:
    dht20 = DHT20(0x38, i2c_dht20)
except OSError as e:
    print(f"DHT20 init error: {e.value}")
    

def get_dht20_data(logging=LOGGING):
    print("DHT")
    global dht20
    
    # Reinitialize the DHT20 sensor if needed.
    if dht20 is None:
        try:
            dht20 = DHT20(0x38, i2c_dht20)
        except OSError as e:
            print(f"DHT20 init error: {e.value}")
            return
        
    # Try to read data from the sensor.
    try:
        if dht20.is_ready:
            measurements = dht20.measurements
            if logging:
                print(f"Temperature: {measurements['t']} °C, humidity: {measurements['rh']} %RH")
            return measurements
        else:
            return None
    # Error accessing the sensor, likely disconnected.
    except OSError as e:
        print(f"DHT20 disconnected: {e.value}")
        dht20 = None
        return
    
# MAIN LOOP
last_tick_time = time.time()
while True:
    try:
        if get_dht20_data():
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


