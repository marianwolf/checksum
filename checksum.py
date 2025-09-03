import hashlib, json, time

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

    checksum = calculate_checksum(file_to_check)

    if checksum:
        checksum_data = {
            "time": time.time(),
            "algorithm": algorithm,
            "path": file_to_check,
            "checksum": checksum
        }

        json_output = json.dumps(checksum_data, indent=4)

        print(json_output)

        try:
            with open("checksum.json", "w") as json_file:
                json_file.write(json_output)
            print("Checksum successfully saved to 'checksum.json'")
        except Exception as e:
            print(f"An error occurred while writing to file: {e}")