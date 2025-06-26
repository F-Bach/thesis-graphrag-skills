import base64
import hashlib
import json
import os
import pandas as pd
from dotenv import load_dotenv
import getpass
from pathlib import Path
from Crypto.Cipher import AES # type: ignore
from Crypto.Random import get_random_bytes # type: ignore

# Load the .env file
load_dotenv()

def encrypt_string(data: str, password: str) -> str:
    # Convert string to bytes
    plain = data.encode("utf-8")
    # Add padding
    padding_length = 16 - len(plain) % 16
    padding = b"\0" * padding_length
    padded_plain = plain + padding
    # Generate key from password
    key = hashlib.sha256(password.encode("utf-8")).digest()
    # Generate random IV
    iv = get_random_bytes(16)
    # Encrypt
    aes = AES.new(key, AES.MODE_CBC, iv)
    cipher = aes.encrypt(padded_plain)
    # Combine IV, padding length, and cipher
    encrypted_data = iv + padding_length.to_bytes(length=1) + cipher
    return base64.b64encode(encrypted_data).decode("utf-8")

def find_name_recursively(data):
    """Recursively search for 'final name' and return its value."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "final name" and isinstance(value, str):
                return value
            elif isinstance(value, (dict, list)):
                result = find_name_recursively(value)
                if result:
                    return result
    elif isinstance(data, list):
        for item in data:
            result = find_name_recursively(item)
            if result:
                return result
    return None

def find_and_replace_name(data, original_name, new_id):
    """Find and replace 'final name' and its occurrences in 'concatenated_summary'."""
    if isinstance(data, dict):
        for key, value in list(data.items()):
            if key == "final name" and value == original_name:
                data[key] = new_id
            elif key == "concatenated_summary" and isinstance(value, str):
                data[key] = value.replace(original_name, new_id)
            elif isinstance(value, (dict, list)):
                find_and_replace_name(value, original_name, new_id)
    elif isinstance(data, list):
        for item in data:
            find_and_replace_name(item, original_name, new_id)

def process_json_files(input_folder: str, output_folder: str, password: str, spain_names_path: str):
    """
    Process all JSON files, encrypt 'final name' and update 'concatenated_summary',
    and save to the output folder.
    """
    try:
        names_df = pd.read_csv(spain_names_path)
        name_list = names_df.iloc[:, 0].dropna().unique().tolist()
        name_iterator = iter(name_list)
        print(f"Successfully loaded and shuffled {len(name_list)} unique names.")
    except FileNotFoundError:
        print(f"Error: The file '{spain_names_path}' was not found.")
        return
    except Exception as e:
        print(f"Error reading or processing CSV file: {e}")
        return

    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)
    json_files = list(input_path.glob("*.json"))

    if not json_files:
        print(f"No JSON files found in {input_folder}")
        return

    processed_count, error_count, file_counter = 0, 0, 1
    id_mapping = {}

    try:
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                original_name = find_name_recursively(data)

                if original_name:
                    new_id_name = next(name_iterator)
                    long_id = encrypt_string(original_name, password)
                    id_mapping[new_id_name] = long_id
                    
                    find_and_replace_name(data, original_name, new_id_name)

                    filename = f"{file_counter}.json"
                    output_file = output_path / filename
                    
                    for info in ["personal_information", "company_information","technical_skills", "programming_languages", "work_experience", "education", "languages", "additional_information"]:
                        if info in data:
                            del data[info]

                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    processed_count += 1
                    file_counter += 1
                    print(f"Processed: {json_file.name} -> {filename}")
                else:
                    print(f"Warning: No 'final name' found in {json_file.name}")

            except json.JSONDecodeError as e:
                print(f"Error parsing JSON file {json_file.name}: {e}")
                error_count += 1
            except StopIteration:
                print("Error: Ran out of unique names from the CSV file. Aborting.")
                raise
            except Exception as e:
                print(f"Error processing file {json_file.name}: {e}")
                error_count += 1
    finally:
        mapping_file_path = Path("../deanonymized/mapping.json")
        mapping_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(mapping_file_path, 'w', encoding='utf-8') as f:
            json.dump(id_mapping, f, indent=2, ensure_ascii=False)
        print(f"\nID mapping saved to: {mapping_file_path}")
        print("\nProcessing complete:")
        print(f"Successfully processed: {processed_count} files")
        print(f"Errors encountered: {error_count} files")
        print(f"Anonymized files saved to: {output_folder}")

def get_encryption_password():
    password = os.getenv('ENCRYPTION_PASSWORD')
    if not password:
        password = getpass.getpass("Enter encryption password: ")
    if len(password) < 16:
        raise ValueError("Password must be at least 16 characters long")
    return password

if __name__ == "__main__":
    try:
        INPUT_FOLDER = "../processed"
        OUTPUT_FOLDER = "output/anonymized"
        SPAIN_NAMES_CSV = "../spain_names.csv"
        encryption_password = get_encryption_password()
        process_json_files(INPUT_FOLDER, OUTPUT_FOLDER, encryption_password, SPAIN_NAMES_CSV)
    except ValueError as e:
        print(f"Password error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
