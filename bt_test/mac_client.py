import asyncio
from bleak import BleakClient

# Replace with your BLE device's UUID
DEVICE_UUID = "ADF90923-3BEB-AC51-6922-ABD56FFD5315"

# UUID for Environmental Sensing (service) and Temperature characteristic
SERVICE_UUID = "0000181a-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "00002a6e-0000-1000-8000-00805f9b34fb"

# Callback function to handle notifications
def notification_handler(sender, data):
    # This function will be called whenever the sensor sends a notification
    print(f"Notification from {sender}: {data}")

    # Decode the value as little-endian signed 16-bit integer
    temperature_little_signed = int.from_bytes(data, byteorder="little", signed=True)
    
    # Convert to Celsius by dividing by 100
    temperature_celsius = temperature_little_signed / 100
    
    print(f"Temperature: {temperature_celsius:.2f}°C")

async def main():
    async with BleakClient(DEVICE_UUID) as client:
        print(f"Connected: {client.is_connected}")

        # Subscribe to notifications on the temperature characteristic
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)

        # Keep the script running to receive notifications
        try:
            while True:
                await asyncio.sleep(1)  # Keep the loop running
        except KeyboardInterrupt:
            print("Stopping notifications...")

        # Stop notifications when done
        await client.stop_notify(CHARACTERISTIC_UUID)

# Run the asyncio loop to execute the main function
asyncio.run(main())