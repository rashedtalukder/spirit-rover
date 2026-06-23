"""
Constants and configuration values for Spirit Rover hardware communication.
"""

# I2C Configuration
PIC_I2C_ADDRESS = 0x32
PIC_CYCLE_DURATION = 0.020

# SPI Configuration
SPI_SPEED = 75000  # SPI transmit speed in Hz
SPI_PAYLOAD_MAX_LENGTH = 9  # max usable SPI data bytes

# SPI Command Bytes (must match the #defines in the MCU's Comms.h)
SPI_CMD_MOTORS = 130      # [130, left, right] set motor speeds (128 = stop)
SPI_CMD_TELEMETRY = 131   # request a telemetry packet with no motion change
SPI_CMD_HEARTBEAT = 132   # keep the Pi-control link alive / clear failsafe
SPI_CMD_ERROR = 255       # sentinel the MCU uses to flag a bad/checksum-failed packet

# SPI Telemetry Response (sent back by the MCU in SPI_LoadTelemetry)
SPI_RESPONSE_TELEMETRY = 0x54  # first response byte identifying a telemetry packet
SPI_LINK_TIMEOUT_MS = 500      # MCU failsafe timeout; Pi should refresh faster than this

# The MCU loads telemetry for the *next* transaction while processing the
# current one, so a single transfer returns data that is one packet stale. A
# brief pause then a second transfer reads the freshly-loaded values.
SPI_REFRESH_DELAY = 0.005

# Motor command byte encoding (0-255, 128 = stop)
MOTOR_STOP_BYTE = 128
MOTOR_MAX = 255
MOTOR_MIN = -255

# Telemetry status-flag bit positions (statusFlags byte, response index 8)
TELEM_STATUS_CHARGE_MASK = 0x03  # bits 0-1 hold the charge status code
TELEM_STATUS_MOTOR_STOP = 2
TELEM_STATUS_SURFACE_SENSE = 3
TELEM_STATUS_RANGE_SENSE = 4
TELEM_STATUS_CURRENT_WARNING = 5
TELEM_STATUS_VOLTAGE_WARNING = 6
TELEM_STATUS_SHUTDOWN_NOW = 7

# Telemetry link-flag bit positions (linkFlags byte, response index 9)
TELEM_LINK_ACTIVE = 0
TELEM_LINK_FAILSAFE = 1
TELEM_LINK_PI_CONTROL = 2
TELEM_LINK_SERVOS_IN_MOTION = 3

# Charge status codes (bits 0-1 of the telemetry status byte)
CHARGE_NOT_PRESENT = 0           # no charger connected
CHARGE_PRESENT_NOT_CHARGING = 1  # charger connected, charge complete/idle
CHARGE_IN_PROGRESS = 2           # charger connected and charging
CHARGE_ERROR = 3                 # invalid charger line combination

# Servo Center Positions
SERVO_CENTER_TILT = 75  # actual value (0-127 degrees) sent to PIC
SERVO_CENTER_PAN = 90   # actual value (0-127 degrees) sent to PIC
SERVO_CENTER_GRIP = 10  # actual value (0-127 degrees) sent to PIC

# Default Pixel Server Configuration
PIXEL_SERVER_PORT = 20568

# Default Configuration Values
DEFAULT_I2C_PROCESS_DELAY = 15
DEFAULT_SERVO_SPEED = 3000
DEFAULT_AVERAGE_INTERVAL = 6
