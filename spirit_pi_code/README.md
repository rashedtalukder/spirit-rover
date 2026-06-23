# Spirit Rover Python Library

A Python 3 library for controlling the Spirit Rover robot hardware via Raspberry Pi. This library provides a clean interface to the PIC32 microcontroller for motors, servos, sensors, and RGB LED control.

## Features

- **Motor Control**: Direct control of left and right motors with speed range -255 to 255
- **Servo Control**: Pan/tilt/grip servo control with speed and position settings
- **Sensor Reading**: 
  - Surface light sensors (6 sensors: left, right, rear × inner/outer)
  - Ambient light sensors (3 sensors: left, right, rear)
  - Rangefinder distance measurement
  - Battery voltage and current monitoring
- **LED Pixel Control**: RGB LED control for eyes and wing animations
- **Status Monitoring**: Hardware interrupts, comparators, and system status

## Installation

### From Source

```bash
cd /path/to/spirit_pi_code
pip3 install -e .
```

To also install the on-board LED pixel server dependencies (run on the Pi):

```bash
pip3 install -e .[server]
```

### Requirements

- Python 3.9 or higher (tested through 3.13)
- Raspberry Pi with I2C and SPI enabled
- `smbus2` library for I2C communication
- `spidev` library for SPI communication

These are installed automatically by `pip3 install -e .`.

## Quick Start

```python
from spirit_rover import Spirit, PixelController
from time import sleep

# Initialize the rover (usable as a context manager so handles are released)
with Spirit() as rover:
    rover.i2c_process_delay(15)

    # Control motors
    rover.motors(120, 120)  # Forward at medium speed
    sleep(1)
    rover.motors(0, 0)  # Stop

    # Read sensors
    voltage = rover.power_voltage()
    print(f"Battery: {voltage}V")

    distance = rover.rangefinder()
    print(f"Distance: {distance}cm")

    # Control servos
    rover.servo_speed(3000)
    rover.servo_pan(30)  # Pan right
    rover.servo_tilt(-15)  # Tilt down

    # Control LEDs
    with PixelController() as pixels:
        pixels.eyes(200, 100)  # Blue eyes at medium brightness
        pixels.wings_autofade(250, 50, 7, 5, 1, 10)  # Animated wings
```

## Project Structure

```
spirit_pi_code/
├── spirit_rover/          # Main library package
│   ├── __init__.py       # Package exports
│   ├── core.py           # Core hardware interface
│   ├── pixels.py         # LED pixel control
│   └── constants.py      # Configuration constants
├── examples/             # Example scripts
│   ├── sensors/          # Sensor reading examples
│   ├── movement/         # Motor control examples
│   └── pixels/           # LED animation examples
├── pgpixelserver/        # On-board LED pixel server (runs on the Pi)
├── pyproject.toml        # Packaging & dependency configuration
└── README.md             # This file
```

## Examples

All examples are located in the `examples/` directory:

### Sensors
- `sensors/lightsense_surface.py` - Read surface light sensors
- `sensors/lightsense_ambient.py` - Read ambient light sensors
- `sensors/rangefinder.py` - Read distance sensor
- `sensors/volts.py` - Read battery voltage

### Movement
- `movement/motors_forward_backward.py` - Basic forward/backward motion
- `movement/motors_spinleft.py` - Spin in place

### Pixels
- `pixels/pixel_eyes.py` - Control eye LEDs
- `pixels/pixel_individual.py` - Control individual pixels
- `pixels/pixel_autofade_wings.py` - Animated wing effects

## API Documentation

### Spirit Class

#### Motor Control
- `motors(left, right)` - Control motor speeds (-255 to 255); returns the decoded `Telemetry`
- `forward(speed=120)` / `backward(speed=120)` - Drive straight
- `spin_left(speed=120)` / `spin_right(speed=120)` - Rotate in place
- `drive(speed, steering=0)` - Differential drive with a steering bias
- `stop()` - Stop both motors

#### Telemetry & Link (SPI)
- `request_telemetry(fresh=True)` - Read a decoded `Telemetry` packet
- `heartbeat(fresh=False)` - Keep the Pi-control link alive / clear a tripped failsafe
- `link_active()` / `failsafe_tripped()` / `pi_control_active()` - Link status booleans
- `telemetry_charge_status()` - Charge status code (`CHARGE_*` constants)
- `last_telemetry` - Most recent valid `Telemetry` snapshot

The MCU stops the motors automatically if it stops hearing from the Pi for
longer than 500 ms. Send motor commands or `heartbeat()` calls more often than
that to retain control while holding still.

A `Telemetry` namedtuple exposes: `valid`, `voltage`, `current`, `range_mm`,
`charge_status`, `motor_stop`, `surface_sense`, `range_sense`,
`current_warning`, `voltage_warning`, `shutdown_now`, `link_active`,
`failsafe_tripped`, `pi_control`, `servos_in_motion`.

#### Sound
- `chirp(frequency)` - Play a piezo tone in Hz (0 = off)
- `chirp_off()` - Silence the piezo

#### Servo Control
- `servo_speed(speed_dps)` - Set servo speed (1-3000 degrees/sec)
- `servo_pan(position)` - Pan servo position (-90 to 90 degrees)
- `servo_tilt(position)` - Tilt servo position (-90 to 90 degrees)
- `servo_grip(position)` - Grip servo position (-10 to 180 degrees)
- `servos_center()` - Return tilt/pan/grip servos to center
- `servos_in_motion()` - Dict of which servos are still moving

#### Sensor Reading
- `power_voltage()` - Battery voltage in volts
- `power_current()` - Battery current in amps
- `power_instant()` / `power_voltage_instant()` / `power_current_instant()` - Instant power reads
- `surf_left_0()`, `surf_left_1()` - Left surface sensors
- `surf_right_0()`, `surf_right_1()` - Right surface sensors
- `surf_rear_0()`, `surf_rear_1()` - Rear surface sensors
- `amb_left()`, `amb_right()`, `amb_rear()` - Ambient light sensors
- `rangefinder()` - Distance measurement
- `rangefinder_enable()` / `rangefinder_disable()` - Toggle automatic ranging
- `rangefinder_present()` - Detect whether a rangefinder is fitted

#### Device Info
- `button_pressed()` - User (BTN) button state
- `pic_software_version()` - PIC firmware version

### PixelController Class

- `eyes(hue, brightness)` - Set eye color and brightness
- `wings_autofade(...)` - Animated wing fade effect
- `hue_pixel(index, hue, brightness)` - Control individual pixel
- `pixels_off()` - Turn off all pixels

## Hardware Requirements

- Raspberry Pi (tested on Pi 3/4)
- Spirit Rover mainboard with PIC32 microcontroller
- I2C connection between Pi and PIC32
- SPI connection for motor control
- Pixel server daemon running for LED control

## Configuration

Default settings can be modified in `spirit_rover/constants.py`:

- I2C address and timing
- SPI speed and payload size
- Servo center positions
- Pixel server port

## Troubleshooting

**I2C Errors**: Ensure I2C is enabled on Raspberry Pi (`sudo raspi-config`)

**SPI Errors**: Ensure SPI is enabled and permissions are correct

**Pixel Control Not Working**: Ensure pixel server daemon is running

**Import Errors**: Ensure library is installed: `pip3 install -e .`

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please submit pull requests or issues on the project repository.
