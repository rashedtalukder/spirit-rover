#!/usr/bin/env python3
"""
Motor Spin Left Example

Demonstrates spinning the rover in place by running motors
in opposite directions.
"""

from time import sleep
import sys

# Import Spirit Rover library
from spirit_rover import Spirit


def main():
    """Spin rover left in place."""
    # Initialize rover
    rover = Spirit()
    rover.i2c_process_delay(15)

    try:
        # Spin left (left motor backward, right motor forward)
        print("Spinning left...")
        rover.motors(-100, 100)  # Left negative, right positive
        sleep(2)  # Spin for 2 seconds

        # Stop motors
        print("Stopping...")
        rover.motors(0, 0)
    except Exception as e:
        print("Error controlling motors: {}".format(e))
        # Ensure motors are stopped on error
        rover.motors(0, 0)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
