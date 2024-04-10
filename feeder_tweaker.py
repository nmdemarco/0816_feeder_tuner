import sys
import msvcrt
from feeder_controller import FeederController
from feeder import Feeder
import json


def print_help():
    immediate_command_help = """
    Jog Controls:
    . - jog cw 1 degree
    , - jog ccw 1 degree
    < > - jog 5 degrees
    < - jog ccw 5 degrees
    o - return to origin (180°)
    F - set current position as full advance
    H - set current position as half advance
    R - set current position as retract angle
    f, h, r - jog to currently set full, half, retract angles
    e - exit jog mode
    Enter numbers directly for absolute angles, prefix with '+' or '-' for relative movement.
    """

    # Display help text.
    print(immediate_command_help)


def adjust_angle(feeder, new_angle):
    '''Adjust the feeder's servo angle based on the provided input string.'''

    if _current_angle is None: # Initialize
        _current_angle = 180

    try:
        # Is this a relative move?
        if new_angle.startswith(("+", "-")):
            relative_adjustment = int(new_angle)
            new_angle = (_current_angle + relative_adjustment) % 360
        else:
            # Nope. This is an absolute move.
            new_angle = int(new_angle) % 360

        send_command(f"M603N{_feeder_address}A{new_angle}", handle_ok_response)
        # TODO: actually re-get the current angle and report it vs. assuming the send_command was successful.
        _current_angle = new_angle  # TODO: When you assume... 
        print(f"Servo angle set to {_current_angle} degrees.")

    except ValueError:
        print("Invalid angle. enter a valid angle (0-360, or +/- for relative adjustment).")

def command_mode():
    """
    Supports interaction with a device through immediate and numeric key-in modes:
    
    - Immediate actions are triggered by single-key inputs, including help, exiting, jogging, 
      and initiating numeric entry for precise control.
      
    - Numeric Entry Mode: Accumulates keypresses into a numeric command, which is executed
      upon pressing Enter. Activated by starting to type numbers, '+' or '-'.

    All modes are exited by pressing 'e','E', or escape. Defaults to Command Mode for single-key commands.
    """

    print("""Command Mode: Use keys to adjust angle. '?' for help, 'e' to exit).
             Enter numbers directly for absolute angles, prefix with '+' or '-' for relative movement.""")

    input_buffer = ""   # Buffer for numeric input
    mode = "immediate"
    exit_keys = {'e', 'E'} # I toyed with adding the escape character b'\x1b'
    immediate_keys = '.,<>ofhrFHR'

    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch().decode('utf-8')
            print(f"Key pressed is: {key}")

            if key.lower() in exit_keys:  # Exit jog mode
                mode = None
                print(f"Exit key ({key}) pressed. Exiting...")
                break

            elif key.lower() == '?':  # Show help
                print_help()

            elif mode == "immediate" and key in immediate_keys:  # Single key commands
                handle_immediate_keys(key)

            elif key.isdigit() or key in '+-':  # Start of numeric input
                    mode = "numeric_entry"
                    input_buffer += key
                    print(f"Angle input: {input_buffer}", end='\r')


            elif mode == "numeric_entry":  # Numeric input mode
                print("We're in numeric entry mode")
                if key == '\r':  # Enter key
                    handle_numeric_input(input_buffer)
                    input_buffer = ""   # Clear buffer
                    mode = "immediate"
                elif key.isdigit() or (key in '+-' and not input_buffer):   # Add pressed key to input_buffer
                    input_buffer += key
                    print(f"Angle input: {input_buffer}", end='\r')
                elif key == '\x08':  # Handle backspace by reducing input_buffer
                    input_buffer = input_buffer[:-1]
                    print(f"Angle input: {input_buffer} ", end='\r')
                else:
                    # TODO: Reprint instructions upon entering immediate mode.
                    print("\nInvalid input. Returning to immediate mode.")
                    input_buffer = ""
                    mode = "immediate"



def handle_immediate_keys(key):
    """Converts immediate keys into angle adjustment values."""
    print(f"Handling immediate key ({key})")

    if key == '.':
        adjust_angle("+1")
    elif key == ',':
        adjust_angle("-1")
    elif key == '>':
        adjust_angle("+5")
    elif key == '<':
        adjust_angle("-5")
    elif key == 'o':
        adjust_angle("180")
    elif key == 'F':
        set_feeder_parameter("full_advance")
    elif key == 'H':
        set_feeder_parameter("half_advance")
    elif key == 'R':
        set_feeder_parameter("retract")
    elif key == 'f':
        set_feeder_parameter("full_advance")
    elif key == 'h':
        set_feeder_parameter("half_advance")
    elif key == 'r':
        print ("handle_immediate_keys - r")


def handle_numeric_input(input_str):
    global _current_angle
    print(f"Setting angle to {input_str} (placeholder action)")



def set_feeder_parameter(key):
    global _current_angle, feeders, _feeder_address

    if key == 'F':
        advance_angle = _current_angle
        print(f"Set full advance angle to {_current_angle}")
    elif key == 'H':
        half_advance_angle = _current_angle
        print(f"Set half advance angle to {_current_angle}")
    elif key == 'R':
        retract_angle = _current_angle
        print(f"Set retract angle to {_current_angle}")
    elif key == 'f':
        adjust_angle(advance_angle)
        print(f"Moved to full advance angle {_current_angle}")
    elif key == 'h':
        adjust_angle(half_advance_angle)
        print(f"Moved to half advance angle {_current_angle}")
    elif key == 'r':
        adjust_angle(retract_angle)
        print(f"Moved to retract angle {_current_angle}")


def select_feeder(feederList):
    """Select a feeder from the list of available feeders"""
    return 1

def load_feeders_from_json(filename="feeders.json"):
    try:
        with open(filename, 'r') as file:
            feeders_data = json.load(file)
        feeders = [Feeder.from_dictionary(f_data) for f_data in feeders_data]
        return feeders
    except FileNotFoundError:
        print(f"File {filename} not found.")
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {filename}: {e}")
        return []



def main_menu():

    if len(sys.argv) > 1:
        port_name = sys.argv[1]
    # else:
    #     print("Specify the communications port as the first argument.")
    #     sys.exit(1)
    else:
        port_name = None

    if port_name:
        feeder_controller = FeederController(port_name)
    else:
        # No serial port was specified. Simulate serial port.
        serial_port = None
        print("No serial port specified on command line. Simulating serial port.")

    feeders = load_feeders_from_json()
    for feeder in feeders:
        print(f"Loaded feeder: {feeder.to_dictionary()}")

    while True:
        print(f"\nMain Menu - Current feeder ID: TODO: FEEDER ID GOES HERE")
        print("1. Choose feeder by ID")
        print("2. Enable/disable all feeders?")
        print("4. Jog feeder servo arm")
        print("8. Exit")
        choice = input("Enter your choice: ")
        if choice == "1":
            feeder1 = Feeder(id="Feeder1", address="000")
        elif choice == "2":
            feeder_controller
        elif choice == "4":
            command_mode()
        elif choice == "8":
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 8.")





if __name__ == "__main__":

    main_menu()
