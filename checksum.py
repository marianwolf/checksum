import hashlib
import json
import os
import datetime
import pathlib
import sys

ALGORITHM = "sha256"
BLOCK_SIZE_DEFAULT = 65536
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
    try:
        with open(log_path, "w", encoding="utf-8") as json_file:
            json.dump(all_logs, json_file, indent=4, ensure_ascii=False)
        print(f"New log entry successfully appended to '{log_path}'.")
    except Exception as e:
        print(f"ERROR WRITING: {e}", file=sys.stderr)

def build_directory_tree(directory_map):
    root_node = {
        "files": directory_map.get('.', []),
        "children": {} 
    }
    
    children_map = {".": root_node}
    sorted_paths = sorted(directory_map.keys(), key=len)
    
    for full_path in sorted_paths:
        if full_path == '.':
            continue

        path_parts = full_path.split(os.sep)
        node_name = path_parts[-1]
        parent_path = str(pathlib.Path(full_path).parent)
        new_node = {
            "name": node_name,
            "files": directory_map.get(full_path, []),
            "children": {} 
        }
        
        children_map[full_path] = new_node
        
        if parent_path in children_map:
            children_map[parent_path]["children"][node_name] = new_node
        else:
            print(f"WARNING: Could not find parent for path: {full_path}")

    final_tree = root_node
    
    def dict_to_list(node):
        node['subdirectories'] = sorted(list(node.pop('children').values()), key=lambda x: x['name'])
        for child in node['subdirectories']:
            dict_to_list(child)

    dict_to_list(final_tree)
    return final_tree

if __name__ == "__main__":
    while True:
        target_input = input(f"Please enter the path: ")
        TARGET_DIRECTORY = pathlib.Path(target_input)
        
        if not TARGET_DIRECTORY.is_dir():
            print(f"ERROR: The target directory '{TARGET_DIRECTORY}' does not exist or is not a directory.")
        else:
            break
    
    directory_map = {} 
    
    print(f"Starting checksum calculation for: {TARGET_DIRECTORY.resolve()}")

    for file_to_check in TARGET_DIRECTORY.rglob('*'):
        
        if not file_to_check.is_file():
            continue

        checksum = calculate_checksum(file_to_check)

        if checksum:
            file_relative_path = file_to_check.relative_to(TARGET_DIRECTORY)
            directory_path = str(file_relative_path.parent)
            file_name = file_relative_path.name

            if directory_path not in directory_map:
                directory_map[directory_path] = []
            
            file_entry = {
                "name": file_name,
                "checksum": checksum,
            }
            directory_map[directory_path].append(file_entry)

    directory_tree = build_directory_tree(directory_map)
    
    log_data = {
        "timestamp": datetime.datetime.now().isoformat(timespec='milliseconds').replace('T', ' '),
        "algorithm": ALGORITHM,
        "block_size": BLOCK_SIZE_DEFAULT,
        "folder": str(TARGET_DIRECTORY.resolve()),
        "structure": directory_tree
    }
            
    all_logs = read_log(CHECKSUM_FILE)
    all_logs.append(log_data)
    write_log(CHECKSUM_FILE, all_logs)