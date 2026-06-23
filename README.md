# Plum Geek Spirit Rover

This repo contains the software and documentation for the **Spirit Rover**, the
Raspberry Pi + Arduino learning robot originally sold on
[Kickstarter](https://www.kickstarter.com/projects/plumgeek/spirit-rover-learn-raspberry-pi-and-arduino-the-fu).

The codebase has been modernized: the Raspberry Pi control code was ported from
Python 2.7 to Python 3 and repackaged as an installable library, and the
on-board Arduino firmware was reorganized to build with PlatformIO.

## Repository structure

```
.
├── spirit_pi_code/                  # Raspberry Pi control software (Python 3)
│   ├── spirit_rover/                # Installable library package
│   ├── examples/                    # Sensor, movement & pixel examples
│   ├── pgpixelserver/               # On-board LED pixel server (runs on the Pi)
│   ├── pyproject.toml / setup.py    # Packaging & dependencies
│   ├── README.md                    # Library documentation
│   └── MIGRATION.md                 # Python 2 → 3 migration notes
│
├── Spirit_BaseSketch_PiControl_Rev01/   # On-board firmware (Arduino / PlatformIO)
│   ├── *.ino / *.h                  # Multi-file Arduino sketch
│   ├── lib/RingoWire/               # Vendored I2C library header
│   ├── platformio.ini               # PlatformIO build configuration
│   └── README.md                    # Firmware documentation
│
├── spirit-rover-code-quick-reference.md   # Command / API quick reference
└── README.md                        # This file
```

## Raspberry Pi software (`spirit_pi_code/`)

A Python 3 library that runs on the Raspberry Pi and drives the rover's motors,
servos, sensors, and RGB LEDs through the on-board microcontroller.

```bash
cd spirit_pi_code
pip3 install -e .
```

```python
from spirit_rover import Spirit, PixelController

with Spirit() as rover:
    rover.forward(120)          # drive forward
    print(rover.rangefinder())  # read distance sensor
```

See [spirit_pi_code/README.md](spirit_pi_code/README.md) for the full API,
examples, and requirements, and
[spirit_pi_code/MIGRATION.md](spirit_pi_code/MIGRATION.md) for details of the
Python 2 → 3 port.

## On-board firmware (`Spirit_BaseSketch_PiControl_Rev01/`)

Firmware for the rover's ATmega328P microcontroller, which acts as an SPI slave
to the Raspberry Pi and an I2C master to the PIC32 power/sensor coprocessor.
It builds with [PlatformIO](https://platformio.org/) while keeping the original
multi-file Arduino sketch layout.

```bash
cd Spirit_BaseSketch_PiControl_Rev01
pio run              # compile
pio run -t upload    # compile + flash
```

See [Spirit_BaseSketch_PiControl_Rev01/README.md](Spirit_BaseSketch_PiControl_Rev01/README.md)
for target hardware details and the vendored `RingoWire` library requirement.

## Documentation

- [spirit-rover-code-quick-reference.md](spirit-rover-code-quick-reference.md) — command and API quick reference
- `spirit-rover-setup-build.pdf` — original assembly and setup guide
