from machine import ADC, Pin
import time

# Initialize ADC on GPIO 28 (ADC2)
adc = ADC(Pin(28))

# Reference voltage for the ADC (3.3V on the Pico)
VREF = 3.3

# Voltage divider correction factor (1.51 based on your resistor values)
VOLTAGE_DIVIDER_RATIO = 1.51

def read_battery_voltage():
    # Read the raw ADC value (0-65535)
    raw_value = adc.read_u16()
    # Convert raw value to voltage
    adc_voltage = raw_value * VREF / 65535
    # Calculate actual battery voltage using the voltage divider ratio
    battery_voltage = adc_voltage * VOLTAGE_DIVIDER_RATIO
    return battery_voltage

while True:
    voltage = read_battery_voltage()
    print("Battery Voltage: {:.2f} V".format(voltage))
    time.sleep(1)