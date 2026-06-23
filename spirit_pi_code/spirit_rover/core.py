"""
Spirit Rover Core Hardware Interface

Provides communication with the PIC32 microcontroller via I2C and SPI
for controlling motors, servos, sensors, and reading hardware status.
"""

import logging
from collections import namedtuple

# Use the monotonic clock for every elapsed-time / cache-freshness check so the
# timing is immune to system clock adjustments (e.g. NTP stepping the wall clock
# after the Pi boots and gets network time). ``sleep`` is unaffected by this.
from time import sleep, monotonic as time

from smbus2 import SMBus
import spidev

from .constants import (
    PIC_I2C_ADDRESS, PIC_CYCLE_DURATION, SPI_SPEED, SPI_PAYLOAD_MAX_LENGTH,
    SERVO_CENTER_TILT, SERVO_CENTER_PAN, SERVO_CENTER_GRIP,
    DEFAULT_SERVO_SPEED, DEFAULT_AVERAGE_INTERVAL,
    SPI_CMD_MOTORS, SPI_CMD_TELEMETRY, SPI_CMD_HEARTBEAT,
    SPI_RESPONSE_TELEMETRY, SPI_REFRESH_DELAY, MOTOR_STOP_BYTE,
    TELEM_STATUS_CHARGE_MASK, TELEM_STATUS_MOTOR_STOP, TELEM_STATUS_SURFACE_SENSE,
    TELEM_STATUS_RANGE_SENSE, TELEM_STATUS_CURRENT_WARNING,
    TELEM_STATUS_VOLTAGE_WARNING, TELEM_STATUS_SHUTDOWN_NOW,
    TELEM_LINK_ACTIVE, TELEM_LINK_FAILSAFE, TELEM_LINK_PI_CONTROL,
    TELEM_LINK_SERVOS_IN_MOTION,
)

logger = logging.getLogger(__name__)


# Structured snapshot of the telemetry packet returned by the MCU over SPI.
# ``valid`` is False when the response id or checksum did not match, in which
# case the remaining fields should not be trusted.
Telemetry = namedtuple("Telemetry", [
    "valid",
    "voltage",            # battery voltage in volts
    "current",            # battery current in amps
    "range_mm",           # last rangefinder distance in millimeters
    "charge_status",      # one of the CHARGE_* codes
    "motor_stop",         # PIC asserted a motor-stop (edge/obstacle)
    "surface_sense",      # surface sensor threshold tripped
    "range_sense",        # rangefinder threshold tripped
    "current_warning",    # over-current warning asserted
    "voltage_warning",    # low-voltage warning asserted
    "shutdown_now",       # MCU is about to power the rover down
    "link_active",        # MCU sees a live Pi SPI link
    "failsafe_tripped",   # motors were stopped by the link-timeout failsafe
    "pi_control",          # MCU is in Pi-control (transparent) mode
    "servos_in_motion",   # one or more servos are still moving
])


class Spirit:
    """
    Main interface class for Spirit Rover hardware control.

    Handles all communication with the PIC32 microcontroller for:
    - Motor control
    - Servo control (pan/tilt/grip)
    - Sensor readings (surface, ambient, rangefinder, power)
    - Status monitoring and interrupts

    The instance can be used as a context manager so that the underlying I2C
    and SPI handles are always released::

        with Spirit() as rover:
            rover.motors(120, 120)
    """

    def __init__(self, i2c_bus=1, spi_bus=0, spi_device=0):
        """
        Initialize I2C and SPI communication interfaces.

        Args:
            i2c_bus: I2C bus number (default 1 on modern Raspberry Pi boards).
            spi_bus: SPI bus number (default 0).
            spi_device: SPI chip-select / device number (default 0).
        """
        self.i2c = SMBus(i2c_bus)
        self.name = "Spirit"
        self.i2c_read_extra_pause = 0
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.max_speed_hz = SPI_SPEED

        # Initialize cached values and timestamps
        self._init_status_registers()
        self._init_sensor_values()
        self._init_servo_positions()

        # Most recent valid telemetry packet decoded from an SPI response.
        self.last_telemetry = None

    def close(self):
        """Release the I2C and SPI hardware handles.

        Safe to call multiple times.
        """
        spi = getattr(self, "spi", None)
        if spi is not None:
            try:
                spi.close()
            except Exception:  # pragma: no cover - defensive cleanup
                logger.debug("Error closing SPI handle", exc_info=True)
            self.spi = None

        i2c = getattr(self, "i2c", None)
        if i2c is not None:
            try:
                i2c.close()
            except Exception:  # pragma: no cover - defensive cleanup
                logger.debug("Error closing I2C handle", exc_info=True)
            self.i2c = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False


    def _init_status_registers(self):
        """Initialize status register cached values."""
        self._time_status_reg = time() - 0.03
        self.statusBank0 = 0
        self.statusBank1 = 0
        self.currentWarningInt = 0
        self.voltageWarningInt = 0
        self.shutdownNowInt = 0
        self.motorStopInt = 0
        self.surfaceSenseInt = 0
        self.powerSenseInt = 0
        self.rangeSenseInt = 0
        self.ambSenseInt = 0
        self.UARTRxThreshInt = 0
        self.UARTRxNullInt = 0
        self.UARTTxInProg = 0

        self._time_inputs = time() - 0.03
        self.picInputs = 0
        self.button = 0
        self.buttonPower = 0
        self.accelInt1 = 0
        self.gyroInt1 = 0
        self.gyroInt2 = 0
        self.chgPresent = 0
        self.chgInProg = 0
        self.xbeeAssoc = 0

        self._time_comparators = time() - 0.03
        self.thresholdComparators1 = 0
        self.thresholdComparators2 = 0
        self.currentComparator = 0
        self.voltageComparator = 0
        self.leftOuterComparator = 0
        self.leftInnerComparator = 0
        self.rightOuterComparator = 0
        self.rightInnerComparator = 0
        self.rearOuterComparator = 0
        self.rearInnerComparator = 0
        self.rangefinderComparator = 0
        self.ambLeftComparator = 0
        self.ambRightComparator = 0
        self.ambRearComparator = 0
        self.wallPowerComparator = 0

    def _init_sensor_values(self):
        """Initialize sensor cached values."""
        self._time_power = time() - 0.03
        self.powerVoltage = 0
        self.powerCurrent = 0

        self._time_power_average = time() - 0.03
        self.powerVoltageAverage = 0
        self.powerCurrentAverage = 0

        self._time_surface = time() - 0.03
        self.surfLeft0 = 0
        self.surfLeft1 = 0
        self.surfRight0 = 0
        self.surfRight1 = 0
        self.surfRear0 = 0
        self.surfRear1 = 0

        self._time_surface_average = time() - 0.03
        self.surfLeft0Average = 0
        self.surfLeft1Average = 0
        self.surfRight0Average = 0
        self.surfRight1Average = 0
        self.surfRear0Average = 0
        self.surfRear1Average = 0

        self._time_ambient = time() - 0.03
        self.ambLeft = 0
        self.ambRight = 0
        self.ambRear = 0

        self._time_ambient_average = time() - 0.03
        self.ambLeftAverage = 0
        self.ambRightAverage = 0
        self.ambRearAverage = 0

        self._time_rangefinder = time() - 0.03
        self.rangeAutoInterval = 0
        self.rangefinderDistance = 0
        self.rangefinderGoodCounts = 0

        self.avgIntervalSurface = DEFAULT_AVERAGE_INTERVAL
        self.avgIntervalAmbient = DEFAULT_AVERAGE_INTERVAL
        self.avgIntervalPower = DEFAULT_AVERAGE_INTERVAL

    def _init_servo_positions(self):
        """Initialize servo position values."""
        self.servoSpeed = DEFAULT_SERVO_SPEED
        self.servoTilt = 75
        self.servoPan = 90
        self.servoGrip = 10
        self.servoTrim_Tilt = 0
        self.servoTrim_Pan = 0
        self.servoTrim_Grip = 0

    # Motor Control Methods
    def motors(self, left, right):
        """
        Control left and right motors.

        Sends the motor command over SPI and decodes the telemetry packet the
        MCU returns in the same transaction.

        Args:
            left: Left motor speed (-255 to 255)
            right: Right motor speed (-255 to 255)

        Returns:
            The decoded :class:`Telemetry` for the transaction, or ``None`` if
            the response could not be decoded.
        """
        left = self.clamp(left, -255, 255)
        right = self.clamp(right, -255, 255)
        left = int(left // 2) + MOTOR_STOP_BYTE
        right = int(right // 2) + MOTOR_STOP_BYTE
        resp = self.spi_transfer([SPI_CMD_MOTORS, left, right])
        return self._parse_telemetry(resp)

    # Convenience motion helpers built on top of motors()
    def stop(self):
        """Stop both motors immediately."""
        return self.motors(0, 0)

    def forward(self, speed=120):
        """Drive straight forward at ``speed`` (0 to 255)."""
        speed = self.clamp(speed, 0, 255)
        return self.motors(speed, speed)

    def backward(self, speed=120):
        """Drive straight backward at ``speed`` (0 to 255)."""
        speed = self.clamp(speed, 0, 255)
        return self.motors(-speed, -speed)

    def spin_left(self, speed=120):
        """Rotate counter-clockwise in place at ``speed`` (0 to 255)."""
        speed = self.clamp(speed, 0, 255)
        return self.motors(-speed, speed)

    def spin_right(self, speed=120):
        """Rotate clockwise in place at ``speed`` (0 to 255)."""
        speed = self.clamp(speed, 0, 255)
        return self.motors(speed, -speed)

    def drive(self, speed, steering=0):
        """Drive with a forward ``speed`` and differential ``steering``.

        Args:
            speed: Base forward (positive) / reverse (negative) speed (-255..255).
            steering: Turn bias added to the left wheel and subtracted from the
                right. Positive steers right, negative steers left.

        Returns:
            The decoded :class:`Telemetry`, or ``None``.
        """
        speed = self.clamp(speed, -255, 255)
        steering = self.clamp(steering, -255, 255)
        left = self.clamp(speed + steering, -255, 255)
        right = self.clamp(speed - steering, -255, 255)
        return self.motors(left, right)

    # SPI Telemetry / Link Methods
    def request_telemetry(self, fresh=True):
        """Request a telemetry packet from the MCU without changing motion.

        Args:
            fresh: When True (default) two transfers are issued so the returned
                packet reflects the current rover state rather than the value
                the MCU staged during the previous transaction.

        Returns:
            The decoded :class:`Telemetry`, or ``None`` if it could not be
            decoded.
        """
        resp = self.spi_transfer([SPI_CMD_TELEMETRY])
        if fresh:
            sleep(SPI_REFRESH_DELAY)
            resp = self.spi_transfer([SPI_CMD_TELEMETRY])
        return self._parse_telemetry(resp)

    def heartbeat(self, fresh=False):
        """Keep the Pi-control link alive and clear a tripped failsafe.

        Call this periodically (faster than ``SPI_LINK_TIMEOUT_MS``) when the Pi
        is holding the rover stationary but still wants to retain control.

        Returns:
            The decoded :class:`Telemetry`, or ``None``.
        """
        resp = self.spi_transfer([SPI_CMD_HEARTBEAT])
        if fresh:
            sleep(SPI_REFRESH_DELAY)
            resp = self.spi_transfer([SPI_CMD_HEARTBEAT])
        return self._parse_telemetry(resp)

    def link_active(self):
        """Return True if the MCU currently sees a live Pi SPI link."""
        telem = self.request_telemetry()
        return bool(telem and telem.link_active)

    def failsafe_tripped(self):
        """Return True if the link-timeout failsafe has stopped the motors."""
        telem = self.request_telemetry()
        return bool(telem and telem.failsafe_tripped)

    def pi_control_active(self):
        """Return True if the MCU is in Pi-control (transparent) mode."""
        telem = self.request_telemetry()
        return bool(telem and telem.pi_control)

    def telemetry_charge_status(self):
        """Return the charge status code from a fresh telemetry packet.

        See the ``CHARGE_*`` constants for the meaning of each value, or
        ``None`` if telemetry could not be read.
        """
        telem = self.request_telemetry()
        return telem.charge_status if telem else None

    def _parse_telemetry(self, resp):
        """Decode an SPI response list into a :class:`Telemetry` namedtuple.

        Validates the response id and XOR checksum. The last valid packet is
        cached on ``self.last_telemetry``. Returns ``None`` for malformed
        responses (e.g. a failed transfer).
        """
        if not isinstance(resp, (list, tuple)) or len(resp) < 11:
            return None

        checksum = 0
        for byte in resp[1:10]:
            checksum ^= byte
        valid = (resp[1] == SPI_RESPONSE_TELEMETRY) and (checksum == resp[10])

        status = resp[8]
        link = resp[9]
        telem = Telemetry(
            valid=valid,
            voltage=((resp[2] << 8) | resp[3]) / 1000.0,
            current=((resp[4] << 8) | resp[5]) / 1000.0,
            range_mm=(resp[6] << 8) | resp[7],
            charge_status=status & TELEM_STATUS_CHARGE_MASK,
            motor_stop=bool((status >> TELEM_STATUS_MOTOR_STOP) & 1),
            surface_sense=bool((status >> TELEM_STATUS_SURFACE_SENSE) & 1),
            range_sense=bool((status >> TELEM_STATUS_RANGE_SENSE) & 1),
            current_warning=bool((status >> TELEM_STATUS_CURRENT_WARNING) & 1),
            voltage_warning=bool((status >> TELEM_STATUS_VOLTAGE_WARNING) & 1),
            shutdown_now=bool((status >> TELEM_STATUS_SHUTDOWN_NOW) & 1),
            link_active=bool((link >> TELEM_LINK_ACTIVE) & 1),
            failsafe_tripped=bool((link >> TELEM_LINK_FAILSAFE) & 1),
            pi_control=bool((link >> TELEM_LINK_PI_CONTROL) & 1),
            servos_in_motion=bool((link >> TELEM_LINK_SERVOS_IN_MOTION) & 1),
        )
        if valid:
            self.last_telemetry = telem
        else:
            logger.debug(
                "Discarding telemetry with bad id/checksum: %s", list(resp))
        return telem

    # Status Register Methods
    def button_pressed(self):
        """Get the BTN (user) button status (1 = pressed)."""
        if ((time()-self._time_inputs) < PIC_CYCLE_DURATION):
            return self.button
        self.PIC_ReadInputs()
        return self.button

    def current_warning_int(self):
        """Get current warning interrupt status."""
        if ((time()-self._time_status_reg) < PIC_CYCLE_DURATION):
            return self.currentWarningInt
        self.PIC_ReadStatus()
        return self.currentWarningInt

    def voltage_warning_int(self):
        """Get voltage warning interrupt status."""
        if ((time()-self._time_status_reg) < PIC_CYCLE_DURATION):
            return self.voltageWarningInt
        self.PIC_ReadStatus()
        return self.voltageWarningInt

    def shutdown_now_int(self):
        """Get shutdown now interrupt status."""
        if ((time()-self._time_status_reg) < PIC_CYCLE_DURATION):
            return self.shutdownNowInt
        self.PIC_ReadStatus()
        return self.shutdownNowInt

    def motor_stop_int(self):
        """Get motor stop interrupt status."""
        if ((time()-self._time_status_reg) < PIC_CYCLE_DURATION):
            return self.motorStopInt
        self.PIC_ReadStatus()
        return self.motorStopInt

    def surface_sense_int(self):
        """Get surface sense interrupt status."""
        if ((time()-self._time_status_reg) < PIC_CYCLE_DURATION):
            return self.surfaceSenseInt
        self.PIC_ReadStatus()
        return self.surfaceSenseInt

    def power_sense_int(self):
        """Get power sense interrupt status."""
        if ((time()-self._time_status_reg) < PIC_CYCLE_DURATION):
            return self.powerSenseInt
        self.PIC_ReadStatus()
        return self.powerSenseInt

    def range_sense_int(self):
        """Get range sense interrupt status."""
        if ((time()-self._time_status_reg) < PIC_CYCLE_DURATION):
            return self.rangeSenseInt
        self.PIC_ReadStatus()
        return self.rangeSenseInt

    def amb_sense_int(self):
        """Get ambient sense interrupt status."""
        if ((time()-self._time_status_reg) < PIC_CYCLE_DURATION):
            return self.ambSenseInt
        self.PIC_ReadStatus()
        return self.ambSenseInt

    def uart_rx_thresh_int(self):
        """Get UART RX threshold interrupt status."""
        if ((time()-self._time_status_reg) < PIC_CYCLE_DURATION):
            return self.UARTRxThreshInt
        self.PIC_ReadStatus()
        return self.UARTRxThreshInt

    def uart_rx_null_int(self):
        """Get UART RX null interrupt status."""
        if ((time()-self._time_status_reg) < PIC_CYCLE_DURATION):
            return self.UARTRxNullInt
        self.PIC_ReadStatus()
        return self.UARTRxNullInt

    def uart_tx_in_prog(self):
        """Get UART TX in progress status."""
        if ((time()-self._time_status_reg) < PIC_CYCLE_DURATION):
            return self.UARTTxInProg
        self.PIC_ReadStatus()
        return self.UARTTxInProg

    def PIC_ReadStatus(self):
        """Read status registers from PIC."""
        if ((time()-self._time_status_reg) < PIC_CYCLE_DURATION):
            return (self.statusBank0, self.statusBank1)

        register = 1
        length = 3
        pause = 0.0016
        sleep(pause)
        i2c_reply = self.i2cRead(register, length, pause)
        if isinstance(i2c_reply, int):
            return i2c_reply

        self._time_status_reg = time()
        self.statusBank0 = i2c_reply[1]
        self.statusBank1 = i2c_reply[2]
        self.currentWarningInt = (self.statusBank0 >> 0) & 1
        self.voltageWarningInt = (self.statusBank0 >> 1) & 1
        self.shutdownNowInt = (self.statusBank0 >> 2) & 1
        self.motorStopInt = (self.statusBank0 >> 3) & 1
        self.surfaceSenseInt = (self.statusBank0 >> 4) & 1
        self.powerSenseInt = (self.statusBank0 >> 5) & 1
        self.rangeSenseInt = (self.statusBank0 >> 6) & 1
        self.ambSenseInt = (self.statusBank0 >> 7) & 1
        self.UARTRxThreshInt = (self.statusBank1 >> 0) & 1
        self.UARTRxNullInt = (self.statusBank1 >> 1) & 1
        self.UARTTxInProg = (self.statusBank1 >> 2) & 1
        return (self.statusBank0, self.statusBank1)

    # Input Status Methods
    def button_power(self):
        """Get power button status."""
        if ((time()-self._time_inputs) < PIC_CYCLE_DURATION):
            return self.buttonPower
        self.PIC_ReadInputs()
        return self.buttonPower

    def accel_int1(self):
        """Get accelerometer interrupt 1 status."""
        if ((time()-self._time_inputs) < PIC_CYCLE_DURATION):
            return self.accelInt1
        self.PIC_ReadInputs()
        return self.accelInt1

    def gyro_int1(self):
        """Get gyro interrupt 1 status."""
        if ((time()-self._time_inputs) < PIC_CYCLE_DURATION):
            return self.gyroInt1
        self.PIC_ReadInputs()
        return self.gyroInt1

    def gyro_int2(self):
        """Get gyro interrupt 2 status."""
        if ((time()-self._time_inputs) < PIC_CYCLE_DURATION):
            return self.gyroInt2
        self.PIC_ReadInputs()
        return self.gyroInt2

    def chg_present(self):
        """Get charger present status."""
        if ((time()-self._time_inputs) < PIC_CYCLE_DURATION):
            return self.chgPresent
        self.PIC_ReadInputs()
        return self.chgPresent

    def chg_in_prog(self):
        """Get charging in progress status."""
        if ((time()-self._time_inputs) < PIC_CYCLE_DURATION):
            return self.chgInProg
        self.PIC_ReadInputs()
        return self.chgInProg

    def xbee_assoc(self):
        """Get XBee association status."""
        if ((time()-self._time_inputs) < PIC_CYCLE_DURATION):
            return self.xbeeAssoc
        self.PIC_ReadInputs()
        return self.xbeeAssoc

    def PIC_ReadInputs(self):
        """Read input status from PIC."""
        if ((time()-self._time_inputs) < PIC_CYCLE_DURATION):
            return self.picInputs

        register = 5
        length = 2
        pause = 0.0016
        sleep(pause)
        i2c_reply = self.i2cRead(register, length, pause)
        if isinstance(i2c_reply, int):
            return i2c_reply

        self._time_inputs = time()
        self.picInputs = i2c_reply[1]
        self.button = (self.picInputs >> 0) & 1
        self.buttonPower = (self.picInputs >> 1) & 1
        self.accelInt1 = (self.picInputs >> 2) & 1
        self.gyroInt1 = (self.picInputs >> 3) & 1
        self.gyroInt2 = (self.picInputs >> 4) & 1
        self.chgPresent = (self.picInputs >> 5) & 1
        self.chgInProg = (self.picInputs >> 6) & 1
        self.xbeeAssoc = (self.picInputs >> 7) & 1
        return self.picInputs

    # Comparator Methods
    def current_comp(self):
        """Get current comparator status."""
        if ((time()-self._time_comparators) < PIC_CYCLE_DURATION):
            return self.currentComparator
        self.PIC_ReadComparators()
        return self.currentComparator

    def voltage_comp(self):
        """Get voltage comparator status."""
        if ((time()-self._time_comparators) < PIC_CYCLE_DURATION):
            return self.voltageComparator
        self.PIC_ReadComparators()
        return self.voltageComparator

    def left_outer_comp(self):
        """Get left outer comparator status."""
        if ((time()-self._time_comparators) < PIC_CYCLE_DURATION):
            return self.leftOuterComparator
        self.PIC_ReadComparators()
        return self.leftOuterComparator

    def left_inner_comp(self):
        """Get left inner comparator status."""
        if ((time()-self._time_comparators) < PIC_CYCLE_DURATION):
            return self.leftInnerComparator
        self.PIC_ReadComparators()
        return self.leftInnerComparator

    def right_outer_comp(self):
        """Get right outer comparator status."""
        if ((time()-self._time_comparators) < PIC_CYCLE_DURATION):
            return self.rightOuterComparator
        self.PIC_ReadComparators()
        return self.rightOuterComparator

    def right_inner_comp(self):
        """Get right inner comparator status."""
        if ((time()-self._time_comparators) < PIC_CYCLE_DURATION):
            return self.rightInnerComparator
        self.PIC_ReadComparators()
        return self.rightInnerComparator

    def rear_outer_comp(self):
        """Get rear outer comparator status."""
        if ((time()-self._time_comparators) < PIC_CYCLE_DURATION):
            return self.rearOuterComparator
        self.PIC_ReadComparators()
        return self.rearOuterComparator

    def rear_inner_comp(self):
        """Get rear inner comparator status."""
        if ((time()-self._time_comparators) < PIC_CYCLE_DURATION):
            return self.rearInnerComparator
        self.PIC_ReadComparators()
        return self.rearInnerComparator

    def rangefinder_comp(self):
        """Get rangefinder comparator status."""
        if ((time()-self._time_comparators) < PIC_CYCLE_DURATION):
            return self.rangefinderComparator
        self.PIC_ReadComparators()
        return self.rangefinderComparator

    def amb_left_comp(self):
        """Get ambient left comparator status."""
        if ((time()-self._time_comparators) < PIC_CYCLE_DURATION):
            return self.ambLeftComparator
        self.PIC_ReadComparators()
        return self.ambLeftComparator

    def amb_right_comp(self):
        """Get ambient right comparator status."""
        if ((time()-self._time_comparators) < PIC_CYCLE_DURATION):
            return self.ambRightComparator
        self.PIC_ReadComparators()
        return self.ambRightComparator

    def amb_rear_comp(self):
        """Get ambient rear comparator status."""
        if ((time()-self._time_comparators) < PIC_CYCLE_DURATION):
            return self.ambRearComparator
        self.PIC_ReadComparators()
        return self.ambRearComparator

    def wall_power_comp(self):
        """Get wall power comparator status."""
        if ((time()-self._time_comparators) < PIC_CYCLE_DURATION):
            return self.wallPowerComparator
        self.PIC_ReadComparators()
        return self.wallPowerComparator

    def PIC_ReadComparators(self):
        """Read comparator status from PIC."""
        if ((time()-self._time_comparators) < PIC_CYCLE_DURATION):
            return (self.thresholdComparators1, self.thresholdComparators2)

        register = 6
        length = 3
        pause = 0.0016
        sleep(pause)
        i2c_reply = self.i2cRead(register, length, pause)
        if isinstance(i2c_reply, int):
            return i2c_reply

        self._time_comparators = time()
        self.thresholdComparators1 = i2c_reply[1]
        self.thresholdComparators2 = i2c_reply[2]
        self.currentComparator = (self.thresholdComparators1 >> 0) & 1
        self.voltageComparator = (self.thresholdComparators1 >> 1) & 1
        self.leftOuterComparator = (self.thresholdComparators1 >> 2) & 1
        self.leftInnerComparator = (self.thresholdComparators1 >> 3) & 1
        self.rightOuterComparator = (self.thresholdComparators1 >> 4) & 1
        self.rightInnerComparator = (self.thresholdComparators1 >> 5) & 1
        self.rearOuterComparator = (self.thresholdComparators1 >> 6) & 1
        self.rearInnerComparator = (self.thresholdComparators1 >> 7) & 1
        self.rangefinderComparator = (self.thresholdComparators2 >> 0) & 1
        self.ambLeftComparator = (self.thresholdComparators2 >> 1) & 1
        self.ambRightComparator = (self.thresholdComparators2 >> 2) & 1
        self.ambRearComparator = (self.thresholdComparators2 >> 3) & 1
        self.wallPowerComparator = (self.thresholdComparators2 >> 4) & 1
        return (self.thresholdComparators1, self.thresholdComparators2)

    # Power Status Methods
    def power_voltage(self):
        """Get current battery voltage in volts."""
        if ((time()-self._time_power) < PIC_CYCLE_DURATION):
            return self.powerVoltage
        self.PIC_ReadPower()
        return self.powerVoltage

    def power_current(self):
        """Get current battery current in amps."""
        if ((time()-self._time_power) < PIC_CYCLE_DURATION):
            return self.powerCurrent
        self.PIC_ReadPower()
        return self.powerCurrent

    def PIC_ReadPower(self):
        """Read power voltage and current from PIC."""
        if ((time()-self._time_power) < PIC_CYCLE_DURATION):
            return (self.powerVoltage, self.powerCurrent)

        register = 21
        length = 5
        pause = 0.0016
        sleep(pause)
        i2c_reply = self.i2cRead(register, length, pause)
        if isinstance(i2c_reply, int):
            return i2c_reply

        self._time_power = time()
        self.powerVoltage = i2c_reply[1] << 8 | i2c_reply[2]
        self.powerCurrent = i2c_reply[3] << 8 | i2c_reply[4]
        self.powerVoltage = float(self.powerVoltage) / 1000
        self.powerCurrent = float(self.powerCurrent) / 1000
        return (self.powerVoltage, self.powerCurrent)

    def power_voltage_avg(self):
        """Get average battery voltage in volts."""
        if ((time()-self._time_power_average) < PIC_CYCLE_DURATION):
            return self.powerVoltageAverage
        self.PIC_ReadPowerAverages()
        return self.powerVoltageAverage

    def power_current_avg(self):
        """Get average battery current in amps."""
        if ((time()-self._time_power_average) < PIC_CYCLE_DURATION):
            return self.powerCurrentAverage
        self.PIC_ReadPowerAverages()
        return self.powerCurrentAverage

    def PIC_ReadPowerAverages(self):
        """Read average power values from PIC."""
        if ((time()-self._time_power_average) < PIC_CYCLE_DURATION):
            return (self.powerVoltageAverage, self.powerCurrentAverage)

        register = 26
        length = 5
        pause = 0.0025
        sleep(pause)
        i2c_reply = self.i2cRead(register, length, pause)
        if isinstance(i2c_reply, int):
            return i2c_reply

        self._time_power_average = time()
        self.powerVoltageAverage = i2c_reply[1] << 8 | i2c_reply[2]
        self.powerCurrentAverage = i2c_reply[3] << 8 | i2c_reply[4]
        self.powerVoltageAverage = float(self.powerVoltageAverage) / 1000
        self.powerCurrentAverage = float(self.powerCurrentAverage) / 1000
        return (self.powerVoltageAverage, self.powerCurrentAverage)

    # Ambient Sensor Methods
    def amb_left(self):
        """Get left ambient light sensor reading."""
        if ((time()-self._time_ambient) < PIC_CYCLE_DURATION):
            return self.ambLeft
        self.PIC_ReadAllAmbientSensors()
        return self.ambLeft

    def amb_right(self):
        """Get right ambient light sensor reading."""
        if ((time()-self._time_ambient) < PIC_CYCLE_DURATION):
            return self.ambRight
        self.PIC_ReadAllAmbientSensors()
        return self.ambRight

    def amb_rear(self):
        """Get rear ambient light sensor reading."""
        if ((time()-self._time_ambient) < PIC_CYCLE_DURATION):
            return self.ambRear
        self.PIC_ReadAllAmbientSensors()
        return self.ambRear

    def PIC_ReadAllAmbientSensors(self):
        """Read all ambient light sensors from PIC."""
        if ((time()-self._time_ambient) < PIC_CYCLE_DURATION):
            return (self.ambLeft, self.ambRight, self.ambRear)

        register = 32
        length = 7
        pause = 0.0016
        sleep(pause)
        i2c_reply = self.i2cRead(register, length, pause)
        if isinstance(i2c_reply, int):
            return i2c_reply

        self._time_ambient = time()
        self.ambLeft = i2c_reply[1] << 8 | i2c_reply[2]
        self.ambRight = i2c_reply[3] << 8 | i2c_reply[4]
        self.ambRear = i2c_reply[5] << 8 | i2c_reply[6]
        return (self.ambLeft, self.ambRight, self.ambRear)

    def amb_left_avg(self):
        """Get average left ambient light sensor reading."""
        if ((time()-self._time_ambient_average) < PIC_CYCLE_DURATION):
            return self.ambLeftAverage
        self.PIC_ReadAllAmbientAverages()
        return self.ambLeftAverage

    def amb_right_avg(self):
        """Get average right ambient light sensor reading."""
        if ((time()-self._time_ambient_average) < PIC_CYCLE_DURATION):
            return self.ambRightAverage
        self.PIC_ReadAllAmbientAverages()
        return self.ambRightAverage

    def amb_rear_avg(self):
        """Get average rear ambient light sensor reading."""
        if ((time()-self._time_ambient_average) < PIC_CYCLE_DURATION):
            return self.ambRearAverage
        self.PIC_ReadAllAmbientAverages()
        return self.ambRearAverage

    def PIC_ReadAllAmbientAverages(self):
        """Read average ambient light sensor values from PIC."""
        if ((time()-self._time_ambient_average) < PIC_CYCLE_DURATION):
            return (self.ambLeftAverage, self.ambRightAverage, self.ambRearAverage)

        register = 35
        length = 7
        pause = 0.0016
        sleep(pause)
        i2c_reply = self.i2cRead(register, length, pause)
        if isinstance(i2c_reply, int):
            return i2c_reply

        self._time_ambient_average = time()
        self.ambLeftAverage = i2c_reply[1] << 8 | i2c_reply[2]
        self.ambRightAverage = i2c_reply[3] << 8 | i2c_reply[4]
        self.ambRearAverage = i2c_reply[5] << 8 | i2c_reply[6]
        return (self.ambLeftAverage, self.ambRightAverage, self.ambRearAverage)

    # Surface Sensor Methods
    def surf_left_0(self):
        """Get left outer surface sensor reading."""
        if ((time()-self._time_surface) < PIC_CYCLE_DURATION):
            return self.surfLeft0
        self.PIC_ReadAllSurfaceSensors()
        return self.surfLeft0

    def surf_left_1(self):
        """Get left inner surface sensor reading."""
        if ((time()-self._time_surface) < PIC_CYCLE_DURATION):
            return self.surfLeft1
        self.PIC_ReadAllSurfaceSensors()
        return self.surfLeft1

    def surf_right_0(self):
        """Get right outer surface sensor reading."""
        if ((time()-self._time_surface) < PIC_CYCLE_DURATION):
            return self.surfRight0
        self.PIC_ReadAllSurfaceSensors()
        return self.surfRight0

    def surf_right_1(self):
        """Get right inner surface sensor reading."""
        if ((time()-self._time_surface) < PIC_CYCLE_DURATION):
            return self.surfRight1
        self.PIC_ReadAllSurfaceSensors()
        return self.surfRight1

    def surf_rear_0(self):
        """Get rear outer surface sensor reading."""
        if ((time()-self._time_surface) < PIC_CYCLE_DURATION):
            return self.surfRear0
        self.PIC_ReadAllSurfaceSensors()
        return self.surfRear0

    def surf_rear_1(self):
        """Get rear inner surface sensor reading."""
        if ((time()-self._time_surface) < PIC_CYCLE_DURATION):
            return self.surfRear1
        self.PIC_ReadAllSurfaceSensors()
        return self.surfRear1

    def PIC_ReadAllSurfaceSensors(self):
        """Read all surface sensors from PIC."""
        if ((time()-self._time_surface) < PIC_CYCLE_DURATION):
            return (self.surfLeft1, self.surfLeft0, self.surfRight0,
                    self.surfRight1, self.surfRear0, self.surfRear1)

        register = 31
        length = 13
        pause = 0.0017
        sleep(pause)
        i2c_reply = self.i2cRead(register, length, pause)
        if isinstance(i2c_reply, int):
            return i2c_reply

        self._time_surface = time()
        self.surfLeft0 = i2c_reply[1] << 8 | i2c_reply[2]
        self.surfRight0 = i2c_reply[3] << 8 | i2c_reply[4]
        self.surfRear0 = i2c_reply[5] << 8 | i2c_reply[6]
        self.surfLeft1 = i2c_reply[7] << 8 | i2c_reply[8]
        self.surfRight1 = i2c_reply[9] << 8 | i2c_reply[10]
        self.surfRear1 = i2c_reply[11] << 8 | i2c_reply[12]
        return (self.surfLeft1, self.surfLeft0, self.surfRight0,
                self.surfRight1, self.surfRear0, self.surfRear1)

    def surf_left_0_avg(self):
        """Get average left outer surface sensor reading."""
        if ((time()-self._time_surface_average) < PIC_CYCLE_DURATION):
            return self.surfLeft0Average
        self.PIC_ReadAllSurfaceAverages()
        return self.surfLeft0Average

    def surf_left_1_avg(self):
        """Get average left inner surface sensor reading."""
        if ((time()-self._time_surface_average) < PIC_CYCLE_DURATION):
            return self.surfLeft1Average
        self.PIC_ReadAllSurfaceAverages()
        return self.surfLeft1Average

    def surf_right_0_avg(self):
        """Get average right outer surface sensor reading."""
        if ((time()-self._time_surface_average) < PIC_CYCLE_DURATION):
            return self.surfRight0Average
        self.PIC_ReadAllSurfaceAverages()
        return self.surfRight0Average

    def surf_right_1_avg(self):
        """Get average right inner surface sensor reading."""
        if ((time()-self._time_surface_average) < PIC_CYCLE_DURATION):
            return self.surfRight1Average
        self.PIC_ReadAllSurfaceAverages()
        return self.surfRight1Average

    def surf_rear_0_avg(self):
        """Get average rear outer surface sensor reading."""
        if ((time()-self._time_surface_average) < PIC_CYCLE_DURATION):
            return self.surfRear0Average
        self.PIC_ReadAllSurfaceAverages()
        return self.surfRear0Average

    def surf_rear_1_avg(self):
        """Get average rear inner surface sensor reading."""
        if ((time()-self._time_surface_average) < PIC_CYCLE_DURATION):
            return self.surfRear1Average
        self.PIC_ReadAllSurfaceAverages()
        return self.surfRear1Average

    def PIC_ReadAllSurfaceAverages(self):
        """Read average surface sensor values from PIC."""
        if ((time()-self._time_surface_average) < PIC_CYCLE_DURATION):
            return (self.surfLeft1Average, self.surfLeft0Average, self.surfRight0Average,
                    self.surfRight1Average, self.surfRear0Average, self.surfRear1Average)

        register = 36
        length = 13
        pause = 0.0017
        sleep(pause)
        i2c_reply = self.i2cRead(register, length, pause)
        if isinstance(i2c_reply, int):
            return i2c_reply

        self._time_surface_average = time()
        self.surfLeft0Average = i2c_reply[1] << 8 | i2c_reply[2]
        self.surfRight0Average = i2c_reply[3] << 8 | i2c_reply[4]
        self.surfRear0Average = i2c_reply[5] << 8 | i2c_reply[6]
        self.surfLeft1Average = i2c_reply[7] << 8 | i2c_reply[8]
        self.surfRight1Average = i2c_reply[9] << 8 | i2c_reply[10]
        self.surfRear1Average = i2c_reply[11] << 8 | i2c_reply[12]
        return (self.surfLeft1Average, self.surfLeft0Average, self.surfRight0Average,
                self.surfRight1Average, self.surfRear0Average, self.surfRear1Average)

    # Servo Control Methods
    def servo_speed(self, speed_dps):
        """Set servo speed in degrees per second (1-3000)."""
        register = 51
        pause = 0.0015
        self.servoSpeed = int(speed_dps)
        self.servoSpeed = self.clamp(self.servoSpeed, 1, 3000)
        data = [((self.servoSpeed >> 8) & 0xFF), (self.servoSpeed & 0xFF)]
        resp = self.i2cWrite(register, data, pause)
        return resp

    def servo_tilt(self, position):
        """Set tilt servo position (-90 to 90 degrees)."""
        register = 52
        pause = 0.0015
        self.servoTilt = int(position)
        self.servoTilt = self.clamp(self.servoTilt, -90, 90)
        servoSetpoint = self.servoTilt + SERVO_CENTER_TILT
        data = [servoSetpoint]
        resp = self.i2cWrite(register, data, pause)
        return resp

    def servo_tilt_move(self, offset):
        """Move tilt servo by relative offset."""
        register = 52
        pause = 0.0015
        offset = int(offset)
        self.servoTilt = self.servoTilt + offset
        self.servoTilt = self.clamp(self.servoTilt, -90, 90)
        servoSetpoint = self.servoTilt + SERVO_CENTER_TILT
        data = [servoSetpoint]
        resp = self.i2cWrite(register, data, pause)
        return resp

    def servo_pan(self, position):
        """Set pan servo position (-90 to 90 degrees)."""
        register = 53
        pause = 0.0015
        self.servoPan = int(position)
        self.servoPan = self.clamp(self.servoPan, -90, 90)
        servoSetpoint = self.servoPan + SERVO_CENTER_PAN
        data = [servoSetpoint]
        resp = self.i2cWrite(register, data, pause)
        return resp

    def servo_pan_move(self, offset):
        """Move pan servo by relative offset."""
        register = 53
        pause = 0.0015
        offset = int(offset)
        self.servoPan = self.servoPan + offset
        self.servoPan = self.clamp(self.servoPan, -90, 90)
        servoSetpoint = self.servoPan + SERVO_CENTER_PAN
        data = [servoSetpoint]
        resp = self.i2cWrite(register, data, pause)
        return resp

    def servo_grip(self, position):
        """Set grip servo position (-10 to 180 degrees)."""
        register = 54
        pause = 0.0015
        self.servoGrip = int(position)
        self.servoGrip = self.clamp(self.servoGrip, -10, 180)
        servoSetpoint = self.servoGrip + SERVO_CENTER_GRIP
        data = [servoSetpoint]
        resp = self.i2cWrite(register, data, pause)
        return resp

    def servo_grip_move(self, offset):
        """Move grip servo by relative offset."""
        register = 54
        pause = 0.0015
        offset = int(offset)
        self.servoGrip = self.servoGrip + offset
        self.servoGrip = self.clamp(self.servoGrip, -10, 180)
        servoSetpoint = self.servoGrip + SERVO_CENTER_GRIP
        data = [servoSetpoint]
        resp = self.i2cWrite(register, data, pause)
        return resp

    def servo_trim_tilt(self, trim):
        """Set tilt servo trim (-45 to 45)."""
        register = 55
        pause = 0.0015
        self.servoTrim_Tilt = int(trim)
        self.servoTrim_Tilt = self.clamp(self.servoTrim_Tilt, -45, 45)
        servoTrimpoint = self.servoTrim_Tilt + 127
        data = [servoTrimpoint]
        resp = self.i2cWrite(register, data, pause)
        return resp

    def servo_trim_pan(self, trim):
        """Set pan servo trim (-45 to 45)."""
        register = 56
        pause = 0.0015
        self.servoTrim_Pan = int(trim)
        self.servoTrim_Pan = self.clamp(self.servoTrim_Pan, -45, 45)
        servoTrimpoint = self.servoTrim_Pan + 127
        data = [servoTrimpoint]
        resp = self.i2cWrite(register, data, pause)
        return resp

    def servo_trim_grip(self, trim):
        """Set grip servo trim (-45 to 45)."""
        register = 57
        pause = 0.0015
        self.servoTrim_Grip = int(trim)
        self.servoTrim_Grip = self.clamp(self.servoTrim_Grip, -45, 45)
        servoTrimpoint = self.servoTrim_Grip + 127
        data = [servoTrimpoint]
        resp = self.i2cWrite(register, data, pause)
        return resp

    # Rangefinder Control Methods
    def rangefinder_auto_interval(self, interval):
        """Set rangefinder automatic reading interval."""
        self.rangeAutoInterval = self.clamp(
            interval, 0, (250*PIC_CYCLE_DURATION))
        if (self.rangeAutoInterval > 0) and (self.rangeAutoInterval < PIC_CYCLE_DURATION):
            interval_PIC = 1
        else:
            interval_PIC = int(self.rangeAutoInterval/PIC_CYCLE_DURATION)
        register = 65
        pause = 0.0015
        data = [interval_PIC]
        resp = self.i2cWrite(register, data, pause)
        return resp

    def rangefinder(self):
        """Get rangefinder distance measurement."""
        if ((time()-self._time_rangefinder) < PIC_CYCLE_DURATION):
            return self.rangefinderDistance
        self.PIC_ReadRangefinder()
        return self.rangefinderDistance

    def rangefinder_good_counts(self):
        """Get rangefinder good counts."""
        if ((time()-self._time_rangefinder) < PIC_CYCLE_DURATION):
            return self.rangefinderGoodCounts
        self.PIC_ReadRangefinder()
        return self.rangefinderGoodCounts

    def PIC_ReadRangefinder(self):
        """Read rangefinder data from PIC."""
        if ((time()-self._time_rangefinder) < PIC_CYCLE_DURATION):
            return (self.rangefinderDistance, self.rangefinderGoodCounts)

        register = 66
        length = 4
        pause = 0.0017
        sleep(pause)
        i2c_reply = self.i2cRead(register, length, pause)
        if isinstance(i2c_reply, int):
            return i2c_reply

        self._time_rangefinder = time()
        self.rangefinderDistance = i2c_reply[1] << 8 | i2c_reply[2]
        self.rangefinderGoodCounts = i2c_reply[3]
        return (self.rangefinderDistance, self.rangefinderGoodCounts)

    # Configuration Methods
    def avg_interval_surface(self, avgPeriod):
        """Set surface sensor averaging interval."""
        register = 101
        pause = 0.0015
        temp = (avgPeriod / (PIC_CYCLE_DURATION*8))
        self.avgIntervalSurface = int(round(temp, 0))
        data = [self.avgIntervalSurface,
                self.avgIntervalAmbient, self.avgIntervalPower]
        resp = self.i2cWrite(register, data, pause)
        return resp

    def avg_interval_ambient(self, avgPeriod):
        """Set ambient sensor averaging interval."""
        register = 101
        pause = 0.0015
        temp = (avgPeriod / (PIC_CYCLE_DURATION*8))
        self.avgIntervalAmbient = int(round(temp, 0))
        data = [self.avgIntervalSurface,
                self.avgIntervalAmbient, self.avgIntervalPower]
        resp = self.i2cWrite(register, data, pause)
        return resp

    def avg_interval_power(self, avgPeriod):
        """Set power sensor averaging interval."""
        register = 101
        pause = 0.0015
        temp = (avgPeriod / (PIC_CYCLE_DURATION*8))
        self.avgIntervalPower = int(round(temp, 0))
        data = [self.avgIntervalSurface,
                self.avgIntervalAmbient, self.avgIntervalPower]
        resp = self.i2cWrite(register, data, pause)
        return resp

    def i2c_process_delay(self, delay):
        """Set I2C process delay (normally not needed to adjust)."""
        register = 109
        pause = 0.0015
        delay = self.clamp(delay, 1, 250)
        data = [delay]
        resp = self.i2cWrite(register, data, pause)
        return resp

    # Sound (Piezo Chirp) Methods
    def chirp(self, frequency):
        """Play a tone on the piezo element.

        Args:
            frequency: Tone frequency in Hz (0 turns the piezo off).
        """
        register = 41
        pause = 0.0015
        frequency = self.clamp(int(frequency), 0, 65535)
        data = [(frequency >> 8) & 0xFF, frequency & 0xFF]
        return self.i2cWrite(register, data, pause)

    def chirp_off(self):
        """Silence the piezo element."""
        return self.chirp(0)

    # Instant Power Methods (PIC pauses to take a fresh reading)
    def power_instant(self):
        """Read instantaneous battery voltage and current.

        Returns:
            ``(voltage_volts, current_amps)`` on success, or a negative error
            code from :meth:`i2cRead`.
        """
        register = 22
        length = 5
        pause = 0.0017
        sleep(pause)
        i2c_reply = self.i2cRead(register, length, pause)
        if isinstance(i2c_reply, int):
            return i2c_reply
        self._time_power = time()
        self.powerVoltage = (i2c_reply[1] << 8 | i2c_reply[2]) / 1000.0
        self.powerCurrent = (i2c_reply[3] << 8 | i2c_reply[4]) / 1000.0
        return (self.powerVoltage, self.powerCurrent)

    def power_voltage_instant(self):
        """Read instantaneous battery voltage in volts."""
        register = 23
        length = 3
        pause = 0.0017
        sleep(pause)
        i2c_reply = self.i2cRead(register, length, pause)
        if isinstance(i2c_reply, int):
            return i2c_reply
        self.powerVoltage = (i2c_reply[1] << 8 | i2c_reply[2]) / 1000.0
        return self.powerVoltage

    def power_current_instant(self):
        """Read instantaneous battery current in amps."""
        register = 24
        length = 3
        pause = 0.0017
        sleep(pause)
        i2c_reply = self.i2cRead(register, length, pause)
        if isinstance(i2c_reply, int):
            return i2c_reply
        self.powerCurrent = (i2c_reply[1] << 8 | i2c_reply[2]) / 1000.0
        return self.powerCurrent

    # Servo Motion / Centering Methods
    def servos_in_motion(self):
        """Report which servos are still moving.

        Returns:
            A dict ``{"tilt": bool, "pan": bool, "grip": bool, "any": bool}`` on
            success, or a negative error code from :meth:`i2cRead`.
        """
        register = 50
        length = 2
        pause = 0.0016
        sleep(pause)
        i2c_reply = self.i2cRead(register, length, pause)
        if isinstance(i2c_reply, int):
            return i2c_reply
        flags = i2c_reply[1]
        return {
            "tilt": bool((flags >> 0) & 1),
            "pan": bool((flags >> 1) & 1),
            "grip": bool((flags >> 2) & 1),
            "any": bool(flags & 0x07),
        }

    def servos_center(self):
        """Return all three servos (tilt, pan, grip) to their center positions."""
        self.servo_tilt(0)
        self.servo_pan(0)
        self.servo_grip(0)

    # Rangefinder Convenience Methods
    def rangefinder_enable(self):
        """Start automatic ranging at ~50 measurements per second."""
        register = 65
        pause = 0.0015
        self.rangeAutoInterval = PIC_CYCLE_DURATION
        return self.i2cWrite(register, [1], pause)

    def rangefinder_disable(self):
        """Stop automatic ranging."""
        register = 65
        pause = 0.0015
        self.rangeAutoInterval = 0
        return self.i2cWrite(register, [0], pause)

    def rangefinder_present(self):
        """Return True if an ultrasonic rangefinder is detected on the PIC."""
        register = 70
        length = 2
        pause = 0.0016
        sleep(pause)
        i2c_reply = self.i2cRead(register, length, pause)
        if isinstance(i2c_reply, int):
            return i2c_reply
        return bool(i2c_reply[1])

    # Device Information
    def pic_software_version(self):
        """Return the firmware version reported by the PIC processor."""
        register = 120
        length = 3
        pause = 0.0016
        sleep(pause)
        i2c_reply = self.i2cRead(register, length, pause)
        if isinstance(i2c_reply, int):
            return i2c_reply
        return i2c_reply[1] << 8 | i2c_reply[2]

    # Low-level I2C/SPI Communication Methods
    def i2cRead(self, register, length, pause):
        """Read data from PIC via I2C.

        Returns the reply list on success, or a negative error code:
        -1 write failed, -2 read failed, -3 unexpected register echoed back.
        """
        sleep(pause)
        try:
            self.i2c.write_byte(PIC_I2C_ADDRESS, register)
        except OSError as e:
            logger.warning("I2C write failed (register %s): %s", register, e)
            return -1

        sleep(pause + (self.i2c_read_extra_pause * .000001))
        try:
            i2c_reply = self.i2c.read_i2c_block_data(
                PIC_I2C_ADDRESS, register, length)
        except OSError as e:
            logger.warning("I2C read failed (register %s): %s", register, e)
            return -2

        if i2c_reply[0] != register:
            logger.warning(
                "I2C register mismatch: expected %s, got %s", register, i2c_reply[0])
            return -3
        return i2c_reply

    def i2cWrite(self, register, data, pause):
        """Write data to PIC via I2C. Returns 0 on success, -1 on failure."""
        sleep(pause)
        try:
            self.i2c.write_i2c_block_data(PIC_I2C_ADDRESS, register, data)
        except OSError as e:
            logger.warning("I2C write failed (register %s): %s", register, e)
            return -1
        return 0

    def i2cTest(self):
        """Test I2C communication by reading the surface-sensor block."""
        register = 31
        length = 12
        sleep(0.0015)
        try:
            self.i2c.write_byte(PIC_I2C_ADDRESS, register)
        except OSError as e:
            logger.warning("I2C test write failed: %s", e)
            return -1
        sleep(0.0015)
        try:
            i2c_reply = self.i2c.read_i2c_block_data(
                PIC_I2C_ADDRESS, register, length)
        except OSError as e:
            logger.warning("I2C test read failed: %s", e)
            return -2
        if i2c_reply[0] != register:
            logger.warning(
                "I2C test register mismatch: expected %s, got %s", register, i2c_reply[0])
            return -1
        return i2c_reply

    def spi_transfer(self, data_to_send):
        """Transfer data via SPI, appending padding and an XOR checksum.

        Args:
            data_to_send: A byte value or a list of byte values (max
                ``SPI_PAYLOAD_MAX_LENGTH``). The caller's list is never mutated.

        Returns:
            The SPI response list, or -1 if the payload is too long.
        """
        if isinstance(data_to_send, int):
            payload = [data_to_send, 0x00]
        else:
            payload = list(data_to_send)

        if len(payload) > SPI_PAYLOAD_MAX_LENGTH:
            logger.error(
                "spi_transfer: payload too long (%s > %s bytes)",
                len(payload), SPI_PAYLOAD_MAX_LENGTH)
            return -1

        payload.extend([0x00] * (SPI_PAYLOAD_MAX_LENGTH - len(payload)))
        payload.append(self.compute_checksum(payload))
        payload.append(0x00)
        return self.spi.xfer2(payload)

    @staticmethod
    def compute_checksum(data):
        """
        Calculate XOR checksum for SPI data.

        Args:
            data: Data array to calculate checksum for

        Returns:
            Checksum byte (XOR of all data bytes)
        """
        xor = 0
        for data_byte in data:
            xor ^= data_byte
        return xor

    @staticmethod
    def clamp(n, minn, maxn):
        """
        Constrain a value to within a given range.

        Args:
            n: Value to clamp
            minn: Minimum value
            maxn: Maximum value

        Returns:
            Clamped value
        """
        return max(minn, min(n, maxn))
