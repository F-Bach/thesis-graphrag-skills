import base64
import hashlib
import json
import os
from dotenv import load_dotenv
import getpass
from pathlib import Path
from Crypto.Cipher import AES # type: ignore

# Load the .env file
load_dotenv()

def decrypt_string(encrypted_data: str, password: str) -> str:
    # Decode from base64
    encrypted_bytes = base64.b64decode(encrypted_data)
    # Extract components
    iv = encrypted_bytes[:16]
    padding_length = int.from_bytes(encrypted_bytes[16:17])
    cipher = encrypted_bytes[17:]
    # Generate key from password
    key = hashlib.sha256(password.encode("utf-8")).digest()
    # Decrypt
    aes = AES.new(key, AES.MODE_CBC, iv)
    padded_plain = aes.decrypt(cipher)
    # Remove padding
    plain = padded_plain[:-padding_length]
    return plain.decode("utf-8")

def find_id_recursively(data):
    """Recursively search for 'final name' (which holds the ID) and return its value."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "final name" and isinstance(value, str):
                return value
            elif isinstance(value, (dict, list)):
                result = find_id_recursively(value)
                if result:
                    return result
    elif isinstance(data, list):
        for item in data:
            result = find_id_recursively(item)
            if result:
                return result
    return None

def find_and_replace_id(data, short_id, decrypted_name):
    """Find and replace the anonymized ID with the original name."""
    if isinstance(data, dict):
        for key, value in list(data.items()):
            if key == "final name" and value == short_id:
                data[key] = decrypted_name
            elif key == "concatenated_summary" and isinstance(value, str):
                data[key] = value.replace(short_id, decrypted_name)
            elif isinstance(value, (dict, list)):
                find_and_replace_id(value, short_id, decrypted_name)
    elif isinstance(data, list):
        for item in data:
            find_and_replace_id(item, short_id, decrypted_name)

def decrypt_final_name_in_files(input_folder: str, output_folder: str, password: str):
    """
    Decrypt 'final name' and update 'concatenated_summary' in all JSON files
    using the ID mapping file.
    """
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)
    
    mapping_file_path = "../deanonymized/mapping.json"
    try:
        with open(mapping_file_path, 'r', encoding='utf-8') as f:
            id_mapping = json.load(f)
        print(f"Loaded ID mapping from {mapping_file_path}")
    except FileNotFoundError:
        print(f"Error: Mapping file not found at {mapping_file_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from mapping file.")
        return

    json_files = list(input_path.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {input_folder}")
        return

    processed_count, error_count = 0, 0

    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            short_id = find_id_recursively(data)

            if not short_id:
                print(f"Warning: No 'final name' (ID) found to decrypt in {json_file.name}")
                continue

            long_id = id_mapping.get(short_id)
            if not long_id:
                print(f"Error: Short ID {short_id} not found in mapping for file {json_file.name}.")
                error_count += 1
                continue
            
            try:
                decrypted_name = decrypt_string(long_id, password)
                find_and_replace_id(data, short_id, decrypted_name)
                
                output_file = output_path / json_file.name
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                processed_count += 1
                print(f"Decrypted: {json_file.name} -> {json_file.name}")

            except Exception as e:
                print(f"Failed to decrypt ID {short_id} for file {json_file.name}: {e}")
                error_count += 1

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON file {json_file.name}: {e}")
            error_count += 1
        except Exception as e:
            print(f"Error processing file {json_file.name}: {e}")
            error_count += 1

    print("\nDecryption complete:")
    print(f"Successfully decrypted: {processed_count} files")
    print(f"Errors encountered: {error_count} files")
    print(f"Decrypted files saved to: {output_folder}")

def get_decryption_password():
    password = os.getenv('ENCRYPTION_PASSWORD')
    if not password:
        password = getpass.getpass("Enter decryption password: ")
    if len(password) < 16:
        raise ValueError("Password must be at least 16 characters long")
    return password

if __name__ == "__main__":
    try:
        INPUT_FOLDER = "output/anonymized"
        OUTPUT_FOLDER = "../deanonymized"
        decryption_password = get_decryption_password()
        decrypt_final_name_in_files(INPUT_FOLDER, OUTPUT_FOLDER, decryption_password)
    except ValueError as e:
        print(f"Password error: {e}")
    except Exception as e:
        print(f"Error: {e}")
