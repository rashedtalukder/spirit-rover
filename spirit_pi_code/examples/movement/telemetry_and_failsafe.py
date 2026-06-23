#!/usr/bin/env python3
"""
Telemetry, Heartbeat, and Failsafe Example

Demonstrates the SPI telemetry features exposed by the MCU:
- Reading a decoded telemetry packet (voltage, current, range, status flags).
- Using the high-level motion helpers (forward / spin / drive / stop).
- Keeping the Pi-control link alive with heartbeats so the MCU failsafe does
  not stop the rover while it is intentionally holding still.

The MCU automatically stops the motors if it stops hearing from the Pi for
longer than SPI_LINK_TIMEOUT_MS (500 ms). Sending motor commands or heartbeats
faster than that keeps the link alive.
"""

from time import sleep
import sys

from spirit_rover import Spirit, CHARGE_IN_PROGRESS


def print_telemetry(telem):
    """Pretty-print a Telemetry namedtuple."""
    if telem is None or not telem.valid:
        print("  (no valid telemetry)")
        return
    print("  voltage={:.2f} V  current={:.2f} A  range={} mm".format(
        telem.voltage, telem.current, telem.range_mm))
    print("  link_active={}  failsafe_tripped={}  pi_control={}".format(
        telem.link_active, telem.failsafe_tripped, telem.pi_control))
    print("  motor_stop={}  surface_sense={}  range_sense={}".format(
        telem.motor_stop, telem.surface_sense, telem.range_sense))
    if telem.charge_status == CHARGE_IN_PROGRESS:
        print("  battery is charging")


def main():
    """Read telemetry, drive briefly, then hold with heartbeats."""
    rover = Spirit()
    rover.i2c_process_delay(15)

    try:
        print("Firmware version:", rover.pic_software_version())

        print("Initial telemetry:")
        print_telemetry(rover.request_telemetry())

        # The motion helpers return the telemetry decoded from each transaction.
        print("Driving forward...")
        print_telemetry(rover.forward(120))
        sleep(0.5)

        print("Spinning left...")
        rover.spin_left(120)
        sleep(0.5)

        print("Curving with drive(speed, steering)...")
        rover.drive(120, steering=60)
        sleep(0.5)

        print("Stopping and holding the link with heartbeats...")
        rover.stop()
        for _ in range(10):
            telem = rover.heartbeat()
            if telem and telem.failsafe_tripped:
                print("  failsafe tripped - re-establishing control")
            sleep(0.2)  # well under the 500 ms MCU timeout

        print("Final telemetry:")
        print_telemetry(rover.request_telemetry())
    except Exception as e:
        print("Error: {}".format(e))
        rover.stop()
        return 1
    finally:
        rover.stop()
        rover.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
