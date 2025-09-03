import hashlib

def calculate_checksum(file_path, algorithm="sha256", block_size=12):
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
        print(f"The SHA-256 checksum of '{file_to_check}' is:")
        print(checksum)