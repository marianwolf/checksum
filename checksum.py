import hashlib
import json
import os
import datetime

algorithm="sha256"
block_size_default=65536
def calculate_checksum(file_path, block_size=block_size_default):
    try:
        hasher = hashlib.new(algorithm)

        with open(file_path, 'rb') as f:
            while True:
                data = f.read(block_size)
                if not data:
                    break
                hasher.update(data)

        return hasher.hexdigest()
    except FileNotFoundError:
        print(f"Error: '{file_path}' was not found.")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None

if __name__ == "__main__":
    target_directory = '/home/marian/Downloads'
    checksum_file = "log.json"
    log_data = {
        "timestamp": datetime.datetime.now().isoformat(timespec='milliseconds').replace('T', ' '),
        "algorithm": algorithm,
        "block_size": block_size_default,
        "folder": target_directory,
        "files": []
    }

    for root, _, files in os.walk(target_directory):
        for file_name in files:
            file_to_check = os.path.join(root, file_name)
            
            if not os.path.isfile(file_to_check):
                continue

            checksum = calculate_checksum(file_to_check)

            if checksum:
                file_entry = {
                    "path": file_to_check,
                    "checksum": checksum,
                }
                log_data["files"].append(file_entry)

    all_logs = []
    try:
        if os.path.exists(checksum_file):
            with open(checksum_file, "r") as json_file:
                all_logs = json.load(json_file)
            if not isinstance(all_logs, list):
                print(f"WARNING: '{checksum_file}' is not a list. Starting a new log.")
                all_logs = []
    except json.JSONDecodeError:
        print(f"WARNING: Could not read JSON from '{checksum_file}'. Starting a new log.")
    except Exception as e:
        print(f"ERROR READING: {e}. Starting a new log.")

    all_logs.append(log_data)

    try:
        with open(checksum_file, "w") as json_file:
            json.dump(all_logs, json_file, indent=4)
        print(f"New log entry successfully appended to '{checksum_file}'.")
    except Exception as e:
        print(f"ERROR WRITING: {e}")