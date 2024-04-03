import re
import serial
import serial.tools.list_ports
import atexit
import time
import json
import tabulate
import copy


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
        self.model = None
        self.body_width = None    # width in millimeters 
        self.tape_width = None   # tape width in millimeters
        self.min_pitch = None   # component pitch in millimeters
        self.advance_angle = None
        self.half_advance_angle = None
        self.retract_angle = None
        self.default_feed_length = None
        self.settle_time = None
        self.control_min_pulsewidth = None
        self.control_max_pulsewidth = None
        self.feedback_pin_monitored = False

    def to_dictionary(self):
        '''Convert a feeder to a dicctionary'''
        return vars(self)
    
    @classmethod
    def from_dictionary(cls, data):
        '''Create a feeder instance from a dictionary'''
        feeder = cls()
        feeder.__dict__.update(data)
        return feeder

class FeederControl:
    def __init__(self) -> None:
        self.feeder_address = None
        self.feeder_enabled = False
        self.advance_increment = None
        self.servo_angle = 90  # Default to 90 degrees
        self.comm_properties = {"baudrate": 19200, "parity": serial.PARITY_NONE, "stopbits": serial.STOPBITS_ONE, "port": None}
        self.serial_port = None
        self.feeder_names = {}  # Map of feeder names to configurations


    def save_feeders_to_file(self, filename="feeders.json"):
        feeders_data = {name: to_dictionary() for name, feeder in self.feeder_names.items}
        with open(filename, 'w') as file:
            json.dump(feeders_data, file, indent=4)

    def load_feeders_from_file(self, filename="feeders.json"):
        '''Load feeders from a file'''
        try:
            with open(filename, 'r') as file:
                feeders_data = json.load(file)
            for name, data in feeders_data.items():
                self.feeder_names[name] = Feeder.from_dictionary(data)
        except FileNotFoundError:
            print(f"No saved feeders file found ({filename}).")

    def create_new_feeder(self):
        if self.feeder_names:
            copy_id = input("Enter an existing feeder ID to copy from, or press Enter to create a blank new feeder: ")
            if copy_id in self.feeder_names:
                new_feeder = copy.deepcopy(self.feeder_names[copy_id])
                print(f"Copying feeder properties from feeder {copy_id}...")
            else:
                new_feeder = Feeder()
        else:
            new_feeder = Feeder()
            print("Creating a completely new ")
            
        new_feeder.id = input("Enter new feeder ID: ")
        self.feeder_names[new_feeder.id] = new_feeder
        print("New feeder created.")

    def edit_feeder(self, feeder_id=None):
        if feeder_id is None:
            print("Select feeder before choosing this option.")
            return

        if feeder_id not in self.feeder_names:
            print(f"Feeder ID {feeder_id} does not exist.")
            return
        
        feeder = self.feeder_names[feeder_id]
        for key, value in feeder.to_dictionary().items():
            new_value = input(f"{key} [currently: {value}]: ") or value
            setattr(feeder, key, new_value)

        print(f"Feeder {feeder_id} has been updated.")

    def list_feeders(self):
        '''List all loaded feeders using tabulate.'''
        if not self.feeder_names:
            print("No feeders have been loaded.")
            return
        
        # Create a list of feeder property lists.

        feeders_list = []
        for name, feeder in self.feeder_names.items():
            feeders_list.append([
                                feeder.id,
                                feeder.model,
                                feeder.body_width,
                                feeder.tape_width,
                                feeder.min_pitch,
                                feeder.advance_angle,
                                feeder.half_advance_angle,
                                feeder.retract_angle,
                                feeder.default_feed_length,
                                feeder.settle_time,
                                feeder.control_min_pulsewidth,
                                feeder.control_max_pulsewidth,
                                feeder.feedback_pin_monitored
            ])

        # Define headers for the table
        headers = [
            "ID", "Model", "Body width", "Tape width", "Min pitch",
            "Advance angle", "Half advance angle", "Retract angle",
            "Default feed length", "Settle time", "Min pulsewidth",
            "Max pulsewidth", "Feedback pin monitored?" 
        ]

        # Use tabluate to print the table
        print(tabulate(feeders.list, headers = headers))

    def list_serial_ports(self):
        """Lists available serial ports."""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]


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

feeder_control = FeederControl()

# Ensure the serial port is closed when the program exits.
atexit.register(feeder_control.close_serial_port)

def check_feeder():
    """Check if the selected feeder is OK."""
    if feeder_control.feeder_address is None:
        print("No feeder address selected.")
        return
    command = f"M602 N{feeder_control.feeder_address}"
    feeder_control.send_command("M602", handle_ok_response)
    response = "Feeder reports OK"
    if re.match(r"^ok.*", response):
        print("Feeder is OK.")
    else:
        print("Feeder reports an error.")

def enable_disable_feeders(enable=True):
    """Enable or disable all feeders."""
    if not feeder_control.feeder_enabled:
        feeder_control.send_command("M611 S1", handle_ok_response)
        feeder_control.feeder_enabled = enable
    else:
        feeder_control.send_command("M611 S0", handle_ok_response)
    print("Feeders enabled." if enable else "Feeders disabled.")
    
def select_feeder_address():
    """Select a feeder address."""
    address = input("Enter feeder address (e.g., 100 for board 1, index 00): ")
    # Validate and set feeder address
    if re.match(r"^[1-5][0-9]{2}$", address) and 0 <= int(address[1:]) <= 11:
        feeder_control.feeder_address = address
        check_feeder()
    else:
        print("Invalid address. Use a valid board (1-5) and index (0-11).")

def choose_advance_increment():
    """Choose an advance increment."""
    increment = input("Enter advance increment (2-24mm, multiples of 2): ")
    if increment.isdigit() and 2 <= int(increment) <= 24 and int(increment) % 2 == 0:
        feeder_control.advance_increment = int(increment)
        print(f"Advance increment set to {increment}mm.")
    else:
        print("Invalid increment. Enter a value between 2 and 24, in multiples of 2.")

def drive_servo():
    """Drive servo to a specific angle."""
    angle = input(f"Enter angle (0-360, current: {feeder_control.servo_angle}, +/- for relative): ")
    # Normalize and set angle
    try:
        if angle.startswith("+") or angle.startswith("-"):
            feeder_control.servo_angle = (feeder_control.servo_angle + int(angle)) % 360
        else:
            feeder_control.servo_angle = int(angle) % 360
        print(f"Servo angle set to {feeder_control.servo_angle} degrees.")
    except ValueError:
        print("Invalid angle. Enter a valid angle.")


def configure_comm_properties():
    print("Available COM ports:", feeder_control.list_serial_ports())
    port = input("Select COM port: ")
    feeder_control.comm_properties["port"] = port
    feeder_control.open_serial_port()

def main_menu():
    while True:
        current_feeder_id = feeder_control.feeder_address if feeder_control.feeder_address else "None"
        print(f"\nMain Menu - Current feeder ID: {current_feeder_id}")
        print("1. Choose feeder by ID")
        print("2. Enable/Disable all feeders")
        print("3. Choose advance increment")
        print("4. Drive servo to a specific angle")
        print("5. Configure communication properties")
        print("6. Save feeders to file")
        print("7. Load feeders from file")
        print("8. Exit")
        choice = input("Enter your choice: ")
        if choice == "1":
            select_feeder_address()
        elif choice == "2":
            enable_disable_feeders(not feeder_control.feeder_enabled)
        elif choice == "3":
            choose_advance_increment()
        elif choice == "4":
            drive_servo()
        elif choice == "5":
            configure_comm_properties()
        elif choice == "6":
            feeder_control.save_feeders_to_file()
        elif choice == "7":
            feeder_control.load_feeders_from_file()
        elif choice == "8":
            break
        elif choice == "9":
            feeder_control.create_new_feeder()
        elif choice == "10":
            feeder_control.edit_feeder()
        else:
            print("Invalid choice. Please enter a number between 1 and 8.")


if __name__ == "__main__":
    main_menu()
