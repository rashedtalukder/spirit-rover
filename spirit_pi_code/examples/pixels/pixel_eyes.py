#!/usr/bin/env python3
"""
Eye LED Control Example

Demonstrates how to control the eye LEDs with different
colors and brightness levels.
"""

from time import sleep
import sys

# Import Spirit Rover library
from spirit_rover import Spirit, PixelController


def main():
    """Control eye LED colors and brightness."""
    # Initialize rover and pixels
    rover = Spirit()
    rover.i2c_process_delay(15)
    pixels = PixelController()

    try:
        # Set eyes to given hue and brightness
        # hue: 0 to 360 (color wheel), brightness: 0 to 255
        print("Setting eyes to blue...")
        pixels.eyes(200, 100)
        sleep(0.5)

        print("Cycling through colors...")
        pixels.eyes(225, 100)
        sleep(0.5)

        pixels.eyes(250, 100)
        sleep(0.5)

        pixels.eyes(275, 100)
        sleep(0.5)

        pixels.eyes(300, 100)
        sleep(0.5)

        # Brightness of 0 turns eyes off
        print("Turning eyes off...")
        pixels.eyes(300, 0)

    except Exception as e:
        print("Error controlling pixels: {}".format(e))
        return 1
    finally:
        pixels.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
