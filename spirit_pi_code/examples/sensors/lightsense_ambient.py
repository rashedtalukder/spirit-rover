#!/usr/bin/env python3
"""
Ambient Light Sensor Reading Example

Demonstrates how to read the Spirit Rover's ambient
light sensors (left, right, and rear positions).
"""

from time import sleep
import sys

# Import Spirit Rover library
from spirit_rover import Spirit


def main():
    """Read and display ambient sensor values."""
    # Initialize rover
    rover = Spirit()
    rover.i2c_process_delay(15)

    # Display ambient light sensor readings
    try:
        print("Ambient Sensors:")
        print("  Left:", rover.amb_left())
        print("  Right:", rover.amb_right())
        print("  Rear:", rover.amb_rear())
    except Exception as e:
        print("Error reading ambient sensors: {}".format(e))
        print("Check I2C connection to PIC32 board")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
