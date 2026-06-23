"""
Spirit Rover Hardware Library

A Python library for controlling the Spirit Rover robot via Raspberry Pi,
interfacing with PIC32 microcontroller for motors, servos, sensors, and LEDs.
"""

from .core import Spirit, Telemetry
from .pixels import PixelController
from .constants import (
    CHARGE_NOT_PRESENT, CHARGE_PRESENT_NOT_CHARGING,
    CHARGE_IN_PROGRESS, CHARGE_ERROR,
)

__version__ = '2.1.0'
__all__ = [
    'Spirit', 'Telemetry', 'PixelController',
    'CHARGE_NOT_PRESENT', 'CHARGE_PRESENT_NOT_CHARGING',
    'CHARGE_IN_PROGRESS', 'CHARGE_ERROR',
]
