#!/usr/bin/env python3
"""
Wing Auto-Fade Animation Example

Demonstrates automated wing LED fade animation with
different colors and speeds.
"""

from time import sleep
import sys

# Import Spirit Rover library
from spirit_rover import Spirit, PixelController


def main():
    """Start automated wing fade animations."""
    # Initialize rover and pixels
    rover = Spirit()
    rover.i2c_process_delay(15)
    pixels = PixelController()

    try:
        # Start automated wing fade
        # Parameters: hue, brightness, fall_off, over_under, fade_direction, speed

        print("Starting purple wing fade...")
        pixels.wings_autofade(250, 50, 7, 5, 1, 10)
        sleep(1.5)

        print("Changing to green wing fade...")
        pixels.wings_autofade(120, 20, 7, 5, 1, 20)
        sleep(1.5)

        print("Turning off all pixels...")
        pixels.pixels_off()

    except Exception as e:
        print("Error controlling pixels: {}".format(e))
        return 1
    finally:
        pixels.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
