# Spirit Rover On-Board Firmware (Arduino)

Firmware for the Spirit Rover's on-board microcontroller. It talks to the
Raspberry Pi over an SPI slave link and to the PIC32 power/sensor coprocessor
over I2C.

## Target hardware

- **MCU:** ATmega328P @ **8 MHz**, 3.3 V (Arduino Pro Mini class)
- **SPI:** hardware SPI in **slave** mode (the Raspberry Pi is master)
- **I2C:** master to the on-board PIC32 (`PIC_I2C_ADDRESS 0x32`)
- **Timer1:** shared by motor PWM, the 38 kHz IR carrier, and IR input capture

The 8 MHz core clock matters: the timing math in `Hardware.ino` assumes it.

## Building with PlatformIO

This project is configured for [PlatformIO](https://platformio.org/). The
existing multi-file `.ino` sketch is built in place (`src_dir = .` in
`platformio.ini`), so the Arduino IDE tab layout still works unchanged.

```bash
pio run                 # compile
pio run -t upload       # compile + flash (configure upload_protocol first)
pio check               # static analysis
```

### Required vendored library

The firmware uses a custom I2C library, `RingoWire` (a trimmed-down `Wire.h`):

```cpp
#include <RingoWire.h>
```

It is **not** bundled here. Drop its source into:

```
lib/RingoWire/RingoWire.h
lib/RingoWire/RingoWire.cpp
```

PlatformIO's Library Dependency Finder will then pick it up automatically. The
`Adafruit NeoPixel` dependency is pinned in `platformio.ini` and fetched
automatically.

### Arduino IDE

You can still open `Spirit_BaseSketch_PiControl_Rev01.ino` in the Arduino IDE.
Select an **8 MHz / 3.3 V ATmega328P** board and install `Adafruit NeoPixel`
plus the `RingoWire` library into your Arduino `libraries/` folder.

## Source layout

All `.ino` files are concatenated into one translation unit by the build, so
function order across files does not matter. Shared functions and globals are
declared in the `.h` headers, which keeps the modules below independent.

| File | Responsibility |
| --- | --- |
| `Spirit_BaseSketch_PiControl_Rev01.ino` | `setup()` / `loop()` entry point |
| `Comms.ino` | I2C/SPI to the Raspberry Pi and PIC; chirp output |
| `Navigation.ino` | Heading/odometry navigation handler |
| `Hardware.ino` | Sensors, servos, motors, timer, movement, shared globals |
| `Pixels.ino` | NeoPixel / eye / wing control + the `pixels` object |
| `Infrared.ino` | IR transmit/receive, IR ISR, remote table, Timer1 carrier |
| `Sound.ino` | Short chirp/eye animations and `playSweep()` |

`Pixels.ino`, `Infrared.ino`, and `Sound.ino` were split out of the original
monolithic `Hardware.ino` with no behavior change.

## Concurrency / FreeRTOS note

An RTOS is **not** recommended on the ATmega328P here: the workload is
interrupt-driven (the hard-real-time SPI-slave ISR must reload `SPDR` before the
master's next clock edge), timing relies on interrupts-off NeoPixel updates and
blocking `delayMicroseconds()`, Timer1 is already triple-booked, and 2 KB SRAM
leaves little room for task stacks. The responsiveness wins are non-blocking
state machines (replacing `delay()` in sound/servo routines), not preemption.
FreeRTOS only makes sense if the board is changed to an ESP32 / RP2040 / SAMD21.
