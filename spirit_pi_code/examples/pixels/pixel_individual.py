#!/usr/bin/env python3
"""
Individual Pixel Control Example

Demonstrates how to control individual pixels with specific
colors and brightness levels.
"""

from time import sleep
import sys

# Import Spirit Rover library
from spirit_rover import Spirit, PixelController


def main():
    """Control individual pixels."""
    # Initialize rover and pixels
    rover = Spirit()
    rover.i2c_process_delay(15)
    pixels = PixelController()

    try:
        # Use this to set any pixel to any hue and brightness
        # Pass: pixel number (beginning with 0), pixel hue, and pixel brightness

        print("Turning on pixels 14 and 24...")
        pixels.hue_pixel(14, 150, 20)  # Turn on some pixels
        sleep(0.1)
        pixels.hue_pixel(24, 150, 20)
        sleep(1)

        print("Turning off pixels...")
        # Set brightness to 0 to turn them off
        pixels.hue_pixel(14, 150, 0)
        sleep(0.1)
        pixels.hue_pixel(24, 150, 0)

    except Exception as e:
        print("Error controlling pixels: {}".format(e))
        return 1
    finally:
        pixels.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
