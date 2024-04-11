import serial
import time


def open_serial_port(port_name):
    """Opens a serial port and returns the serial object.

    Args:
        port_name (str): The name of the serial port (e.g., "COM5").

    Returns:
        serial.Serial: The serial object if successful, None otherwise.
    """
    try:
        return serial.Serial(port=port_name, baudrate=19200, timeout=0.1)
    except serial.SerialException as e:
        print(f"Failed to open serial port {port_name}: {e}")
        return None


def main_loop(ser):
    """Sends messages (M codes) and reads responses from the serial port.

    Args:
        ser (serial.Serial): The serial object.
    """
    for i in range(1000):
        message = f"M{i:03}\n"
        ser.write(message.encode())

        response = ""  # Initialize empty string to store complete response
        while True:
            time.sleep(0.01)  # Wait for a short period for additional data
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting).decode()
                response += data  # Append received data to the response string
            else:
                break

        # Print only if response is not empty and contains "Invalid M code"
        if response and "Invalid M code" in response:
            print(f"{message.strip()} - response: {response.strip()}")
        else:
            print(f"{message} - timeout" if not response else f"{message} - response: {response.strip()}")


if __name__ == "__main__":
    port = "COM5"

    ser = open_serial_port(port)
    if ser:
        try:
            main_loop(ser)
        finally:
            ser.close()
    else:
        print("Exiting due to serial port error")
