import sys


# Create a file object to write print statements and errors
class FileLogger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()  # Ensure the buffer is flushed

    def flush(self):
        pass
