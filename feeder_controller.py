import re
import serial
import atexit
import time
import logging

class BoardPosition:
    """A position (slot) on a feeder board where a feeder can be connected."""

    def __init__(self, advance_angle=None, half_advance_angle=None,
                 retract_angle=None, default_feed_length=None, settle_time=None,
                 enabled=False, feeder_id=None):
        self._current_angle = None  # Transient value, not persisted
        self.advance_angle = advance_angle
        self.half_advance_angle = half_advance_angle
        self.retract_angle = retract_angle
        self.default_feed_length = default_feed_length
        self.settle_time = settle_time
        self._enabled = enabled
        self.feeder_id = None

    def update_angle(self, new_angle):
        self._current_angle = new_angle


    # Methods to CRUD feeders to a position
    def assign_feeder(self, feeder_id):
        self.feeder_id = feeder_id

    def remove_feeder(self):
        self.feeder_id = None

    @property
    def enabled(self):
        return self._enabled
    
    @enabled.setter
    def enabled(self, value):
        if isinstance(value, bool):
            if value and not self._enabled:
                if self.send_command("M610S1", self.handle_response):
                    self._enabled = True
            else:
                if self.send_command("M610S0", self.handle_response):
                    self._enabled = False


class FeederBoard:
    """Represents each board in a chain of boards. Boards have positions.
    As far as I know, boards cannot be selectively enabled, disabled.
    They are physically addressed."""

    def __init__(self, num_positions=13) -> None:
        self.positions = [BoardPosition() for _ in range(num_positions)]


class FeederController:
    def __init__(self, port_name, num_boards=1, model="PandaPlacerSlotFeederv2") -> None:
        self.port_name = port_name
        self.model = model
        self.boards = [FeederBoard() for _ in range(num_boards)]
        self.serial_port = self.open_serial_port(port_name)
        self._enabled = False

        self.command_callbacks = {}
        self.command_callbacks["M115"] = self.handle_m115_response

        # Register a serial port cleanup routine at exit.
        atexit.register(self.close_serial_port)

        self.open_serial_port()

        
    def open_serial_port(self, port_name):
        try:
            serial_port = serial.Serial(port=port_name,
                                        baudrate=19200,
                                        bytesize=8,
                                        parity=serial.PARITY_NONE,
                                        stopbits=serial.STOPBITS_ONE,
                                        timeout=1)

            logging.info(f"Serial port {self.port_name} opened successfully.")
            # Request firmware info on successful connection
            self.request_firmware_info()
        except serial.SerialException as e:
            print(f"Failed to open serial port {self.port_name}: {e}")
            self.serial_port = None
        
    def close_serial_port(self):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
                print("Serial port closed.")
            except Exception as e:
                print(f"Failed to close serial port {self.port_name}: {e}")

    def register_command_callback(self, command, callback):
        """Registers a callback function for a specific command"""
        if not callable(callback):
            raise ValueError("Callback must be a callable function.")
        self.command_callbacks[command] = callback

    def send_command(self, command, response_type=None):
            if not self.serial_port or not self.serial_port.is_open:
                print("Serial port not open.")
                return

            try:
                self.serial_port.write(command.encode('utf-8'))
                logging.info(f"Sent command: {command}")

                # Read all data until timeout or newline character
                response = self.serial_port.readline().decode('utf-8').strip()
                if response:
                    # Call the registered callback, if available. Otherwise, handle as generic.
                    if command in self.command_callbacks:
                        self.command_callbacks[command](response)
                    else:
                        self.generic_callback(response, response_type)
                else:
                    logging.warning("No response received before timeout.")
            except serial.SerialException as e:
                    logging.error(f"Failed to send command {command}: {e}")

    def request_firmware_info(self):
        self.send_command("M115", "M115")   # Register a specific callback
                   
    def handle_m115_response(self, response):
        """Parses the M115 response for firmware and hardware versions."""
        logging.info("We're in the M115 response now.")
        result = {}
        firmware_info_pattern = r"FIRMWARE_VERSION:(?P<firmware>[^ ]+) HW_VERSION:(?P<hardware>.+)"
        matches = re.finditer(firmware_info_pattern, response, re.IGNORECASE)
        # Compile results into a list of tuples if any matches are found
        versions = [(match.group("firmware"), match.group("hardware")) for match in matches]
        if versions:
            print("Firmware and Hardware Versions:", versions)
            # Add versions info to the result dictionary
            result.update({"versions": versions})
        else:
            print("No firmware/hardware version info found.")
        return result

    def generic_callback(self, response, response_type=None):
        if not response_type:
            if response.startswith("ok"):
                logging.info("Command successful.")
                return True
            elif response.startswith("error"):
                logging.error(f"Command failed: {response}")
                return False
        
        elif response_type == "M115":
            logging.info("We're in the M115 response now.")
            result = {}
            firmware_info_pattern = r"FIRMWARE_VERSION:(?P<firmware>[^ ]+) HW_VERSION:(?P<hardware>.+)"
            matches = re.finditer(firmware_info_pattern, response, re.IGNORECASE)
            # Compile results into a list of tuples if any matches are found
            versions = [(match.group("firmware"), match.group("hardware")) for match in matches]
            if versions:
                print("Firmware and Hardware Versions:", versions)
                # Add versions info to the result dictionary
                result.update({"versions": versions})
            else:
                print("No firmware/hardware version info found.")
        
            return result