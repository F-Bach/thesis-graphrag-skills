
import json
import os
from datetime import datetime

# La única clave (en minúsculas) que se buscará para reemplazar "Present"
KEY_FOR_PRESENT_REPLACEMENT = "end_year"

def modify_value_in_json_if_present(data_item, target_key, replacement_value_int):
    """
    Función recursiva para modificar el valor de una clave específica a 'replacement_value_int' (entero)
    si su valor actual es "Present" (insensible a mayúsculas/minúsculas).
    Modifica los datos en el lugar.
    """
    if isinstance(data_item, dict):
        for key, value in data_item.items():
            if str(key).lower() == target_key.lower() and \
               isinstance(value, str) and \
               value.strip().lower() == "present":
                data_item[key] = replacement_value_int  # Almacenar como entero
            elif isinstance(value, (dict, list)):
                modify_value_in_json_if_present(value, target_key, replacement_value_int)
    elif isinstance(data_item, list):
        for i, item in enumerate(data_item):
            if isinstance(item, (dict, list)):
                modify_value_in_json_if_present(item, target_key, replacement_value_int)

def find_name_fields_in_section(section_data):
    """
    Busca recursivamente first_name y last_name en una sección específica del JSON.
    Retorna una tupla (first_name, last_name) o (None, None) si no los encuentra.
    """
    first_name = None
    last_name = None
    
    def _recursive_search(data):
        nonlocal first_name, last_name
        
        if isinstance(data, dict):
            # Buscar directamente en este nivel
            if "first_name" in data and isinstance(data["first_name"], str) and data["first_name"].strip():
                first_name = data["first_name"].strip()
            if "last_name" in data and isinstance(data["last_name"], str) and data["last_name"].strip():
                last_name = data["last_name"].strip()
            
            # Si ya encontramos ambos, no necesitamos seguir buscando
            if first_name and last_name:
                return
            
            # Buscar recursivamente en subcampos
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    _recursive_search(value)
                    if first_name and last_name:
                        return
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    _recursive_search(item)
                    if first_name and last_name:
                        return
    
    _recursive_search(section_data)
    return first_name, last_name

def get_name_from_json(data):
    """
    Obtiene first_name y last_name del JSON siguiendo esta prioridad:
    1. Buscar primero en company_information (y sus subcampos)
    2. Si no los encuentra, buscar en personal_information
    
    Retorna una tupla (first_name, last_name)
    """
    first_name = None
    last_name = None
    
    # Primero buscar en company_information
    company_info = data.get("company_information")
    if company_info:
        first_name, last_name = find_name_fields_in_section(company_info)
    
    # Si no encontramos ambos nombres en company_information, buscar en personal_information
    if not (first_name and last_name):
        personal_info = data.get("personal_information")
        if personal_info:
            personal_first, personal_last = find_name_fields_in_section(personal_info)
            
            # Usar los valores de personal_information para llenar los que faltan
            if not first_name:
                first_name = personal_first
            if not last_name:
                last_name = personal_last
    
    return first_name, last_name

def flatten_json(data, parent_key='', sep='_'):
    """
    Flattens a nested JSON/dictionary into a single-level dictionary.
    Nested keys are concatenated with sep (default '_').
    """
    items = {}
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            items.update(flatten_json(v, new_key, sep=sep))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
            items.update(flatten_json(v, new_key, sep=sep))
    else:
        items[parent_key] = data
    return items

def flat_dict_to_string(flat_dict, pair_sep=';', kv_sep='='):
    """
    Converts a flat dictionary into a string with key=value pairs separated by pair_sep.
    """
    return pair_sep.join(f"{k}{kv_sep}{v}" for k, v in flat_dict.items())



def process_jsons_and_add_fields(input_folder, output_folder, string_separator=". "):
    """
    Lee todos los archivos JSON en la carpeta de entrada, y para cada archivo JSON:
    1.  Modifica los datos JSON en memoria: si una clave es "end_year" y su valor es
        "Present", lo cambia por el año actual como un entero.
    2.  Crea un nuevo archivo JSON en la carpeta de salida.
    3.  Este nuevo archivo JSON contiene los datos modificados y tiene:
        a.  Una clave adicional llamada "concatenated_string_with_keys".
        b.  Una clave adicional llamada "name" (concatenación de first_name y last_name).
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Carpeta de salida creada: '{output_folder}'")

    files_processed = 0
    files_failed = 0
    
    # Obtener el año actual como entero
    current_year_int = datetime.now().year

    for filename in os.listdir(input_folder):
        if filename.endswith(".json"):
            input_filepath = os.path.join(input_folder, filename)
            output_filepath = os.path.join(output_folder, filename)

            try:
                with open(input_filepath, 'r', encoding='utf-8') as infile:
                    data = json.load(infile)

                # 1. Modificar los datos JSON en el lugar, usando el año como entero
                modify_value_in_json_if_present(data, KEY_FOR_PRESENT_REPLACEMENT, current_year_int)

                # 2. Concatenar todas las cadenas y números relevantes
                flat_dict = flatten_json(data)
                concatenated_value = flat_dict_to_string(flat_dict, pair_sep=';', kv_sep='=')
                data["concatenated_string_with_keys"] = concatenated_value

                # 3. Añadir el campo "name" usando la nueva lógica de prioridad
                first_name, last_name = get_name_from_json(data)
                
                name_parts = []
                if first_name:
                    name_parts.append(first_name)
                if last_name:
                    name_parts.append(last_name)
                
                data["final name"] = " ".join(name_parts)

                # Escribir el JSON modificado (con "Present" reemplazado por un entero en campos primarios)
                with open(output_filepath, 'w', encoding='utf-8') as outfile:
                    json.dump(data, outfile, indent=4, ensure_ascii=False)

                print(f"Archivo procesado correctamente: '{filename}'")
                files_processed += 1

            except Exception as e:
                print(f"Error al procesar el archivo '{filename}': {e}")
                files_failed += 1

    print(f"\n--- Resumen de la conversión ---")
    print(f"Archivos .json totales encontrados: {files_processed + files_failed}")
    print(f"Convertidos correctamente: {files_processed}")
    print(f"No se pudo convertir: {files_failed}")
    if files_failed > 0:
        print("Por favor, comprueba la salida de la consola para ver los detalles del error en los archivos fallidos.")