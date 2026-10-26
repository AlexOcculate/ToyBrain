# Line 1:  Import time for timestamping log entries.
import time

# Line 2:  Import typing for type hints.
from typing import List, Dict, Any


# Line 5:  ANSI color codes (no external packages needed).
class C:
    # Line 7:  Reset all formatting back to default.
    RESET = "\033[0m"
    # Line 9:  Bold text for emphasis.
    BOLD = "\033[1m"
    # Line 11:  Red foreground (for errors, guardrails, blocked actions).
    RED = "\033[31m"
    # Line 13:  Green foreground (for success, loop progress).
    GREEN = "\033[32m"
    # Line 15:  Yellow foreground (for warnings, tools).
    YELLOW = "\033[33m"
    # Line 17:  Blue foreground (for info messages).
    BLUE = "\033[34m"
    # Line 19:  Magenta foreground (for planner-related events - not used here but kept for consistency).
    MAGENTA = "\033[35m"
    # Line 21:  Cyan foreground (for wire/network events - THIS module's primary color).
    CYAN = "\033[36m"
    # Line 23:  White foreground.
    WHITE = "\033[37m"
    # Line 25:  Light red background with white text (for BLOCKED/error states).
    BG_RED = "\033[41;97m"
    # Line 27:  Light green background with black text (for valid/success states).
    BG_GREEN = "\033[42;30m"
    # Line 29:  Light yellow background with black text (for warnings/stopped states).
    BG_YELLOW = "\033[43;30m"


# Line 33:  TraceLogger captures and displays colored log entries for the agent's execution.
class TraceLogger:
    # Line 35:  Constructor initializes an empty log buffer.
    def __init__(self):
        # Line 37:  List of (timestamp, color, component, message) tuples.
        self.entries: List[tuple] = []
        # Line 38:  Start time for calculating relative timestamps.
        self.start_time: float = time.time()

    # Line 41:  Log a colored entry with component label.
    def log(self, component: str, message: str, color: str = C.CYAN):
        # Line 43:  Calculate elapsed time since start (for relative timestamps).
        elapsed = time.time() - self.start_time
        # Line 44:  Format the timestamp as seconds with 2 decimal places.
        ts = f"+{elapsed:.2f}s"
        # Line 45:  Store the entry in our buffer.
        self.entries.append((ts, color, component, message))

    # Line 48:  Log a wire-level event (request or response) with cyan coloring.
    def wire(self, message: str):
        # Line 50:  Use cyan color for all wire events (this module's signature color).
        self.log("WIRE", message, C.CYAN)

    # Line 53:  Log a loop control event with green coloring.
    def loop(self, message: str):
        # Line 55:  Use green for loop progression events.
        self.log("LOOP", message, C.GREEN)

    # Line 58:  Log a tool execution event with yellow coloring.
    def tool(self, message: str):
        # Line 60:  Use yellow for tool-related events.
        self.log("TOOL", message, C.YELLOW)

    # Line 63:  Log an error event with red coloring and red background.
    def error(self, message: str):
        # Line 65:  Use red foreground for error messages.
        self.log("ERROR", message, C.RED)

    # Line 68:  Log a success/valid state with green background.
    def success(self, message: str):
        # Line 70:  Use green background for successful operations.
        self.log("OK", message, C.BG_GREEN)

    # Line 73:  Log a warning or stopped state with yellow background.
    def warning(self, message: str):
        # Line 75:  Use yellow background for warnings.
        self.log("WARN", message, C.BG_YELLOW)

    # Line 78:  Print the full colored report of all logged events.
    def report(self):
        # Line 80:  Print a header for the trace report.
        print(f"\n{C.BOLD}{'═' * 70}{C.RESET}")
        # Line 81:  Title the report.
        print(f"{C.BOLD}  EXECUTION TRACE{C.RESET}")
        # Line 82:  Separator line.
        print(f"{C.BOLD}{'═' * 70}{C.RESET}")
        # Line 83:  Iterate through all logged entries and print them colored.
        for ts, color, component, message in self.entries:
            # Line 85:  Format each line with timestamp, colored component tag, and message.
            comp_tag = f"{color}[{component}]{C.RESET}"
            # Line 86:  Print the formatted entry.
            print(f"  {ts}  {comp_tag}  {message}")
        # Line 88:  Print closing separator.
        print(f"{C.BOLD}{'═' * 70}{C.RESET}")

    # Line 91:  Clear all logged entries (useful between test runs).
    def clear(self):
        # Line 93:  Reset the entries list and start time.
        self.entries = []
        # Line 94:  Reset start time for fresh relative timestamps.
        self.start_time = time.time()
