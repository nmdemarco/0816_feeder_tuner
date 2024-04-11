import logging
import sys
import msvcrt
from feeder_controller import FeederController
from feeder import Feeder
import json


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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
            logging.debug(f"Key pressed is: {key}")

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
    print(f"Setting angle to {input_str} (placeholder action)")

def load_feeders_from_json(filename="feeders.json"):
    try:
        with open(filename, 'r') as file:
            feeders_data = json.load(file)
        feeders = [Feeder.from_dictionary(f_data) for f_data in feeders_data]
        return feeders
    except FileNotFoundError:
        logging.info(f"File {filename} not found.")
        return []
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {filename}: {e}")
        return []

def list_feeders(feeders, exclude_columns=None):
    if exclude_columns is None:
        exclude_columns = ["_current_angle", "_enabled"]

    # Define all possible columns
    all_columns = ["id", "model", "body_width", "tape_width", "min_pitch", "_advance_angle", "_half_advance_angle", "_retract_angle", "_default_feed_length", "_settle_time", "_current_angle", "_enabled"]

    # Filter out excluded columns
    columns = [col for col in all_columns if col not in exclude_columns]

    # Determine the maximum width for each column
    column_widths = {col: len(col) for col in columns}

    for feeder in feeders:
        feeder_info = feeder.to_dictionary()
        for col in columns:
            column_widths[col] = max(column_widths[col], len(str(feeder_info.get(col, ''))))

    # Create the header row
    header_row = "Idx " + " | ".join(f"{col:{column_widths[col]}}" for col in columns)
    print(header_row)
    print("-" * len(header_row))  # Separator line

    # Print each feeder's details in a row
    for index, feeder in enumerate(feeders, start=1):
        feeder_info = feeder.to_dictionary()
        row = f"{index:<3} " + " | ".join(f"{str(feeder_info.get(col, '')):{column_widths[col]}}" for col in columns)
        print(row)



def select_feeder(feederList):
    """Select a feeder from the list of available feeders. Return the FeederID"""
    list_feeders(feederList)

    try:
        selection = int(input("Enter the number of the feeder to select: ")) -1
        if 0 <= selection < len(feederList):
            select_feeder = feederList[selection]
            feeder_id = select_feeder.id
            logging.info(f"Feeder ID {feeder_id} selected.")
            return feeder_id
        else:
            print("Invalid selection. Please enter a number from the list.")
            return None
        
    except ValueError:
        logging.error("Invalid input. Enter a numeric value.")
        return None


def load_feeder_controllers_config(file_path='feeder_controllers.json'):
    "Load feeder controller configurations from a JSON file."
    try:
        with open(file_path, 'r') as file:
            feeder_controllers = json.load(file)
            return feeder_controllers
    except FileNotFoundError:
        logging.warn(f"Configuration file {file_path} not found.")
        return []
    except json.JSONDecodeError:
        logging.warning(f"Error decoding JSON from {file_path}")
        return []


def main_menu():

    feeder_controllers_config = load_feeder_controllers_config()
    if feeder_controllers_config:
        # TODO: Should we really initialize the first controller found? Good for most situations, but not all.
        first_controller_config = feeder_controllers_config[0]
        port_name = first_controller_config['port_name']
        feeder_controller = FeederController(port_name)
        logging.info(f"Connected to feeder on {feeder_controller.serial_port.port}.")
    else:
        logging.warning("No feeder controller configuration found. Exiting.")

    feeders = load_feeders_from_json()
    feeder_id = None


    while True:
        append_feeder_info = f" - Current feeder: {feeder_id}" if feeder_id else ""
        print(f"\nMain Menu{append_feeder_info}")
        print("1. Choose feeder by ID")
        print("2. Enable/disable all feeders?")
        print("3. List feeders")
        print("5. Jog feeder servo arm")
        print("0. Exit")
        choice = input("Enter your choice: ")
        print("\n")

        if choice == "1":
            feeder_id = select_feeder(feeders)
        elif choice == "2":
            feeder_controller
        elif choice == "3":
            list_feeders(feeders)
        elif choice == "5":
            command_mode()
        elif choice == "0":
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 8.")


if __name__ == "__main__":

    main_menu()
