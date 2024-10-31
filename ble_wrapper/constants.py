import bluetooth

# org.bluetooth.service.environmental_sensing
ENV_SENSE_UUID = bluetooth.UUID(0x181A)
# org.bluetooth.characteristic.temperature
ENV_SENSE_TEMP_UUID = bluetooth.UUID(0x2A6E)
# org.bluetooth.characteristic.gap.appearance.xml
ADV_APPEARANCE_GENERIC_THERMOMETER = const(768)

# bioinfo-characteristics UUID
BIO_INFO_CHARACTERISTICS_UUID = bluetooth.UUID("9fda7cce-48d4-4b1a-9026-6d46eec4e63a")
# request-characteristics UUID
REQUEST_CHARACTERISTICS_UUID = bluetooth.UUID("4f2d7b8e-23b9-4bc7-905f-a8e3d7841f6a")
# response-characteristics UUID
RESPONSE_CHARACTERISTICS_UUID = bluetooth.UUID("93e89c7d-65e3-41e6-b59f-1f3a6478de45")
# machine-time-characteristics UUID
MACHINE_TIME_CHARACTERISTICS_UUID = bluetooth.UUID("4fd3a9d8-5e82-4c1e-a2d3-9bc23f3a8341")

# expected handshake message from client
HANDSHAKE_MSG = "hello"
HANDSHAKE_TIMEOUT_MS = 1000

# How frequently to send advertising beacons.
ADV_INTERVAL_MS = 250_000