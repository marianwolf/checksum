import hashlib
import json
import os
import datetime

algorithm="sha256"
def calculate_checksum(file_path, block_size=65536):
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
        print(f"Error: The file '{file_path}' was not found.")
        return None
    except Exception as e:
        print(f"An error occurred with file '{file_path}': {e}")
        return None

if __name__ == "__main__":
    target_directory = '/home/marian/Downloads'
    checksum_file = "log.json"
    log_data = {
        "timestamp": datetime.datetime.now().isoformat(timespec='milliseconds'),
        "algorithm": algorithm,
        "files": []
    }

    for root, _, files in os.walk(target_directory):
        for file_name in files:
            file_to_check = os.path.join(root, file_name)
            
            if not os.path.isfile(file_to_check):
                continue

            print(f"Checking: {file_to_check}")
            checksum = calculate_checksum(file_to_check)

            if checksum:
                file_entry = {
                    "path": file_to_check,
                    "checksum": checksum,
                }
                log_data["files"].append(file_entry)

    try:
        with open(checksum_file, "w") as json_file:
            json.dump(log_data, json_file, indent=4)
        print(f"All checksums successfully logged to '{checksum_file}'.")
    except Exception as e:
        print(f"An error occurred while writing to file: {e}")