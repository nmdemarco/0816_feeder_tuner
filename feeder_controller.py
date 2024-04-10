import serial
import atexit
import time


class BoardPosition:
    def __init__(self, advance_angle=None, half_advance_angle=None,
                 retract_angle=None, default_feed_length=None, settle_time=None,
                 enabled=False):
        self._current_angle = None  # Transient value, not persisted
        self.advance_angle = advance_angle
        self.half_advance_angle = half_advance_angle
        self.retract_angle = retract_angle
        self.default_feed_length = default_feed_length
        self.settle_time = settle_time
        self._enabled = enabled
        self.feeder = None

    def update_angle(self, new_angle):
        self._current_angle = new_angle


    # Methods to CRUD feeders to a position
    def assign_feeder(self, feeder):
        self.feeder = feeder

    def remove_feeder(self):
        self.feeder = None

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
        self.serial_port = self.open_serial_port(port_name)
        self.model = model
        self.boards = [FeederBoard() for _ in range(num_boards)]
        self._enabled = False

    def open_serial_port(self, port_name):
        try:
            serial_port = serial.Serial(port=port_name, baudrate=19200,
                                        bytesize=8,
                                        parity=serial.PARITY_NONE,
                                        stopbits=serial.STOPBITS_ONE,
                                        timeout=1)
            atexit.register(self.close_serial_port)
            print(f"COM port {port_name} opened successfully.")
            return serial_port
        except serial.SerialException as e:
            print(f"Failed to open COM port {port_name}: {e}")
            return None

    def close_serial_port(self):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
                print("Serial port closed.")
            except Exception as e:
                print(f"Failed to close serial port {self.port_name}: {e}")
        else: print(f"Serial port {self.port_name} is already closed or is not initialized.")

    def send_command(self, command, response_callback):
            if not self.serial_port or not self.serial_port.is_open:
                print("Serial port not open.")
                return

            try:
                self.serial_port.write(command.encode('utf-8'))
                # Wait for the response
                time.sleep(0.1)
                response = self.serial_port.readline().decode('utf-8').strip()
                if response:
                    response_callback(response)
                else:
                    print("No response received before timeout.")
            except serial.SerialException as e:
                print(f"Failed to send command {command}: {e}")

    def handle_response(self, response):
        # TODO: FIgure out what else is sent in the responses, and return that for case-by-case handling per command.
        if re.match(r"^ok.*", response):
            return True
        elif re.match(r"^error.*", response):
            return False