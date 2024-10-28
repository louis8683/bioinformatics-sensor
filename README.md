# Bioinformatics Sensor Project

## Introduction
This repository contains the code for the sensor of the bioinformatics project for high school students.

## Sensors
### PM2.5 sensor: PMS7003
### CO sensor: ZE07-CO
### Temperature and humidity sensor: DHT20

## Update Notes
### 9/10/2024: Testing the first version of the PCB design
* Created tests for each sensor module with error handling in various cases of connecting and disconnecting.
* Created an integration test.

### 9/25/2024: Using VS Code for development, experimented with BLE
* Use the MicroPico extension to enable using VS Code for RPi Pico development. 
* The "aioble" library (higher-level) from MicroPython can be used alongside the "bluetooth" library (lower-level)
* To test the connection, Python's "bleak" library can enable BLE connection from the computer
* Important BLE advertising mode facts:
    * The device ID is used for connection
    * The device name can be used for discovery of the device
    * Three important values for connection: Device UUID, Service UUID, and Characteristic UUID
    * 16-bit UUID is used for 
    * The standard Bluetooth SIG-assigned service and characteristic UUIDs are in "0000xxxx-0000-1000-8000-00805f9b34fb" format.
        * Example 1: 0000181a-0000-1000-8000-00805f9b34fb is the Environmental Sensing service
        * Example 2: 00002a6e-0000-1000-8000-00805f9b34fb is the Temperature characteristic.
    * Custom service and characteristic UUIDs don't have to be in this format
    * GATT (Generic Attribute Profile) is used for the communication process, including "read," "write," and "notify."
    * Characteristics are organized within Services.
    * **Only one device can connect to a BLE advertising device at a time.** This can lead to problems.
        * Potential solutions: Unique device names, QR codes for MAC address, Non-connectable advertising, Time-slicing
* Notable characteristics that is related to this project:
    * Environmental Sensing Service (UUID: 0x181A)
    * Temperature Characteristic (UUID: 0x2A6E)
    * Humidity Characteristic (UUID: 0x2A6F)
* The CO and PM2.5 will need to be custom characteristics. We can assign our own values.

### 10/28/2024: Overhaul
* Completely overhaul the project to align with the State Machine pattern.