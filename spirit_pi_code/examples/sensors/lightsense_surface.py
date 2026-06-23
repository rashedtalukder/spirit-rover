#!/usr/bin/env python3
"""
Surface Light Sensor Reading Example

Demonstrates how to read the Spirit Rover's bottom-facing
surface light sensors (left, right, and rear positions).
"""

from time import sleep
import sys

# Import Spirit Rover library
from spirit_rover import Spirit


def main():
    """Read and display surface sensor values."""
    # Initialize rover
    rover = Spirit()
    rover.i2c_process_delay(15)

    # Display bottom sensor values
    try:
        print("Surface Sensors:")
        print("Left Sensors...")
        print("  Outer:", rover.surf_left_0())
        print("  Inner:", rover.surf_left_1())
        print("Right Sensors...")
        print("  Outer:", rover.surf_right_0())
        print("  Inner:", rover.surf_right_1())
        print("Rear Sensors...")
        print("  Outer:", rover.surf_rear_0())
        print("  Inner:", rover.surf_rear_1())
    except Exception as e:
        print("Error reading surface sensors: {}".format(e))
        print("Check I2C connection to PIC32 board")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
