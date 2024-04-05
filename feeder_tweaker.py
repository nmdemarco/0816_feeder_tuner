import re
import sys
import serial
import serial.tools.list_ports
import atexit
import time
import msvcrt

# Naughty global variables
_feeder_enabled = False
_feeder_address = None
_current_angle = 180    # Default starting and resting angle for servos.
serial_port = None

class Feeder:
    '''
    Each feeder is a separate instance. These are not feeder slots, addresses, or positions.

    Configure feeders using M620 syntax from:
    https://docs.mgrl.de/maschine:pickandplace:feeder:0816feeder:mcodes
        N	Number of Feeder: 0…(NUMBER_OF_FEEDERS-1)
        A	advanced angle, defaults to FEEDER_DEFAULT_FULL_ADVANCED_ANGLE
        B	half advanced angle, defaults to FEEDER_DEFAULT_HALF_ADVANCED_ANGLE
        C	retract angle, defaults to FEEDER_DEFAULT_RETRACT_ANGLE
        F	standard feed length, defaults to FEEDER_DEFAULT_FEED_LENGTH, which is FEEDER_MECHANICAL_ADVANCE_LENGTH,
            which is 4mm usually
        U	settle time to go from advanced angle to retract angle and reverse, defaults to FEEDER_DEFAULT_TIME_TO_SETTLE.
            make sure the servo is fast enough to reach the angles within given settle time
        V	pulsewidth at which servo is at about 0°, defaults to FEEDER_DEFAULT_MOTOR_MIN_PULSEWIDTH
        W	pulsewidth at which servo is at about 180°, defaults to FEEDER_DEFAULT_MOTOR_MAX_PULSEWIDTH
        X	ignore feedback pin, defaults to FEEDER_DEFAULT_IGNORE_FEEDBACK
    '''
    def __init__(self) -> None:
        self.id = None
        # self.model = None
        # self.body_width = None    # width in millimeters 
        # self.tape_width = None   # tape width in millimeters
        # self.min_pitch = None   # component pitch in millimeters
        self.advance_angle = None
        self.half_advance_angle = None
        self.retract_angle = None
        self.default_feed_length = None
        self.settle_time = None
        # The following are advanced configuration parameters
        # self.control_min_pulsewidth = None    
        # self.control_max_pulsewidth = None
        # self.feedback_pin_monitored = False
        self.current_angle = None   # This angle is not persistent

    def to_dictionary(self):
        '''Convert a feeder to a dictionary'''
        feeder_dictionary = vars(self)
        print(feeder_dictionary)

    @classmethod
    def from_dictionary(cls, data):
        '''Create a feeder instance from a dictionary'''
        feeder = cls()
        feeder.__dict__.update(data)
        return feeder

    @staticmethod
    def _normalize_angle(angle):
        return angle % 360  # Normalize angle to be within 0-359 degrees.

    @property
    def advance_angle(self):
        return self.advance_angle

    @advance_angle.setter
    def advance_angle(self, angle):
        self.advance_angle = Feeder.normalize_angle(angle)

    @property
    def half_advance_angle(self):
        return self.half_advance_angle

    @half_advance_angle.setter
    def half_advance_angle(self, angle):
        self.half_advance_angle = Feeder._normalize_angle(angle)

    @property
    def retract_angle(self):
        return self.retract_angle

    @retract_angle.setter
    def retract_angle(self, angle):
        self.retract_angle = Feeder._normalize_angle(angle)

    @property
    def settle_time(self):
        return self.settle_time

    @settle_time.setter
    def settle_time(self, time):
        self.settle_time = time
        # TODO: Add error checking based on acceptable time values in feeder firmware

def open_serial_port(port_name):
    """Open the provided COM port."""
    global serial_port

    if port_name:

        try:
            serial_port = serial.Serial(port=port_name,
                                                baudrate=19200
                                                ,
                                                bytesize=8,
                                                parity=serial.PARITY_NONE,
                                                stopbits=serial.STOPBITS_ONE,
                                                timeout=1)
            print(f"COM port {port_name} opened successfully.")
            return serial_port
        except serial.SerialException as e:
            print(f"Failed to open COM port {port_name}: {e}")
            return
        
    else:
        serial_port = None
        print("Simulating serial port.")

def close_serial_port():
    """Close the open serial port."""

    global serial_port

    # Only close if serial_port is defined, which it isn't if simulating.
    if serial_port and serial_port.is_open:
        serial_port.close()
        print("Serial port closed.")

def send_command(command, response_callback):
    """Send a command to the feeder and handle the response with a callback"""

    global serial_port

    if not serial_port:
        print("No serial port defined. Simulating.")
        return
    elif serial_port.is_open:
        print("Serial port not open.")
        return

    try:
        serial_port.write(command.encode('utf-8'))
        # Wait for the response
        time.sleep(0.5)
        response = serial_port.readline().decode('utf-8').strip()
        if response:
            response_callback(response)
        else:
            print("No response received before timeout.")
    except serial.SerialException as e:
        print(f"Failed to send command {command}: {e}")

def handle_ok_response(response):
    if re.match(r"^ok.*", response):
        print("Operation successful.")
    else:
        print("Unexpected response.", response)

def handle_error_response(response):
    if re.match(r"^error.*", response):
        print("Operation failed.")
    else:
        print("Unexpected response.", response)

# Ensure the serial port is closed when the program exits.
atexit.register(close_serial_port)

# def check_feeder():
#     """Check if the selected feeder is OK."""
#     if _feeder_address is None:
#         print("No feeder address selected.")
#         return
#     command = f"M602 N{_feeder_address}"
#     send_command("M602", handle_ok_response)
#     response = "Feeder reports OK"
#     if re.match(r"^ok.*", response):
#         print("Feeder is OK.")
#     else:
#         print("Feeder reports an error.")

# def enable_disable_feeders(enable=True):
#     """Enable or disable all feeders."""
#     if not enable:
#         send_command("M611 S1", handle_ok_response)
#         _feeder_enabled = enable
#     else:
#         send_command("M611 S0", handle_ok_response)
#     print("Feeders enabled." if enable else "Feeders disabled.")
    
def select_feeder_address():
    """Select a feeder address."""
    global _feeder_address
    address = input("Enter 3-digit feeder address (e.g., 003 for board 0, position 3): ")
    # Validate and set feeder address
    if re.match(r"^[0-4](0[0-9]|1[0-2])$", address):
        _feeder_address = address
        print(f"Feeder address{_feeder_address} selected.")
        # check_feeder()
    else:
        print("Invalid address. Use a board number (0-4) and position (00-12).")


def jog_windows():
    command_mode = True # Start command mode.

    print("Jog Mode: Use keys to adjust angle ('e' to exit, 'h' for help).")
    print("Enter numbers directly for absolute angles, prefix with '+' or '-' for relative movement.")

    input_buffer = ""   # Buffer for numeric input

    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch().decode('utf-8')

            if command_mode:
                if key.lower() == 'e':  # Exit jog mode
                    print("Exiting jog mode.")
                elif key.lower() == 'h':  # Show help
                    print_help()
                elif key in '.,<>ofhrFHR':  # Single key commands
                    handle_command(key)
                elif key.isdigit() or key in '+-':  # Start of numeric input
                        command_mode = False
                        input_buffer += key
                        print(f"Angle input: {input_buffer}", end='\r')
                else:
                    print("Unknown command. Press 'h' for help.")
            else:   # Numeric input mode
                if key == '\r':  # Enter key
                    handle_numeric_input(input_buffer)
                    input_buffer = ""   # Clear buffer
                    command_mode = True # Switch back to command mode
                elif key.isdigit() or (key in '+-' and not input_buffer):
                    input_buffer += key
                    print(f"Angle input: {input_buffer}", end='\r')
                elif key == '\x08':  # Handle backspace
                    input_buffer = input_buffer[:-1]
                    print(f"Angle input: {input_buffer}", end='\r')
                else:
                    print("\nInvalid input. Returning to command mode.")
                    input_buffer = ""
                    command_mode = True

def handle_command(key):
    if key in ['.', ',', '>', '<', 'o', 'F', 'H', 'R', 'f', 'h', 'r']:
        if key == '.':
            adjust_angle("+1")
        elif key == ',':
            adjust_angle("-1")
        elif key == '>':
            adjust_angle("+5")
        elif key == '<':
            adjust_angle("-5")
    elif key.isdigit() or key in ['+', '-']:
        print("Switching to numeric input mode for angle adjustment.")
    else:
        print(f"Unknown command: {key}")


def print_help():
    help_text = """
    Jog Controls:
    . - jog cw 1 degree
    , - jog ccw 1 degree
    > - jog cw 5 degrees
    < - jog ccw 5 degrees
    o - return to origin (180°)
    F - set current position as full advance
    H - set current position as half advance
    R - set current position as retract angle
    f, h, r - jog to currently set full, half, retract angles
    e - exit jog mode
    Enter numbers directly for absolute angles, prefix with '+' or '-' for relative movement.
    """
    print(help_text)


def handle_numeric_input(input_str):
    global _current_angle
    print(f"Setting angle to {input_str} (placeholder action)")


    
def adjust_angle(input_str):
    '''Adjust the servo angle based on the provided input string.'''
    global _current_angle

    if _current_angle is None: # Initialize
        _current_angle = 180

    try:
        if input_str.startswith(("+", "-")):
            relative_adjustment = int(input_str)
            _current_angle = (_current_angle + relative_adjustment) % 360
        else:
            _current_angle = int(input_str) % 360

        send_command(f"M603N{_feeder_address}A{_current_angle}", handle_ok_response)
        print(f"Servo angle set to {_current_angle} degrees.")

    except ValueError:
        print("Invalid angle. enter a valid angle (0-360, or +/- for relative adjustment).")

def main_menu():

    if len(sys.argv) > 1:
        port_name = sys.argv[1]
    # else:
    #     print("Specify the communications port as the first argument.")
    #     sys.exit(1)
    else:
        port_name = None

    if port_name:
        serial_port = open_serial_port(port_name)
    else:
        # No serial port was specified. Simulate serial port.
        serial_port = None
        print("No serial port specified on command line. Simulating serial port.")

    while True:
        current_feeder_id = _feeder_address if _feeder_address else "None"
        print(f"\nMain Menu - Current feeder ID: {current_feeder_id}")
        print("1. Choose feeder by ID")
        print("2. Enable/disable all feeders?")
        print("4. Jog feeder servo arm")
        print("6. Save feeders to file")
        print("7. Load feeders from file")
        print("8. Exit")
        choice = input("Enter your choice: ")
        if choice == "1":
            select_feeder_address()
        elif choice == "2":
            pass
        elif choice == "4":
            jog_windows()
        elif choice == "6":
            print("Function not implemented")
            # save_feeders_to_file()
        elif choice == "7":
            print("Function not implemented")
            # load_feeders_from_file()
        elif choice == "8":
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 8.")


if __name__ == "__main__":

    main_menu()
