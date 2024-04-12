import re
import serial
import atexit
import json
import logging
import sys

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

    def __init__(self, board_config):
        self.positions = {}
        for position_id, position_data in board_config["positions"].items():
            self.positions[int(position_id)] = BoardPosition(
                feeder_id=position_data.get("feeder_id", None),
                advance_angle=position_data.get("advance_angle", 120),
                half_advance_angle=position_data.get("half_advance_angle", 60),
                retract_angle=position_data.get("retract_angle", 45),
                default_feed_length=position_data.get("default_feed_length", 4),
                settle_time=position_data.get("settle_time", 200)
            )



class FeederController:
    """
    
    BambooFeederController commands:
    M621 - return all position configurations
    M621 Bx where x is a board ID - returns all position configurations for one board.
    M575 - get current baudrate
    M575 Bx where x is (4800,9600,19200,38400,57600,115200) - changes the baud rate
    
    """
    def __init__(self, config_file="feeder_controller.json"):
        """Load feeder config info from a JSON file."""
        try:
            with open(config_file, 'r') as file:
                self.config = json.load(file)
                logging.info("Extaccting 'feeder_controller' key.")
                self.controller_config = self.config["feeder_controller"]
                if not self.controller_config:
                    raise KeyError(f"No 'feeder_controller' key found in the {config_file} file.")

                self.model = self.controller_config["model"] 
                self.port_name = self.controller_config["port_name"]
                self.boards = [FeederBoard(board_config) for board_config in self.controller_config["boards"].values()]
                self.serial_port = None
                self._enabled = False
                self.command_callbacks = {}
                self.open_serial_port(self.port_name)
                atexit.register(self.close_serial_port)

        except FileNotFoundError:
            logging.exception(f"Configuration file {config_file} not found.")
            sys.exit(1)
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from file {config_file}: {e}")
            sys.exit(1)
        except KeyError as e:
            logging.error(f"Missing key: {e}")
            sys.exit(1)
        except Exception as e:
            logging.error(f"An unexpected error occurred. {e}")
            sys.exit(1)

    def initialize_feeder_positions(self):
        """Initializes feeder positions based on the JSON configuration file."""

        total_positions_initialized = 0

 
        print(f"Boards contains {len(self.config["feeder_controller"]["boards"].items())} items.")
        for board_id, board_data in self.config["feeder_controller"]["boards"].items():
            board_positions = board_data.get("positions", {})
            for position_id, position_data in board_positions.items():
                position = BoardPosition(
                    advance_angle=position_data.get("advance_angle", 120),
                    half_advance_angle=position_data.get("half_advance_angle", 60),
                    retract_angle=position_data.get("retract_angle", 45),
                    default_feed_length=position_data.get("default_feed_length", 4),
                    settle_time=position_data.get("settle_time", 200)
                )
                self.boards[int(board_id)].positions[int(position_id)] = position
                total_positions_initialized += 1

        logging.info(f"{total_positions_initialized} positions initialized successfully.")

    def open_serial_port(self, port_name):
        try:
            self.serial_port = serial.Serial(port=port_name,
                                        baudrate=19200,
                                        bytesize=8,
                                        parity=serial.PARITY_NONE,
                                        stopbits=serial.STOPBITS_ONE,
                                        timeout=1)

            logging.info(f"Serial port {port_name} opened successfully.")
            self.request_firmware_info()
        except serial.SerialException as e:
            print(f"Failed to open serial port {port_name}: {e}")
            self.serial_port = None
        
    def close_serial_port(self):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
                print("Serial port closed.")
            except Exception as e:
                print(f"Failed to close serial port {self.port_name}: {e}")

    def send_command(self, command, response_type=None):
            if not self.serial_port or not self.serial_port.is_open:
                print("Serial port not open.")
                return

            try:
                full_command = command + '\n'
                self.serial_port.write(full_command.encode('utf-8'))
                logging.info(f"Sent command: {full_command}")
                
                # Read all data until timeout or newline character
                response = self.serial_port.readline().decode('utf-8').strip()
                logging.info(f"Response RRReceived: {response}")

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
        logging.debug("Sent M115 command.")
                   
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
        
     
    def select_feeder(self):
        feeder_id = input("Enter the feeder ID to select: ")
        selected_feeder = next((feeder for feeder in self._feeders if feeder.id == feeder_id), None)
        if selected_feeder is None:
            print(f"No feeder found with ID {feeder_id}.")
        return selected_feeder
    

def import_feeder_controller_config(file_path='feeder_controller.json'):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            controller_data = data.get('feeder_controller')
            if controller_data:
                num_boards = len(controller_data.get('boards', {}))
                feeder_controller = FeederController(
                    port_name=controller_data.get('port_name'),
                    num_boards=num_boards,
                    model=controller_data.get('model')
                )
                
                for board_id, board_data in controller_data.get('boards', {}).items():
                    board = FeederBoard()
                    feeder_controller.boards[int(board_id)] = board
                    
                    for position_id, position_data in board_data.get('positions', {}).items():
                        position = BoardPosition(
                            feeder_id=position_data.get('feeder_id', 'None'),
                            advance_angle=position_data.get('advance_angle', 120),  # Default to 120 if not specified
                            half_advance_angle=position_data.get('half_advance_angle', 60),
                            retract_angle=position_data.get('retract_angle', 45),
                            default_feed_length=position_data.get('default_feed_length', 4.0),
                            settle_time=position_data.get('settle_time', 200)
                        )
                        board.positions[int(position_id)] = position

                return feeder_controller
            else:
                logging.error("No 'feeder_controller' key found in the provided JSON file.")
                return None
    except Exception as e:
        logging.error(f"Failed to load or parse the JSON file: {e}")
        return None

def register_command_callback(controller, command, callback):
    """Registers a callback function for a specific command"""
    if not callable(callback):
        raise ValueError("Callback must be a callable function.")
    controller.command_callbacks[command] = callback

