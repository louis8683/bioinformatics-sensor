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
ZE07_UART = 0
ZE07_TX_PIN = 12
ZE07_RX_PIN = 13
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

# ------- DHT20 ----------

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

# ------- ZE07-CO ----------

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
        
# ------- PMS7003 ----------



# This code base follows the description of the datasheet
# https://download.kamami.pl/p564008-PMS7003%20series%20data%20manua_English_V2.5.pdf

# Active mode for PMS7003
uart_pms = UART(PMS7003_UART, baudrate=9600, stop=1, timeout=50, timeout_char=50)
uart_pms.init(tx=Pin(PMS7003_TX_PIN), rx=Pin(PMS7003_RX_PIN))

# Command to switch to active mode
cmd = bytearray([0xe1, 0x00, 0x01])
uart_pms.write(cmd)

def parse_pm_sensor_data(data):
    if len(data) < 32:
        raise ValueError("Data length is too short")

    # Start characters validation
    if data[0] != 0x42 or data[1] != 0x4d:
        raise ValueError("Invalid start characters")

    # Frame length (2 bytes, but we'll skip over it for now)
    frame_length = (data[2] << 8) | data[3]

    # Data 1 - PM1.0 concentration (CF=1)
    pm1_0_cf1 = (data[4] << 8) | data[5]

    # Data 2 - PM2.5 concentration (CF=1)
    pm2_5_cf1 = (data[6] << 8) | data[7]

    # Data 3 - PM10 concentration (CF=1)
    pm10_cf1 = (data[8] << 8) | data[9]

    # Data 4 - PM1.0 concentration (atmospheric environment)
    pm1_0_atm = (data[10] << 8) | data[11]

    # Data 5 - PM2.5 concentration (atmospheric environment)
    pm2_5_atm = (data[12] << 8) | data[13]

    # Data 6 - PM10 concentration (atmospheric environment)
    pm10_atm = (data[14] << 8) | data[15]

    # Data 7 - Number of particles with diameter > 0.3um
    particles_03um = (data[16] << 8) | data[17]

    # Data 8 - Number of particles with diameter > 0.5um
    particles_05um = (data[18] << 8) | data[19]

    # Data 9 - Number of particles with diameter > 1.0um
    particles_10um = (data[20] << 8) | data[21]

    # Data 10 - Number of particles with diameter > 2.5um
    particles_25um = (data[22] << 8) | data[23]

    # Data 11 - Number of particles with diameter > 5.0um
    particles_50um = (data[24] << 8) | data[25]

    # Data 12 - Number of particles with diameter > 10um
    particles_100um = (data[26] << 8) | data[27]

    # Data 13 - Reserved
    reserved = (data[28] << 8) | data[29]

    # Checksum (2 bytes)
    checksum = (data[30] << 8) | data[31]

    # Calculate checksum to verify data integrity
    calculated_checksum = sum(data[:-2]) & 0xFFFF
    if calculated_checksum != checksum:
        raise ValueError("Checksum mismatch")

    # Return the parsed data as a dictionary
    return {
        "pm1_0_cf1": pm1_0_cf1,
        "pm2_5_cf1": pm2_5_cf1,
        "pm10_cf1": pm10_cf1,
        "pm1_0_atm": pm1_0_atm,
        "pm2_5_atm": pm2_5_atm,
        "pm10_atm": pm10_atm,
        "particles_03um": particles_03um,
        "particles_05um": particles_05um,
        "particles_10um": particles_10um,
        "particles_25um": particles_25um,
        "particles_50um": particles_50um,
        "particles_100um": particles_100um,
        "reserved": reserved,
        "checksum": checksum
    }


def get_pms7003_data(logging=LOGGING):
    
    if not uart_pms.any():
        return None
    
    data = uart_pms.read(32)
    try:
        parsed = parse_pm_sensor_data(data)
        print(parsed)
        return parsed
    except ValueError as e:
        print("Pms7003 runtime error: bad data")
        
    # TODO: check if I need to set it back to active mode in case of disconnection.
    
    
# ------- MAIN LOOP ----------

last_tick_time = time.time()
while True:
    if get_ze07_data() or get_pms7003_data() or get_dht20_data():
        pass
    else:
        if time.time() - last_tick_time >= 1:
            last_tick_time = time.time()
            print("Tick (per second)")
            
        led.toggle()
        time.sleep(0.25)
        led.toggle()
    # get_ze07_data()
    # get_dht20_data()
    # get_pms7003_data()



