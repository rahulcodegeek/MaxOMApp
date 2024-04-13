import sys
from datetime import datetime, timezone


# Create a file object to write print statements and errors
class FileLogger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a")

    def write(self, message):
        # Get current UTC time
        utc_now = datetime.now(timezone.utc)
        formatted_time = utc_now.strftime('%m-%d-%Y %H:%M:%S UTC')
        # If the message is not empty, write it along with timestamp
        if message.strip():  # Check if message has any content after stripping whitespace
            self.terminal.write(str(formatted_time) + ": " + str(message) + "\n")
            self.log.write(str(formatted_time) + ": " + str(message) + "\n")
            self.log.flush()  # Ensure the buffer is flushed

    def flush(self):
        pass