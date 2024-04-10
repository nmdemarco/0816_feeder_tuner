def parse_m620_lines(lines):
  """Parses lines containing M620 commands and returns a dictionary.

  Args:
      lines: A list of strings containing the M620 command lines.

  Returns:
      A dictionary where keys are board_position (e.g., 'N100') and values are
      dictionaries containing the parsed parameters with meaningful names.
  """
  data = {}
  for line in lines:
    if not line.startswith("M620"):
      continue
    board_addr, *params = line.split()[1:]
    board, position = board_addr.split("N")
    position = int(position) * 100

    # Define parameter names and corresponding indices in params list
    param_names = ["advance_angle", "half_advance_angle", "retract_angle",
                   "feed_length", "settle_time", "pulsewidth_at_0", "pulsewidth_at_180",
                   "ignore_feedback_pin"]
    params_dict = {name: float(value) for name, value in zip(param_names, params[:len(param_names)])}

    # Extract boolean value for ignore_feedback_pin
    params_dict["ignore_feedback_pin"] = int(params[-1]) == 1

    data[f"N{position}"] = params_dict
  return data

# Example usage
lines = [
    "BoardAddr:0",
    "M620 N0 A180 B125 C56 F4 U480 V500 W2500 X1",
    "M620 N1 A180 B125 C56 F4 U480 V500 W2500 X1",
    # ... other lines
]

parsed_data = parse_m620_lines(lines)
print(parsed_data)


def parse_m621_output(data):
  """Parses the output from the M621 command and returns a list of dictionaries.

  Args:
      data: A string containing the output from the M621 command.

  Returns:
      A list of dictionaries, where each dictionary represents a position
      for a single board.
  """

  boards = []
  current_board = {}
  for line in data.splitlines():
    if line.startswith("BoardAddr:"):
      # Start of a new board section
      if current_board:
        boards.append(current_board)
      current_board = {"board_id": int(line.split(":")[1])}
    elif line.startswith("ok"):
      # End of a board section
      if current_board:
        boards.append(current_board)
      current_board = {}
    elif line.startswith("M620"):
      # Position data for the current board
      match = re.match(r"^M620 N(\d+) ([A-Z])(.*)$", line)
      if match:
        position = int(match.group(1))
        param_code = match.group(2)
        param_value = match.group(3).split()
        current_board.setdefault("positions", {})[position] = {
            "param_code": param_code,
            "param_value": param_value,
        }

  return boards

# Example usage
data = """
M621

BoardAddr:0

M620 N0 A180 B125 C56 F4 U480 V500 W2500 X1

M620 N1 A180 B125 C56 F4 U480 V500 W2500 X1

... (other board data)

M620 N12 A180 B125 C56 F4 U480 V25 W2500 X1

M620 N12 A180 B125 C56 F4 U480 V500 W2500 X1  # Invalid data (duplicate position)

ok [BoardAddr:0]

BoardAddr:2

... (other board data)

ok [BoardAddr:2]

... (data for other boards)

BoardAddr:4

M620 N412 A180 B125 C56 F4 U480 V500 W2500 X1

ok [BoardAddr:4]
"""

parsed_boards = parse_m621_output(data)
print(parsed_boards)
