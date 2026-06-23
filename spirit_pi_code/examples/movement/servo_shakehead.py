#!/usr/bin/env python3
"""
Servo Shake Head Example

Demonstrates servo control by making the rover shake its head
(pan servo side to side).
"""

from time import sleep
import sys

# Import Spirit Rover library
from spirit_rover import Spirit


def main():
    """Make rover shake head using pan servo."""
    # Initialize rover
    rover = Spirit()
    rover.i2c_process_delay(15)

    try:
        # Servo commands to make robot shake head
        print("Setting servo speed...")
        # Set servo speed in degrees per second (3000 is max)
        rover.servo_speed(3000)

        print("Shaking head...")
        # 0 is center, plus or minus 90 from there to rotate head
        rover.servo_pan(30)
        sleep(0.25)  # Short delay

        rover.servo_pan(-30)
        sleep(0.25)

        # 0 sets servo back to center
        print("Centering head...")
        rover.servo_pan(0)

    except Exception as e:
        print("Error controlling servo: {}".format(e))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
