import hashlib
import json
import os
import datetime
import pathlib
import sys

ALGORITHM = "sha256"
BLOCK_SIZE_DEFAULT = 65536
TARGET_DIRECTORY = pathlib.Path('/home/marian/Downloads')
CHECKSUM_FILE = pathlib.Path("log.json")

def calculate_checksum(file_path, block_size=BLOCK_SIZE_DEFAULT):
    """Calculates the checksum of a file using the specified algorithm."""
    try:
        hasher = hashlib.new(ALGORITHM)

        with open(file_path, 'rb') as f:
            while data := f.read(block_size):
                hasher.update(data)

        return hasher.hexdigest()
    except FileNotFoundError:
        print(f"Error: '{file_path}' was not found.", file=sys.stderr)
        return None
    except PermissionError:
        print(f"Error: Permission denied for '{file_path}'. Skipping.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR: An unexpected error occurred with '{file_path}': {e}", file=sys.stderr)
        return None

def read_log(log_path):
    """Reads the existing log file, handling errors and non-list structures."""
    all_logs = []
    if log_path.exists():
        try:
            with open(log_path, "r") as json_file:
                all_logs = json.load(json_file)
            if not isinstance(all_logs, list):
                print(f"WARNING: '{log_path}' is not a list. Starting a new log.")
                all_logs = []
        except json.JSONDecodeError:
            print(f"WARNING: Could not read JSON from '{log_path}'. Starting a new log.")
        except Exception as e:
            print(f"ERROR READING: {e}. Starting a new log.")
    return all_logs

def write_log(log_path, all_logs):
    """Writes the updated log data to the file."""
    try:
        with open(log_path, "w") as json_file:
            json.dump(all_logs, json_file, indent=4)
        print(f"New log entry successfully appended to '{log_path}'.")
    except Exception as e:
        print(f"ERROR WRITING: {e}", file=sys.stderr)

if __name__ == "__main__":
    if not TARGET_DIRECTORY.is_dir():
        print(f"Error: Target directory '{TARGET_DIRECTORY}' does not exist or is not a directory.")
        sys.exit(1)

    log_data = {
        "timestamp": datetime.datetime.now().isoformat(timespec='milliseconds'),
        "algorithm": ALGORITHM,
        "block_size": BLOCK_SIZE_DEFAULT,
        "folder": str(TARGET_DIRECTORY.resolve()),
        "files": []
    }

    for file_to_check in TARGET_DIRECTORY.rglob('*'):
        
        if not file_to_check.is_file():
            continue

        checksum = calculate_checksum(file_to_check)

        if checksum:
            file_entry = {
                "path": str(file_to_check.relative_to(TARGET_DIRECTORY.parent)),
                "checksum": checksum,
            }
            log_data["files"].append(file_entry)
            
    all_logs = read_log(CHECKSUM_FILE)
    all_logs.append(log_data)
    write_log(CHECKSUM_FILE, all_logs)