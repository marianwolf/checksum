import hashlib
import json
import os
import datetime

algorithm="sha256"
def calculate_checksum(file_path, block_size=12):
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
        print(f"An error occurred: {e}")
        return None

if __name__ == "__main__":
    file_to_check = '/home/marian/Downloads/process_form.php'
    checksum_file = "log.json"
    
    checksum = calculate_checksum(file_to_check)

    if checksum:
        new_checksum_data = {
            "timestamp": datetime.datetime.now().isoformat(timespec='milliseconds'),
            "path": file_to_check,
            "checksum": checksum,
            "algorithm": algorithm,
    }

        existing_data = []
        if os.path.exists(checksum_file) and os.path.getsize(checksum_file) > 0:
            with open(checksum_file, 'r') as f:
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        existing_data = data
                    elif isinstance(data, dict):
                        existing_data.append(data)
                except json.JSONDecodeError:
                    print("Existing file is empty or not a valid JSON. Starting with a new list.")
        
        existing_data.insert(0, new_checksum_data)

        try:
            with open(checksum_file, "w") as json_file:
                json.dump(existing_data, json_file, indent=4)
            print(f"Checksum for '{file_to_check}' successfully prepended to '{checksum_file}'.")
        except Exception as e:
            print(f"An error occurred while writing to file: {e}")