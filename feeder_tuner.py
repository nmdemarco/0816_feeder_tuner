import re
import serial
import serial.tools.list_ports
import atexit
import time
import json
import tabulate

# Naughty global variables
_feeder_enabled = False
_feeder_address = None

class Feeder:
    '''
    Each feeder is a separate instance. These are not feeder slots, addresses, or positions.

    Configure feeders using M620 syntax from:
    https://docs.mgrl.de/maschine:pickandplace:feeder:0816feeder:mcodes
        N	Number of Feeder: 0…(NUMBER_OF_FEEDERS-1)
        A	advanced angle, defaults to FEEDER_DEFAULT_FULL_ADVANCED_ANGLE
        B	half advanced angle, defaults to FEEDER_DEFAULT_HALF_ADVANCED_ANGLE
        C	retract angle, defaults to FEEDER_DEFAULT_RETRACT_ANGLE
        F	standard feed length, defaults to FEEDER_DEFAULT_FEED_LENGTH, which is FEEDER_MECHANICAL_ADVANCE_LENGTH, which is 4mm usually
        U	settle time to go from advanced angle to retract angle and reverse, defaults to FEEDER_DEFAULT_TIME_TO_SETTLE. make sure the servo is fast enough to reach the angles within given settle time
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
        '''Convert a feeder to a dicctionary'''
        feeder_dictionary = vars(self)
        print(feeder_dictionary)
        return
    
    @staticmethod
    def _normalize_angle(angle):
        return angle % 360  # Normalize angle to be within 0-359 degrees.

    @classmethod
    def from_dictionary(cls, data):
        '''Create a feeder instance from a dictionary'''
        feeder = cls()
        feeder.__dict__.update(data)
        return feeder
    
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
        self.settle_time = time     # TODO: Add error checking based on acceptable time values in feeder firmware



    # def list_feeders(self):
    #     '''List all loaded feeders using tabulate.'''
    #     if not self.feeder_names:
    #         print("No feeders have been loaded.")
    #         return
        
    #     # Create a list of feeder property lists.

    #     feeders_list = []
    #     for name, feeder in self.feeder_names.items():
    #         feeders_list.append([
    #                             feeder.id,
    #                             feeder.model,
    #                             feeder.body_width,
    #                             feeder.tape_width,
    #                             feeder.min_pitch,
    #                             feeder.advance_angle,
    #                             feeder.half_advance_angle,
    #                             feeder.retract_angle,
    #                             feeder.default_feed_length,
    #                             feeder.settle_time,
    #                             feeder.control_min_pulsewidth,
    #                             feeder.control_max_pulsewidth,
    #                             feeder.feedback_pin_monitored
    #         ])

    #     # Define headers for the table
    #     headers = [
    #         "ID", "Model", "Body width", "Tape width", "Min pitch",
    #         "Advance angle", "Half advance angle", "Retract angle",
    #         "Default feed length", "Settle time", "Min pulsewidth",
    #         "Max pulsewidth", "Feedback pin monitored?" 
    #     ]

    #     # Use tabluate to print the table
    #     print(tabulate(feeders.list, headers = headers))

def open_serial_port(self):
    """Open the selected COM port with the state's comm_properties values."""
    if self.serial_port:
        print("Serial port is already open.")
        return

    port = self.comm_properties["port"]

    if port is None:
        print("No COM port selected. Configure communications properties before attempting to open the port.")
        return

    try:
        self.serial_port = serial.Serial(port=port,
                                            baudrate=self.comm_properties["baudrate"],
                                            parity=self.comm_properties["parity"],
                                            stopbits=self.comm_properties["stopbits"],
                                            timeout=1)
        print(f"COM port {port} opened successfully.")
    except serial.SerialException as e:
        print(f"Failed to open COM port {port}: {e}")

def close_serial_port(self):
    """Close the open serial port."""
    if self.serial_port and self.serial_port.is_open:
        self.serial_port.close()
        print("Serial port closed.")

def send_command(self, command, response_callback):
    """Send a command to the feeder and handle the response with a callback"""
    if not self.serial_port or not self.serial_port.is_open:
        print("Serial port not open.")
        return

    try:
        self.serial_port.write(command.encode('utf-8'))
        # Wait for the response
        time.sleep(0.5)
        response = self.serial_port.readline().decode('utf-8').strip()
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

def check_feeder():
    """Check if the selected feeder is OK."""
    if _feeder_address is None:
        print("No feeder address selected.")
        return
    command = f"M602 N{_feeder_address}"
    send_command("M602", handle_ok_response)
    response = "Feeder reports OK"
    if re.match(r"^ok.*", response):
        print("Feeder is OK.")
    else:
        print("Feeder reports an error.")

def enable_disable_feeders(enable=True):
    """Enable or disable all feeders."""
    if not _feeder_enabled:
        send_command("M611 S1", handle_ok_response)
        _feeder_enabled = enable
    else:
        send_command("M611 S0", handle_ok_response)
    print("Feeders enabled." if enable else "Feeders disabled.")
    
def select_feeder_address():
    """Select a feeder address."""
    address = input("Enter feeder address (e.g., 100 for board 1, index 00): ")
    # Validate and set feeder address
    if re.match(r"^[1-5][0-9]{2}$", address) and 0 <= int(address[1:]) <= 11:
        _feeder_address = address
        check_feeder()
    else:
        print("Invalid address. Use a valid board (1-5) and index (0-12).")


def send_to_angle(current_angle):
    """Command servo to go to a specific angle."""
    angle = input(f"Enter angle (0-360, current: {current_angle}, +/- for relative): ")
    # Normalize and set angle
    try:
        if angle.startswith("+") or angle.startswith("-"):
            commanded_angle = current_angle + int(angle) % 360
        
        else:
            commanded_angle = int(angle) % 360
        
        send_command(f"M603N{_feeder_address}A{commanded_angle}", handle_ok_response)
        print(f"Servo angle set to {current_angle} degrees.")
    except ValueError:
        print("Invalid angle. Enter a valid angle.")

def main_menu():
    while True:
        current_feeder_id = _feeder_address if _feeder_address else "None"
        print(f"\nMain Menu - Current feeder ID: {current_feeder_id}")
        print("1. Choose feeder by ID")
        print("2. Enable/disable all feeders?")
        print("4. Drive servo to a specific angle")
        print("6. Save feeders to file")
        print("7. Load feeders from file")
        print("8. Exit")
        choice = input("Enter your choice: ")
        if choice == "1":
            select_feeder_address()
        elif choice == "2":
            pass
        elif choice == "4":
            send_to_angle()
        elif choice == "6":
            pass
            # save_feeders_to_file()
        elif choice == "7":
            pass
            # load_feeders_from_file()
        elif choice == "8":
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 8.")


if __name__ == "__main__":

    main_menu()
    # open_serial_port("COM5")
