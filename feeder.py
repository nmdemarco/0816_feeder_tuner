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
    def __init__(self, id, model=None, body_width=None, tape_width=None,
                 min_pitch=None, advance_angle=None, half_advance_angle=None,
                 retract_angle=None, default_feed_length=None, settle_time=None) -> None:
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
        # The following are advanced configuration parameters
        # self.control_min_pulsewidth = None    
        # self.control_max_pulsewidth = None
        # self.feedback_pin_monitored = False
        self._current_angle = None   # This angle is not persistent
        self._enabled = False   # This state is not persistent

        # Initialize angles using the setters
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

    def to_dictionary(self):
        '''Convert a feeder to a dictionary'''
        return  vars(self)

    @classmethod
    def from_dictionary(cls, data):
        '''Create a feeder instance from a dictionary'''
        return cls(id=data['id'], **{k: v for k, v in data.items() if k != 'id'})


    @property
    def advance_angle(self):
        return self._advance_angle

    @advance_angle.setter
    def advance_angle(self, angle):
        self._advance_angle = Feeder._normalize_angle(angle)

    @property
    def half_advance_angle(self):
        return self._half_advance_angle

    @half_advance_angle.setter
    def half_advance_angle(self, angle):
        self._half_advance_angle = Feeder._normalize_angle(angle)

    @property
    def retract_angle(self):
        return self._retract_angle

    @retract_angle.setter
    def retract_angle(self, angle):
        self._retract_angle = Feeder._normalize_angle(angle)

    @property
    def settle_time(self):
        return self._settle_time

    @settle_time.setter
    def settle_time(self, time):
        self._settle_time = time
        # TODO: Add error checking based on acceptable time values in feeder firmware

    @property
    def default_feed_length(self):
        return self._default_feed_length
    
    @default_feed_length.setter
    def default_feed_length(self, length):
        self._default_feed_length = length

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


def enable_feeder(state=True):
    """Enable or disable all feeders."""
    if not enable:
        send_command("M611 S1", handle_ok_response)
        _feeder_enabled = enable
    else:
        send_command("M611 S0", handle_ok_response)
    print("Feeders enabled." if enable else "Feeders disabled.")
