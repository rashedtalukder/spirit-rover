"""
Spirit Rover Pixel Control Interface

Provides control for RGB LED pixels (eyes and wings) via socket connection
to the pixel server process.
"""

import logging
import socket

from .constants import PIXEL_SERVER_PORT

logger = logging.getLogger(__name__)


class PixelController:
    """
    Controller for Spirit Rover LED pixels.

    Communicates with the pixel server daemon to control RGB LEDs
    for eyes and wing animations.

    Can be used as a context manager so the socket is always closed::

        with PixelController() as pixels:
            pixels.eyes(200, 100)
    """

    def __init__(self, host=None, port=PIXEL_SERVER_PORT, timeout=2.0):
        """
        Initialize pixel controller.

        Args:
            host: Hostname to connect to (default: local machine)
            port: Port number for pixel server (default: 20568)
            timeout: Socket connect/send timeout in seconds.
        """
        self.hue_eyes = 140
        self.hue_wings = 200
        self.host = host if host else socket.gethostname()
        self.port = port
        self.timeout = timeout
        self.socket = None
        self.connected = False

        self._connect()

    def _connect(self):
        """Establish connection to pixel server."""
        try:
            self.socket = socket.create_connection(
                (self.host, self.port), timeout=self.timeout)
            self.connected = True
        except OSError as e:
            logger.warning(
                "Could not connect to pixel server on %s:%s - %s",
                self.host, self.port, e)
            logger.warning(
                "Pixel functions will be no-ops. Is the pixel server running?")
            self.socket = None
            self.connected = False

    def _send_command(self, data):
        """Send a command string to the pixel server if connected."""
        if not self.connected:
            return
        if isinstance(data, str):
            data = data.encode("ascii")
        try:
            self.socket.sendall(data)
        except OSError as e:
            logger.warning("Error sending pixel command: %s", e)
            self.connected = False


    def hue_eye_up(self):
        """Increase eye hue by 20 degrees."""
        self.hue_eyes = self.hue_eyes + 20
        if self.hue_eyes > 360:
            self.hue_eyes = 20
        self.eyes(self.hue_eyes, 200)

    def hue_eye_down(self):
        """Decrease eye hue by 20 degrees."""
        self.hue_eyes = self.hue_eyes - 20
        if self.hue_eyes < 0:
            self.hue_eyes = 340
        self.eyes(self.hue_eyes, 200)

    def hue_wing_up(self):
        """Increase wing hue by 20 degrees."""
        self.hue_wings = self.hue_wings + 20
        if self.hue_wings > 360:
            self.hue_wings = 20

    def hue_wing_down(self):
        """Decrease wing hue by 20 degrees."""
        self.hue_wings = self.hue_wings - 20
        if self.hue_wings < 0:
            self.hue_wings = 340

    def eyes(self, hue, brightness):
        """
        Set eye pixels to specified color and brightness.

        Args:
            hue: Color hue (0-360 on color wheel)
            brightness: Brightness level (0-255)
        """
        animation_index = 12
        self._send_command(f"{animation_index}:{hue}:{brightness}")

    def wings_autofade(self, hue, bright, fall_off, over_under, streak_mode, interval):
        """
        Start automated wing fade animation.

        Args:
            hue: Color hue (0-360)
            bright: Brightness (0-255)
            fall_off: Fade fall-off rate
            over_under: Over/under fade parameter
            streak_mode: Streak animation mode
            interval: Animation speed interval
        """
        animation_index = 32
        self._send_command(
            f"{animation_index}:{hue}:{bright}:{fall_off}:"
            f"{over_under}:{streak_mode}:{interval}")

    def hue_pixel(self, pixel_index, hue=0, brightness=0):
        """
        Set individual pixel to specified color and brightness.

        Args:
            pixel_index: Index of pixel to control (starting from 0)
            hue: Color hue (0-360)
            brightness: Brightness level (0-255)
        """
        animation_index = 5
        self._send_command(
            f"{animation_index}:{pixel_index}:{hue}:{brightness}")

    def pixels_off(self):
        """Turn off all pixels."""
        animation_index = 2
        self._send_command(f"{animation_index}:")

    def close(self):
        """Close connection to pixel server. Safe to call multiple times."""
        if self.socket is not None:
            try:
                self.socket.close()
            except OSError:
                logger.debug("Error closing pixel socket", exc_info=True)
            self.socket = None
        self.connected = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
