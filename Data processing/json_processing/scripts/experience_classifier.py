import os
import json
from typing import List, Dict, Optional, Union
from pydantic import BaseModel, Field, field_validator, ValidationInfo
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough

# Load environment variables
load_dotenv()

class WorkExperience(BaseModel):
    """Model for individual work experience entry"""
    current: bool = Field(description="Whether this is the current position")
    position: str = Field(description="Job title/position")
    company: str = Field(description="Company name")
    start_year: int = Field(description="Year when the position started")
    end_year: Union[int, str, None] = Field(description="Year when the position ended (can be empty string, None, or int)")
    description: str = Field(description="Job description")
    
    @field_validator('end_year', mode='before')
    @classmethod
    def validate_end_year(cls, v):
        """Convert empty strings to None and ensure proper type"""
        if v == "" or v is None:
            return None
        return int(v) if isinstance(v, str) and v.isdigit() else v

class TechnicalSkills(BaseModel):
    """Model for technical skills section"""
    tech_skills: List[str] = Field(default=[])
    programming_languages: Dict[str, List[str]] = Field(default={})

class PersonalInformation(BaseModel):
    """Model for personal information"""
    first_name: str = Field(default="")
    last_name: str = Field(default="")
    email: str = Field(default="")

class Education(BaseModel):
    """Model for education entry"""
    current: bool = Field(description="Whether this education is current")
    degree: str = Field(description="Degree name")
    institution: str = Field(description="Institution name")
    start_year: int = Field(description="Year when education started")
    end_year: Union[int, str, None] = Field(description="Year when education ended")
    description: str = Field(description="Education description")
    
    @field_validator('end_year', mode='before')
    @classmethod
    def validate_end_year(cls, v):
        if v == "" or v is None:
            return None
        return int(v) if isinstance(v, str) and v.isdigit() else v

class Language(BaseModel):
    """Model for language entry"""
    language: str = Field(description="Language name")
    level: str = Field(description="Proficiency level")

class CVData(BaseModel):
    """Model for the complete CV data matching your JSON structure"""
    personal_information: PersonalInformation = Field(default_factory=PersonalInformation)
    technical_skills: TechnicalSkills = Field(default_factory=TechnicalSkills)
    work_experience: List[WorkExperience] = Field(description="List of work experiences")
    education: List[Education] = Field(default=[])
    languages: List[Language] = Field(default=[])
    company_information: Dict = Field(default={})
    additional_information: str = Field(default="")

class ConsolidatedExperience(BaseModel):
    """Model for the final output"""
    consolidated_roles: Dict[str, str] = Field(description="Dictionary mapping role to years of experience")

def process_cv_experience(json_file_path: str, use_llm: bool = False) -> Dict[str, str]:
    """
    Process CV work experience and consolidate roles by seniority level
    
    Args:
        json_file_path: Path to the JSON file containing CV data
        use_llm: Whether to use LLM for intelligent consolidation (default: False)
        
    Returns:
        Dictionary with consolidated roles and their total experience
    """
    
    # Read and parse the JSON file
    with open(json_file_path, 'r') as file:
        cv_data = json.load(file)
    
    cv = CVData(**cv_data)
    
    if use_llm:
        return _process_with_llm(cv)
    else:
        return _process_manually(cv)

# In case the use of LLMs doesn't work
def _process_manually(cv: CVData) -> Dict[str, str]:
    """Manual rule-based processing"""
    
    # Dictionary to store role mappings and experience
    role_experience = {}
    role_levels = {}
    
    # Define seniority levels (higher number = more senior)
    seniority_map = {
        'trainee': 1, 'intern': 1, 'apprentice': 1,
        'junior': 2, 'jr': 2, 'associate': 2,
        'mid': 3, 'middle': 3, 'intermediate': 3,
        'senior': 4, 'sr': 4,
        'lead': 5, 'team lead': 5,
        'principal': 6, 'staff': 7, 'architect': 8,
        'director': 9, 'vp': 10, 'cto': 11
    }
    
    for i, exp in enumerate(cv.work_experience):
        # Skip if position is empty or just whitespace
        if not exp.position or exp.position.strip() == "":
            continue
            
        # Calculate years of experience
        end_year = exp.end_year if exp.end_year else 2025
        years = max(0, end_year - exp.start_year)
        
        if years == 0:
            continue
        
        # Extract base role and seniority
        position_lower = exp.position.lower().strip()
        
        # Find seniority level
        seniority_level = 0
        seniority_word = ""
        for level, value in seniority_map.items():
            if level in position_lower:
                if value > seniority_level:
                    seniority_level = value
                    seniority_word = level
        
        # Extract base role (remove seniority words)
        base_role = position_lower
        for level in seniority_map.keys():
            base_role = base_role.replace(level, "").strip()
        
        # Clean up the base role
        base_role = " ".join(base_role.split())
        
        # If base role is empty after cleaning, use original position
        if not base_role:
            base_role = position_lower
        
        # Update experience and level tracking
        if base_role not in role_experience:
            role_experience[base_role] = 0
            role_levels[base_role] = (seniority_level, seniority_word)
        
        role_experience[base_role] += years
        
        # Update to highest seniority level
        if seniority_level > role_levels[base_role][0]:
            role_levels[base_role] = (seniority_level, seniority_word)
    
    # Create final output
    result = {}
    for base_role, total_years in role_experience.items():
        seniority_level, seniority_word = role_levels[base_role]
        
        if seniority_word and seniority_word != base_role:
            final_role = f"{seniority_word}_{base_role}".replace(" ", "_")
        else:
            final_role = base_role.replace(" ", "_")
        
        result[final_role] = f"{total_years} years"
    
    return result

def _process_with_llm(cv: CVData) -> Dict[str, str]:
    """Process using LangChain and Azure OpenAI with full CV context"""
    
    # Initialize Azure OpenAI
    llm = AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("OPENAI_API_VERSION"),
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        temperature=0
    )
    
    # Create the prompt template for full CV processing
    prompt_template = PromptTemplate(
        input_variables=["cv_json"],
        template="""
        You are an expert at analyzing work experience data and consolidating roles by their base function.
        
        CRITICAL RULES - Follow these exactly:
        1. IDENTIFY the base role (e.g., "Data Scientist", "Data Analyst", "Software Engineer")
        2. GROUP all variations of the same base role together regardless of seniority level
        3. SUM all years across ALL seniority levels for each base role
        4. USE ONLY the HIGHEST seniority level achieved as the final role name
        5. DO NOT create separate entries for different seniority levels of the same role
        
        CV Data:
        {cv_json}
        
        STEP-BY-STEP PROCESS:
        Step 1: Extract base roles by removing seniority words (trainee, junior, senior, lead, etc.)
        Step 2: Group experiences by base role
        Step 3: Sum total years for each base role group
        Step 4: Determine highest seniority level achieved for each base role
        Step 5: Create final consolidated entry using highest seniority + base role
        
        EXAMPLE CONSOLIDATION:
        Input:
        - Junior Data Scientist: 1 year
        - Senior Data Scientist: 1 year  
        - Data Analyst Trainee: 1 year
        - Junior Data Analyst: 1 year
        
        Correct Output:
        {{
            "senior_data_scientist": "2 years",
            "junior_data_analyst": "2 years"
        }}
        
        WRONG Output (DO NOT DO THIS):
        {{
            "junior_data_scientist": "1 year",
            "senior_data_scientist": "1 year",
            "data_analyst_trainee": "1 year",
            "junior_data_analyst": "1 year"
        }}
        
        FORMAT REQUIREMENTS:
        - Use lowercase with underscores (e.g., "senior_data_scientist")
        - Format as "X years" or "X year" for singular
        - Return ONLY the JSON object, no explanatory text
        
        SENIORITY HIERARCHY (highest to lowest):
        director > principal > staff > architect > lead > senior > mid > junior > associate > trainee/intern
        
        Now process the work experiences and return the consolidated JSON:
        """
    )
    
    # Convert CV to JSON string
    cv_json = cv.model_dump_json(indent=2)
    
    # Set up the output parser
    parser = JsonOutputParser(pydantic_object=ConsolidatedExperience)
    
    # Create the chain
    chain = (
        {"cv_json": lambda x: x["cv_json"]}
        | prompt_template
        | llm
        | parser
    )
    
    # Execute the chain
    try:
        result = chain.invoke({"cv_json": cv_json})
        return result
    except Exception as e:
        print(f"LLM processing failed: {e}")
        return _process_manually(cv)


# Example usage and testing
if __name__ == "__main__":
    # Process the provided JSON file
    import os
    
    # Get all JSON file names from the json folder
    json_folder = '../json'
    if os.path.exists(json_folder) and os.path.isdir(json_folder):
        json_files = [f for f in os.listdir(json_folder) if f.endswith('.json')]
        json_names = [os.path.splitext(f)[0] for f in json_files]
    else:
        print(f"Error: Folder '{json_folder}' does not exist!")
        json_names = []
    
    if not json_names:
        print("No JSON files found in the json folder!")
    else:
        print(f"Found {len(json_names)} JSON files: {json_names}")
        
        # Process each JSON file
        for name in json_names:
            json_file = f'../json/{name}.json'
            
            print(f"\nProcessing CV experience for {name}...")
            
            try:
                result = process_cv_experience(json_file, use_llm=True)
                
                print("Consolidated Experience:")
                print(json.dumps(result, indent=2))
            except FileNotFoundError:
                print(f"Error: File {json_file} not found!")
            except Exception as e:
                print(f"Error processing {name}: {e}")
            
            print("-" * 50)
