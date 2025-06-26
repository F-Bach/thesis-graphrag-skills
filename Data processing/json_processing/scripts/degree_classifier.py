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
    field_of_study: str = Field(description="Field of study or major", default="")
    institution: str = Field(description="Institution name")
    start_year: int = Field(description="Year when education started")
    end_year: Union[int, str, None] = Field(description="Year when education ended")
    description: str = Field(description="Education description", default="")
    
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

class StandardizedEducation(BaseModel):
    """Model for the final standardized education output"""
    standardized_degrees: List[str] = Field(description="List of full standardized degree names with field of study")

class CVData(BaseModel):
    """Model for the complete CV data matching your JSON structure"""
    personal_information: PersonalInformation = Field(default_factory=PersonalInformation)
    technical_skills: TechnicalSkills = Field(default_factory=TechnicalSkills)
    work_experience: List[Dict] = Field(default=[])
    education: List[Education] = Field(default=[])
    languages: List[Language] = Field(default=[])
    company_information: Dict = Field(default={})
    additional_information: str = Field(default="")

def process_cv_education(json_file_path: str, use_llm: bool = True) -> List[str]:
    """
    Process CV education and return full standardized degree names with field of study
    
    Args:
        json_file_path: Path to the JSON file containing CV data
        use_llm: Whether to use LLM for intelligent processing (default: True)
        
    Returns:
        List of full standardized degree names
    """
    
    # Read and parse the JSON file
    with open(json_file_path, 'r') as file:
        cv_data = json.load(file)
    
    # Validate the input data
    cv = CVData(**cv_data)
    
    if use_llm:
        return _process_education_with_llm(cv)
    else:
        return _process_education_manually(cv)

# In case the use of LLMs doesn't work
def _process_education_manually(cv: CVData) -> List[str]:
    """Manual rule-based education processing"""
    
    # Define degree standardization mapping
    degree_mapping = {
        'bachelor': 'Bachelor', 'ba': 'Bachelor', 'bs': 'Bachelor', 'bsc': 'Bachelor',
        'beng': 'Bachelor', 'bed': 'Bachelor', 'llb': 'Bachelor', 'bfa': 'Bachelor',
        'bba': 'Bachelor', 'bcom': 'Bachelor',
        'master': 'Master', 'ma': 'Master', 'ms': 'Master', 'msc': 'Master',
        'mba': 'Master', 'med': 'Master', 'mres': 'Master', 'mphil': 'Master',
        'llm': 'Master', 'meng': 'Master',
        'doctor': 'Doctorate', 'phd': 'Doctorate', 'ph.d': 'Doctorate',
        'doctorate': 'Doctorate', 'edd': 'Doctorate', 'ed.d': 'Doctorate',
        'dba': 'Doctorate', 'jd': 'Doctorate', 'j.d.': 'Doctorate',
        'md': 'Doctorate', 'm.d.': 'Doctorate'
    }
    
    # University keywords for filtering
    university_keywords = [
        'university', 'college', 'institute', 'school of', 'academy',
        'polytechnic', 'tech', 'state university'
    ]
    
    exclude_keywords = [
        'high school', 'secondary school', 'grammar school', 'training center', 'bootcamp'
    ]
    
    standardized_degrees = []
    
    for edu in cv.education:
        # Check if it's a university institution
        institution_lower = edu.institution.lower()
        is_university = any(keyword in institution_lower for keyword in university_keywords)
        should_exclude = any(keyword in institution_lower for keyword in exclude_keywords)
        
        if not is_university or should_exclude:
            continue
        
        # Standardize degree
        degree_lower = edu.degree.lower().strip()
        standardized_degree = None
        
        for key, value in degree_mapping.items():
            if key in degree_lower:
                standardized_degree = value
                break
        
        if standardized_degree and edu.field_of_study:
            # Format as "Bachelor of (...)", "Master of (...)", "Doctorate in (...)"
            if standardized_degree == "Bachelor":
                full_degree = f"Bachelor of {edu.field_of_study}"
            elif standardized_degree == "Master":
                full_degree = f"Master of {edu.field_of_study}"
            elif standardized_degree == "Doctorate":
                full_degree = f"Doctorate in {edu.field_of_study}"
            
            standardized_degrees.append(full_degree)
    
    # Remove duplicates while preserving order
    return list(dict.fromkeys(standardized_degrees))

def _process_education_with_llm(cv: CVData) -> List[str]:
    """Process education using LangChain and Azure OpenAI"""
    
    # Initialize Azure OpenAI
    llm = AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("OPENAI_API_VERSION"),
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        temperature=0
    )
    
    # Create the prompt template for education processing
    prompt_template = PromptTemplate(
        input_variables=["cv_json"],
        template="""
        You are an expert at analyzing education data and standardizing academic credentials.
        
        CRITICAL RULES - Follow these exactly:
        1. STANDARDIZE degree formats to: "Bachelor of [Field]", "Master of [Field]", or "Doctorate in [Field]"
        2. INCLUDE ONLY university-level education (exclude high schools, training centers, bootcamps)
        3. EXTRACT the field of study and combine with standardized degree level
        4. REMOVE DUPLICATES from the final list
        
        CV Data:
        {cv_json}
        
        DEGREE STANDARDIZATION RULES:
        - Bachelor degrees (BA, BS, BSc, BEng, BEd, LLB, BFA, BBA, BCom) → "Bachelor of [Field]"
        - Master degrees (MA, MS, MSc, MBA, MEd, MRes, MPhil, LLM, MEng) → "Master of [Field]"  
        - Doctoral degrees (PhD, EdD, DBA, JD, MD) → "Doctorate in [Field]"
        
        UNIVERSITY FILTERING:
        Include ONLY institutions with these keywords:
        - university, college, institute, school of, academy, polytechnic, tech
        
        Exclude institutions with these keywords:
        - high school, secondary school, grammar school, training center, bootcamp
        
        FIELD OF STUDY EXTRACTION:
        - Extract the subject area from degree titles
        - Clean up field names (e.g., "Computer Science", "Business Administration", "Physics")
        - Handle cases where field is in degree name or separate field
        
        EXAMPLE INPUT:
        - "Bachelor of Science in Computer Science" from "MIT University"
        - "High School Diploma" from "Central High School"
        - "Master of Business Administration" from "Harvard Business School"
        - "PhD in Physics" from "Stanford University"
        
        CORRECT OUTPUT:
        {{
            "standardized_degrees": ["Bachelor of Computer Science", "Master of Business Administration", "Doctorate in Physics"]
        }}
        
        FORMAT REQUIREMENTS:
        - Return ONLY a JSON object with "standardized_degrees" array
        - Use format: "Bachelor of [Field]", "Master of [Field]", "Doctorate in [Field]"
        - Remove duplicates from the list
        - Return ONLY the JSON object, no explanatory text
        - DO NOT include high school or non-university education
        
        Now process the education data and return the full standardized degree names:
        """
    )
    
    # Convert CV to JSON string
    cv_json = cv.model_dump_json(indent=2)
    
    # Set up the output parser
    parser = JsonOutputParser(pydantic_object=StandardizedEducation)
    
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
        return result.get("standardized_degrees", [])
    except Exception as e:
        print(f"LLM processing failed: {e}")
        return _process_education_manually(cv)

# Example usage and testing
if __name__ == "__main__":
    # Process the provided JSON file
    import os
    
    # Get all JSON file names from the json folder
    json_folder = '../json'
    output_folder = '../output_degree'
    
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
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
            output_file = f'{output_folder}/{name}_standardized_degrees.json'
            
            print(f"\nProcessing CV education for {name}...")
            
            try:
                degrees = process_cv_education(json_file, use_llm=True)
                
                # Print results
                print(f"Standardized Degrees: {degrees}")
                
            except FileNotFoundError:
                print(f"Error: File {json_file} not found!")
            except Exception as e:
                print(f"Error processing {name}: {e}")
            
            print("-" * 50)
