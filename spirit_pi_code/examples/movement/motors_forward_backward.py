#!/usr/bin/env python3
"""
Motor Forward/Backward Example

Demonstrates basic motor control - moving forward and backward.
"""

from time import sleep
import sys

# Import Spirit Rover library
from spirit_rover import Spirit


def main():
    """Run motors forward then backward."""
    # Initialize rover
    rover = Spirit()
    rover.i2c_process_delay(15)

    try:
        # Run motors forward
        print("Moving forward...")
        rover.motors(120, 120)  # Can be from -255 to 255
        sleep(1)  # Delay 1 second

        # Run motors backward
        print("Moving backward...")
        rover.motors(-120, -120)
        sleep(1)

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
