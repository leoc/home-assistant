"""
components.arduino
~~~~~~~~~~~~~~~~~~
Arduino component that connects to a directly attached Arduino board which
runs with the Firmata firmware.

Configuration:

To use the Arduino board you will need to add something like the following
to your configuration.yaml file.

arduino:
    port: /dev/ttyACM0

Variables:

port
*Required
The port where is your board connected to your Home Assistant system.
If you are using an original Arduino the port will be named ttyACM*. The exact
number can be determined with 'ls /dev/ttyACM*' or check your 'dmesg'/
'journalctl -f' output. Keep in mind that Arduino clones are often using a
different name for the port (e.g. '/dev/ttyUSB*').

A word of caution: The Arduino is not storing states. This means that with
every initialization the pins are set to off/low.
"""
import logging

try:
    from PyMata.pymata import PyMata
except ImportError:
    PyMata = None

from homeassistant.helpers import validate_config
from homeassistant.const import (EVENT_HOMEASSISTANT_START,
                                 EVENT_HOMEASSISTANT_STOP)

DOMAIN = "arduino"
DEPENDENCIES = []
REQUIREMENTS = ['PyMata==2.07a']
BOARD = None
_LOGGER = logging.getLogger(__name__)


def setup(hass, config):
    """ Setup the Arduino component. """

    global PyMata  # pylint: disable=invalid-name
    if PyMata is None:
        from PyMata.pymata import PyMata as PyMata_
        PyMata = PyMata_

    import serial

    if not validate_config(config,
                           {DOMAIN: ['port']},
                           _LOGGER):
        return False

    global BOARD
    try:
        BOARD = ArduinoBoard(config[DOMAIN]['port'])
    except (serial.serialutil.SerialException, FileNotFoundError):
        _LOGGER.exception("Your port is not accessible.")
        return False

    if BOARD.get_firmata()[1] <= 2:
        _LOGGER.error("The StandardFirmata sketch should be 2.2 or newer.")
        return False

    def stop_arduino(event):
        """ Stop the Arduino service. """
        BOARD.disconnect()

    def start_arduino(event):
        """ Start the Arduino service. """
        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_arduino)

    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, start_arduino)

    return True


class ArduinoBoard(object):
    """ Represents an Arduino board. """

    def __init__(self, port):
        self._port = port
        self._board = PyMata(self._port, verbose=False)

    def set_mode(self, pin, direction, mode):
        """ Sets the mode and the direction of a given pin. """
        if mode == 'analog' and direction == 'in':
            self._board.set_pin_mode(pin,
                                     self._board.INPUT,
                                     self._board.ANALOG)
        elif mode == 'analog' and direction == 'out':
            self._board.set_pin_mode(pin,
                                     self._board.OUTPUT,
                                     self._board.ANALOG)
        elif mode == 'digital' and direction == 'in':
            self._board.set_pin_mode(pin,
                                     self._board.OUTPUT,
                                     self._board.DIGITAL)
        elif mode == 'digital' and direction == 'out':
            self._board.set_pin_mode(pin,
                                     self._board.OUTPUT,
                                     self._board.DIGITAL)
        elif mode == 'pwm':
            self._board.set_pin_mode(pin,
                                     self._board.OUTPUT,
                                     self._board.PWM)

    def get_analog_inputs(self):
        """ Get the values from the pins. """
        self._board.capability_query()
        return self._board.get_analog_response_table()

    def set_digital_out_high(self, pin):
        """ Sets a given digital pin to high. """
        self._board.digital_write(pin, 1)

    def set_digital_out_low(self, pin):
        """ Sets a given digital pin to low. """
        self._board.digital_write(pin, 0)

    def get_digital_in(self, pin):
        """ Gets the value from a given digital pin. """
        self._board.digital_read(pin)

    def get_analog_in(self, pin):
        """ Gets the value from a given analog pin. """
        self._board.analog_read(pin)

    def get_firmata(self):
        """ Return the version of the Firmata firmware. """
        return self._board.get_firmata_version()

    def disconnect(self):
        """ Disconnects the board and closes the serial connection. """
        self._board.reset()
        self._board.close()