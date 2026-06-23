#!/usr/bin/env python3
"""
Battery Voltage Reading Example

Demonstrates how to read the Spirit Rover's battery voltage.
"""

from time import sleep
import sys

# Import Spirit Rover library
from spirit_rover import Spirit


def main():
    """Read and display battery voltage."""
    # Initialize rover
    rover = Spirit()
    rover.i2c_process_delay(15)

    # Display battery voltage
    try:
        print("Battery Voltage:", rover.power_voltage())

        # Can just print the result by calling the function directly
        print(rover.power_voltage())

        # Can store result in a variable, then do something with it
        voltage = rover.power_voltage()
        print("Voltage: {} V".format(voltage))
    except Exception as e:
        print("Error reading voltage: {}".format(e))
        print("Check I2C connection to PIC32 board")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
