import logging
import json

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
   
    _feeders = None     # feeders is a singleton.
    _ephemeral_keys = ['_current_angle', '_enabled']  # Class variable for excluding ephemeral keys in functions.
   
    def __init__(self, id, model=None, body_width=None, tape_width=None,
                 min_pitch=None, advance_angle=None, half_advance_angle=None,
                 retract_angle=None, default_feed_length=None, settle_time=None,
                 min_pulsewidth=None, max_pulsewidth=None, feedback_monitored=None) -> None:
        self.id = id
        self.model = model
        self.body_width = body_width
        self.tape_width = tape_width
        self.min_pitch = min_pitch
        self._advance_angle = advance_angle
        self._half_advance_angle = half_advance_angle
        self._retract_angle = retract_angle
        self._default_feed_length = default_feed_length
        self._settle_time = settle_time   # TODO: Determine the units. Is this in ms, seconds, ?
        self._min_pulsewidth = None    
        self._max_pulsewidth = None
        self._feedback_monitored = False
        self._current_angle = None   # This angle is not persistent
        self._enabled = False   # This state is not persistent

        # Initialize values using the setters
        if advance_angle is not None:
            self._advance_angle = advance_angle
        if half_advance_angle is not None:
            self._half_advance_angle = half_advance_angle
        if retract_angle is not None:
            self._retract_angle = retract_angle
        if default_feed_length is not None:
            self._default_feed_length = default_feed_length
        if settle_time is not None:
            self._settle_time = settle_time
        if min_pulsewidth is not None:
            self._min_pulsewidth = min_pulsewidth
        if max_pulsewidth is not None:
            self._max_pulsewidth = max_pulsewidth
        if feedback_monitored is not None:
            self._feedback_monitored = feedback_monitored
    

    def to_dictionary(self):
        '''Convert a feeder to a dictionary, excluding ephemeral attributes.'''
        # List of attributes to exclude
        exclude_keys = ['_current_angle', '_enabled']
        # Use a dictionary comprehension to filter out excluded attributes
        return {key.lstrip('_'): value for key, value in vars(self).items() if key not in Feeder._ephemeral_keys}


    @classmethod
    def from_dictionary(cls, data):
        '''Create a feeder instance from a dictionary. Exclude ephemeral attributes.'''
        feeder = cls(**data)
        return feeder
    
    @classmethod
    def clone_feeder(cls, current_feeder_id, new_feeder_id):
        # Does the new_feeder_id already exist?
        existing_feeder = next(feeder for feeder in cls._feeders if feeder.id == new_feeder_id), None
        if existing_feeder is not None:
            logging.warning(f"Cannot clone to {new_feeder_id} becuase this ID already exists.")
            return None
        
        feeder_to_clone = next((feeder for feeder in cls._feeders if feeder.id == current_feeder_id), None)
        
        if feeder_to_clone and not feeder_to_clone is None:
            feeder_dict = feeder_to_clone.to_dictionary()
            feeder_dict['id'] = new_feeder_id  # Update the ID for the clone

            cloned_feeder = cls.from_dictionary(feeder_dict)
            cls._feeders.append(cloned_feeder)
            print(f"Feeder with ID {current_feeder_id} cloned to new feeder ID {new_feeder_id}.")
            # Save the feeder list to capture the new clone.
            Feeder.save_to_json()
        else:
            print(f"Cannot clone. No source feeder found with ID {current_feeder_id}.")

    @classmethod
    def list_feeders(cls, exclude_columns=None):
        """Lists all feeders in the singleton feeders list, optionally excluding some columns."""
        
        if cls._feeders is None:
            logging.error("No feeders loaded.")

        if exclude_columns is None:
            exclude_columns = ["_current_angle", "_enabled"]

        # Define all possible columns
        all_columns = ["id", "model", "body_width", "tape_width", "min_pitch", "advance_angle", "half_advance_angle", "retract_angle", "default_feed_length", "settle_time"]

        # Filter out excluded columns
        columns = [col for col in all_columns if col not in exclude_columns]

        # Determine the maximum width for each column
        column_widths = {col: len(col) for col in columns}

        for feeder in cls._feeders:
            feeder_info = feeder.to_dictionary()
            for col in columns:
                column_widths[col] = max(column_widths[col], len(str(feeder_info.get(col, ''))))

        # Create the header row
        header_row = "Idx " + " | ".join(f"{col:{column_widths[col]}}" for col in columns)
        print(header_row)
        print("-" * len(header_row))  # Separator line

        # Print each feeder's details in a row
        for index, feeder in enumerate(cls._feeders, start=1):
            feeder_info = feeder.to_dictionary()
            row = f"{index:<3} " + " | ".join(f"{str(feeder_info.get(col, '')):{column_widths[col]}}" for col in columns)
            print(row)

    @classmethod
    def delete_feeder(cls, feeder_id):
        """Deletes a feeder."""
        feeder_to_delete = next((feeder for feeder in cls._feeders if feeder.id == feeder_id), None)
        


    @staticmethod
    def _normalize_angle(angle):
        return int(angle % 360)  # Normalize angle to be within 0-359 degrees.
    
    def adjust_angle(self, _new_angle):
        '''Adjust the feeder's servo angle based on the provided input string.'''

        if self._current_angle is None: # Initialize
            self._current_angle = 180

        try:
            # Is this a relative move?
            if _new_angle.startswith(("+", "-")):
                _relative_adjustment = int(_new_angle)
                _new_angle = Feeder._normalize_angle(self._current_angle + _relative_adjustment)
            else:
                # Nope. This is an absolute move.
                _new_angle = Feeder._normalize_angle(_new_angle)
            
            return _new_angle

        except ValueError:
            print("Invalid angle. enter a valid angle (0-360, or +/- for relative adjustment).")

    @classmethod
    def select_feeder_by_index(cls):
        """Select a feeder by its index as printed by list_feeders"""

        try:
            index = int(input("Enter the feeder index to select: ")) - 1
            if 0 <= index < len(cls._feeders):
                selected_feeder = cls._feeders[index]
                return selected_feeder
            else:
                print(f"Invalid index. Please enter an index number.")
        except ValueError:
            logging.warning("Invalid input. Enter a numeric value.")
        return None
    
    
    @classmethod
    def load_from_json(cls, filename="feeders.json"):
        """Load feeders from a JSON file, ensuring only one instance exists."""
        if cls._feeders is None:
            try:
                with open(filename, 'r') as file:
                    feeders_data = json.load(file)
                cls._feeders = [cls.from_dictionary(f_data) for f_data in feeders_data]

            except FileNotFoundError:
                logging.info(f"File {filename} not found.")
                cls._feeders = []

            except json.JSONDecodeError as e:
                logging.error(f"Error decoding JSON from {filename}: {e}")
                cls._feeders = []
        return cls._feeders
    
    @classmethod
    def save_to_json(cls, filename="feeders.json"):
        """Save all feeders to a JSON file."""
        if cls._feeders is None or len(cls._feeders) == 0:
            logging.info("No feeders to save.")
            return
        
        feeders_data = [feeder.to_dictionary() for feeder in cls._feeders]

        try:
            with open(filename, 'w') as file:
                json.dump(feeders_data, file, indent=4)
            logging.info(f"Saved {len(feeders_data)} feeders to {filename}")
        except Exception as e:
            logging.error(f"An error occurred while saving feeders to {filename}: {e}")

# def enable_feeder(state=True):
#     """Enable or disable all feeders."""
#     if not enable:
#         send_command("M611 S1", handle_ok_response)
#         _feeder_enabled = enable
#     else:
#         send_command("M611 S0", handle_ok_response)
#     print("Feeders enabled." if enable else "Feeders disabled.")
