import logging
import sys
import msvcrt
import feeder_controller
from feeder import Feeder
import json


######
## TODO: select a position as part of the main menu.
## Add the ability to assign a feeder to a position.
## Pass the position to the JOG MODE.
## Pass the feeder to JOG MODE.
## Persist the feeder changes each time the JOG MODE changes are updated.




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


def command_mode(feeder):
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





def select_feeder(feeder_list):
    """Select a feeder from the list of available feeders. Return the FeederID"""
    Feeder.list_feeders()

    try:
        selection = int(input("Enter the number of the feeder to select: ")) -1
        if 0 <= selection < len(feeder_list):
            select_feeder = feeder_list[selection]
            feeder_id = select_feeder.id
            logging.info(f"Feeder ID {feeder_id} selected.")
            return feeder_id
        else:
            print("Invalid selection. Please enter a number from the list.")
            return None
        
    except ValueError:
        logging.error("Invalid input. Enter a numeric value.")
        return None
    
    
def clone_feeder(source_feeder_id):
    """Requests a new feeder ID, then confirms the clone from the selected feeder ID to the new ID."""
    
    new_feeder_id = input(f"Cloning feeder {source_feeder_id}. Enter new feeder ID: ")
    Feeder.clone_feeder(source_feeder_id, new_feeder_id)

def delete_feeeder(source_feeder_id):
    pass
    """Lists feeders, then prompts for the feeder to delete. After confirmation, permanently deletes the feeder."""
    Feeder.list_feeders()
    Feeder.delete_feeder(feeder_id)

def main_menu(feeder_controller):

    feeder_id = None

    print(f"Feeder connected on port {feeder_controller.port_name}")


    while True:
        append_feeder_info = f" - {feeder_id} is selected." if feeder_id else ""
        print(f"\nMain Menu{append_feeder_info}")
        print("1. List feeders")  
        print("2. Select feeder by ID")
        print("3. Clone selected feeder")
        print("4. *Select position")
        print("5. *Enable (/disable) all feeders")
        print("6. *Activate (/deactivate) selected feeder")
        print("7. Jog feeder servo arm")
        print("8. Assign feeder to position")
        print("9. Import feeder controller data")
        print("0. Exit")
        choice = input("Enter your choice: ")
        print("\n")

        if choice == "2":   # Select feeder
            Feeder.list_feeders()
            print("\n")
            selected_feeder = Feeder.select_feeder_by_index()
            if selected_feeder is not None:
                feeder = selected_feeder
                feeder_id = selected_feeder.id
                print(feeder)
        elif choice == "3": # Clone feeder
            Feeder.clone_feeder(feeder_id)
        elif choice == "3": #
            pass
        elif choice == "4": #
            pass
        elif choice == "6": #
            pass
        elif choice == "1": # List feeders
            Feeder.list_feeders()
        elif choice == "7": # Jog feeder
            command_mode(feeder)
        elif choice == "8": # Assign feeder to position
            pass
        elif choice == "9": # Import feeder controller data
            pass
        elif choice == "0": # Exit
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 8.")


if __name__ == "__main__":
    feeder_controller = feeder_controller.import_feeder_controller_config()
    if feeder_controller:
        main_menu(feeder_controller)
    else:
        logging.warning("No feeder controller configuration found. Exiting.")