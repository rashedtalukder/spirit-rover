#!/usr/bin/env python3
"""
Rangefinder Reading Example

Demonstrates how to read the Spirit Rover's rangefinder
distance sensor.
"""

from time import sleep
import sys

# Import Spirit Rover library
from spirit_rover import Spirit


def main():
    """Read and display rangefinder values."""
    # Initialize rover
    rover = Spirit()
    rover.i2c_process_delay(15)

    # Display rangefinder reading
    try:
        print("Rangefinder:", rover.rangefinder())

        # Can just print the result by calling the function directly
        print(rover.rangefinder())

        # Can store result in a variable, then do something with it
        distance = rover.rangefinder()
        print("Distance: {} cm".format(distance))
    except Exception as e:
        print("Error reading rangefinder: {}".format(e))
        print("Check I2C connection to PIC32 board")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
