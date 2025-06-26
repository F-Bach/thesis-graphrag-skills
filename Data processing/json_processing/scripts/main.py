import os
import json
from datetime import datetime
from dotenv import load_dotenv

from flatten_jsons import get_name_from_json, modify_value_in_json_if_present
from experience_classifier import process_cv_experience
from degree_classifier import process_cv_education
from flatten_jsons import KEY_FOR_PRESENT_REPLACEMENT

load_dotenv()

def extract_manager_information(data):
    """Extract manager information from company_information section"""
    manager_info = []
    company_info = data.get("company_information", {})
    
    # Look for manager-related fields
    for key, value in company_info.items():
        if "manager" in key.lower() or "supervisor" in key.lower() or "boss" in key.lower():
            if isinstance(value, str) and value.strip():
                manager_info.append(f"{key}: {value}")
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, str) and sub_value.strip():
                        manager_info.append(f"{key}_{sub_key}: {sub_value}")
    
    return manager_info

def extract_languages(data):
    """Extract languages information"""
    languages = data.get("languages", [])
    language_list = []
    
    # Get languages
    for lang in languages:
        if isinstance(lang, dict):
            language_name = lang.get("language", "")
            level = lang.get("level", "")
            if language_name:
                if level:
                    language_list.append(f"{language_name} {level}")
                else:
                    language_list.append(language_name)
        elif isinstance(lang, str):
            language_list.append(lang)
    
    return language_list

def extract_degrees(data):
    """Extract education degrees"""
    education = data.get("education", [])
    degrees = []
    
    # Get education
    for edu in education:
        if isinstance(edu, dict):
            degree = edu.get("degree", "")
            if degree:
                degrees.append(f"{degree}")
    
    return degrees

def extract_tech_skills(data):
    """Extract technical skills"""
    tech_skills = data.get("technical_skills", {})
    skills_list = []
    
    # Get general tech skills
    general_skills = tech_skills.get("tech_skills", [])
    if isinstance(general_skills, list):
        skills_list.extend(general_skills)
    
    return skills_list

def extract_programming_languages(data):
    """Extract programming languages"""
    tech_skills = data.get("technical_skills", {})
    prog_langs = tech_skills.get("programming_languages", {})

    # Get programming language categories (keys)
    prog_lang_keys = list(prog_langs.keys()) if isinstance(prog_langs, dict) else []
    
    # Get detailed packages (current output format)
    packages_list = []
    
    if isinstance(prog_langs, dict):
        for category, languages in prog_langs.items():
            if isinstance(languages, list):
                for lang in languages:
                    if isinstance(lang, str):
                        packages_list.append(f"{lang} ({category})")
            elif isinstance(languages, str):
                packages_list.append(f"{languages} ({category})")
    
    return prog_lang_keys, packages_list

def create_concatenated_string(name, experience_output, languages, degrees, tech_skills, programming_languages):
    """Create concatenated string with specified fields"""
    parts = []

    if name:
        parts.append("Name: " + name)
    
    # Add experience output
    if experience_output:
        exp_parts = []
        for role, years in experience_output.items():
            exp_parts.append(f"{role}: {years}")
        if exp_parts:
            parts.append("Experience: " + ", ".join(exp_parts))    
    
    # Add languages
    if languages:
        parts.append("Languages: " + ", ".join(languages))
    
    # Add degrees
    if degrees:
        parts.append("Education: " + ", ".join(degrees))
    
    # Add tech skills
    if tech_skills:
        parts.append("Technical Skills: " + ", ".join(tech_skills))
    
    # Add programming languages
    if programming_languages:
        parts.append("Programming Languages: " + ", ".join(programming_languages[0]))
        parts.append("Programming Language Packages: " + ", ".join(programming_languages[1]))
    
    return " | ".join(parts)

if __name__ == "__main__":
    current_year_int = datetime.now().year
    
    # Get all JSON file names from the json folder
    json_folder = '../json_complete'
    output_folder = '../processed'
    
    if os.path.exists(json_folder) and os.path.isdir(json_folder):
        json_files = [f for f in os.listdir(json_folder) if f.endswith('.json')]
        json_names = [os.path.splitext(f)[0] for f in json_files]
    else:
        json_names = []
    
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Process each JSON file
    for name in json_names:
        json_file = f'{json_folder}/{name}.json'
        output_file = f'{output_folder}/{name}_processed.json'
        
        try:
            # Read the original JSON file
            with open(json_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # Step 1: Modify "Present" values to current year
            modify_value_in_json_if_present(data, KEY_FOR_PRESENT_REPLACEMENT, current_year_int)
            
            # Step 2: Process CV experience
            experience_output = process_cv_experience(json_file, use_llm=True)
            
            # Add experience output to the data
            data["processed_experience"] = experience_output

            # Step 3: Process CV education
            education_output = process_cv_education(json_file, use_llm=True)
            
            # Add experience output to the data
            data["processed_education"] = education_output

            # Step 4: Final name
            first_name, last_name = get_name_from_json(data)
                
            name_parts = []
            if first_name:
                name_parts.append(first_name)
            if last_name:
                name_parts.append(last_name)
            
            data["final name"] = " ".join(name_parts)
            
            # Step 5: Extract required information for concatenated string
            languages = extract_languages(data)
            degrees = extract_degrees(data)
            tech_skills = extract_tech_skills(data)
            programming_languages = extract_programming_languages(data)
            # manager_info = extract_manager_information(data)
            
            # Step 6: Create concatenated string
            concatenated_string = create_concatenated_string(
                data["final name"],
                experience_output, 
                languages, 
                education_output, 
                tech_skills, 
                programming_languages
            )
            
            # Add concatenated string to the data
            data["concatenated_summary"] = concatenated_string

            
            # Step 7: Save the processed JSON file
            with open(output_file, 'w', encoding='utf-8') as outfile:
                json.dump(data, outfile, indent=4, ensure_ascii=False)
            
        except FileNotFoundError:
            pass
        except Exception as e:
            pass
