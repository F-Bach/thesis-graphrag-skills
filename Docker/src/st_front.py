import streamlit as st
import json
from difflib import get_close_matches
from streamlit_modal import Modal
from datetime import datetime
from difflib import get_close_matches

# Load company data loader
from ETL.data_loader import load_data as load_company_data

from storage import connect_to_blob_storage, upload_cv_to_blob

# Page configuration
st.set_page_config(page_title="Technical CV Generator", layout="wide")

# Custom CSS for professional layout
st.markdown(
    """
    <style>
    .cv-container {
       font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
       background-color: #ffffff;
       padding: 30px;
       border-radius: 10px;
       box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
       margin: 20px auto;
       width: 90%;
       max-width: 800px;
    }
    .cv-section {
       margin-bottom: 25px;
    }
    .cv-section h3 {
       border-bottom: 2px solid #2980b9;
       padding-bottom: 5px;
       color: #2980b9;
       margin-bottom: 10px;
    }
    .cv-divider {
       margin: 20px 0;
       border: none;
       border-top: 1px solid #ecf0f1;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Function to load skills from JSON
def load_skills():
    try:
        with open("src/skills.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("SKILLS", {})
    except Exception:
        st.error("Error loading skills configuration.")
        return {}

SKILLS = load_skills()

# Initialize session state
def init_session_state():
    if "education" not in st.session_state:
        st.session_state.education = [{"current": False}]
    if "experience" not in st.session_state:
        st.session_state.experience = [{"current": False}]
    if "languages" not in st.session_state:
        st.session_state.languages = [{}]
    if "company_info" not in st.session_state:
        st.session_state.company_info = {}
    # track confirmed last‐name separately
    if "last_name_selected" not in st.session_state:
        st.session_state.last_name_selected = ""

# Utility for dynamic multiselect input
def create_dynamic_input(key, options, label):
    selected = st.multiselect(
        label=label,
        options=options,
        default=st.session_state.get(f"selected_{key}", []),
        key=f"multiselect_{key}",
        placeholder=f"Select {label}...",
        max_selections=1000,
        accept_new_options=True
    )
    return selected

# Format CV preview HTML
def format_cv_html(cv_data):
    personal = cv_data.get("personal_information", {})
    education = cv_data.get("education", [])
    experience = cv_data.get("work_experience", [])
    skills = cv_data.get("technical_skills", {})
    languages = cv_data.get("languages", [])

    html = "<div class='cv-container'>"
    # Personal
    html += "<div class='cv-section'><h3>Personal Information</h3>"
    html += f"<p><strong>Name:</strong> {personal.get('first_name','')} {personal.get('last_name','')}</p>"
    html += f"<p><strong>Email:</strong> {personal.get('email','')}</p>"
    html += "</div><hr class='cv-divider'>"

    # Education
    html += "<div class='cv-section'><h3>Education</h3>"
    for edu in education:
        deg = edu.get("degree","")
        inst = edu.get("institution","")
        if deg and inst:
            start = edu.get("start_year", "")
            end = edu.get("end_year", "")
            period = f" ({start}–{end})" if start or end else ""
            html += f"<p><strong>{deg}</strong>, {inst}{period}</p>"
    html += "</div><hr class='cv-divider'>"

    # Experience
    html += "<div class='cv-section'><h3>Work Experience</h3>"
    for exp in experience:
        pos = exp.get("position","")
        comp = exp.get("company","")
        start = exp.get("start_year","")
        end = exp.get("end_year","")
        desc = exp.get("description","")
        html += f"<p><strong>{pos}</strong>, {comp} ({start}–{end})<br>{desc}</p>"
    html += "</div><hr class='cv-divider'>"

    # Skills
    html += "<div class='cv-section'><h3>Technical Skills</h3>"
    for cat, vals in skills.items():
        html += f"<p><strong>{cat.replace('_',' ').title()}:</strong> {', '.join(vals)}</p>"
    html += "</div><hr class='cv-divider'>"

    # Languages
    html += "<div class='cv-section'><h3>Languages</h3>"
    for lang in languages:
        name = lang.get("language", "")
        lvl = lang.get("level", "")
        if name:
            html += f"<p><strong>{name}:</strong> {lvl}</p>"
    html += "</div></div>"
    return html

# Show preview modal
def show_modal_preview(cv_data):
    modal = Modal("CV Preview", key="cv_modal")
    with modal.container():
        st.markdown(format_cv_html(cv_data), unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm & Submit CV"):
                st.success("CV submitted!")
                modal.close()
        with col2:
            if st.button("Edit CV"):
                modal.close()

# Main application
def main():
    init_session_state()
    
    st.title("ARD CV Collector")
    # Load company records once\    
    try:
        company_records = load_company_data()
    except Exception as e:
        st.error(f"Failed to load company data: {e}")
        company_records = []

    # Personal Information
    with st.expander("Personal Information", expanded=True):
        # 1) Gather Inputs
        first = st.text_input("First Name", key="first_name")
        last  = st.text_input("Last Name",  key="last_name")
        email = st.text_input("Email",      key="email")

        # 2) Fuzzy‐match full name (threshold 0.8)
        rec = None
        if first and last:
            full_in = f"{first.strip().lower()} {last.strip().lower()}"
            # Build list of “First Last” strings from your records
            candidates = {
                f"{r['first_name'].lower()} {r['last_name'].lower()}": r
                for r in company_records
            }
            # Ask difflib for the closest match
            best = get_close_matches(full_in, candidates.keys(), n=1, cutoff=0.8)
            if best:
                rec = candidates[best[0]]

        # 3) Autocomplete if we found a good match
        if rec:
            st.text_input("TEAMS ID",       value=rec.get("teams_id", ""),    disabled=True, key="teams_id")
            st.text_input("Team",           value=rec.get("team", ""),         disabled=True, key="team")
            st.text_input("Capability Lead",value=rec.get("capability_lead", ""), disabled=True, key="cap_lead")
            st.session_state.company_info = rec
        else:
            st.session_state.company_info = {}

    # Education
    with st.expander("Education"):
        # Display each education entry with delete button
        education_to_remove = -1
        for i, edu in enumerate(st.session_state.education):
            cols = st.columns([1, 1, 1, 1, 0.5, 0.5])
            cols2 = st.columns([1])
            with cols[0]:
                edu["degree"] = st.text_input(f"Degree #{i + 1}", key=f"degree_{i}")
            with cols[1]:
                edu["institution"] = st.text_input(f"Institution #{i + 1}", key=f"institution_{i}")
            with cols[2]:
                edu["start_year"] = st.number_input(
                    f"Start Year #{i + 1}",
                    min_value=1950,
                    max_value=datetime.now().year,
                    value=datetime.now().year,
                    key=f"start_year_{i}"
                )
            with cols[3]:
                edu["end_year"] = st.number_input(
                    f"End Year #{i + 1}",
                    min_value=1950,
                    max_value=datetime.now().year,
                    value=datetime.now().year,
                    key=f"end_year_{i}"
                )
            with cols[4]:
                # Checkbox for current education
                edu["current"] = st.checkbox(f"Currently studying?", key=f"edu_current_{i}")

                if edu["current"]:
                    edu["end_year"] = "Present"

            with cols[5]:
                # Only show delete button if there's more than one entry
                if len(st.session_state.education) > 1:
                    if st.button("🗑️", key=f"del_edu_{i}"):
                        education_to_remove = i
            with cols2[0]:
                edu["description"] = st.text_area(f"Description #{i + 1}", key=f"edu_desc_{i}")
            st.divider()

        # Process education entry removal
        if education_to_remove >= 0:
            st.session_state.education.pop(education_to_remove)
            st.rerun()

        # Add new education entry button
        if st.button("➕ Add Another Degree"):
            st.session_state.education.append({"current": False})
            st.rerun()

    # Work Experience Section
    with st.expander("Work Experience"):
        # Display each work experience entry with delete button
        experience_to_remove = -1
        for i, exp in enumerate(st.session_state.experience):
            cols = st.columns([1, 1, 1, 1, 0.5, 0.5])
            cols2 = st.columns([1])
            with cols[0]:
                exp["position"] = st.text_input(f"Position #{i + 1}", key=f"position_{i}")
            with cols[1]:
                exp["company"] = st.text_input(f"Company #{i + 1}", key=f"company_{i}")
            with cols[2]:
                exp["start_year"] = st.number_input(
                    f"Start Year #{i + 1}",
                    min_value=2000,
                    max_value=datetime.now().year,
                    value=datetime.now().year,
                    key=f"start_{i}"
                )
            with cols[3]:
                exp["end_year"] = st.number_input(
                    f"End Year #{i + 1}",
                    min_value=2000,
                    max_value=datetime.now().year,
                    value=datetime.now().year,
                    key=f"end_{i}"
                )
            with cols[4]:
                # Checkbox for current position
                exp["current"] = st.checkbox(f"Current position?", key=f"exp_current_{i}")
                if exp["current"]:
                    exp["end_year"] = "Present"
            with cols2[0]:
                exp["description"] = st.text_area(f"Description #{i + 1}", key=f"desc_{i}")
            with cols[5]:
                # Only show delete button if there's more than one entry
                if len(st.session_state.experience) > 1:
                    if st.button("🗑️", key=f"del_exp_{i}"):
                        experience_to_remove = i
            st.divider()

        # Process experience entry removal
        if experience_to_remove >= 0:
            st.session_state.experience.pop(experience_to_remove)
            st.rerun()

        # Add new work experience button
        if st.button("➕ Add Another Experience"):
            st.session_state.experience.append({"current": False})
            st.rerun()

    # Technical Skills Section
    with st.expander("Technical Skills", expanded=False):
        tech_skills = {}
        tech_skills["tech_skills"] = st.multiselect(
            label="Tech skills",
            options=SKILLS["tech_skills"] if isinstance(SKILLS["tech_skills"], list)
                else list(SKILLS["tech_skills"].keys()),
            default=st.session_state.get(f"selected_tech_skills", []),
            key=f"multiselect_tech_skills",
            placeholder=f"Select Tech skills...",
            max_selections=1000,
            accept_new_options=True
        )
        # st.session_state[f"selected_tech_skills"] =  tech_skills["tech_skills"]

        # Programming languages and libraries
        tech_skills["programming_languages"] = {}
        for lang in create_dynamic_input(
                "languages",
                list(SKILLS["programming_languages"].keys()),
                "programming languages"
        ):
            libs = create_dynamic_input(
                f"libs_{lang}",
                SKILLS["programming_languages"].get(lang, []),
                f"{lang} libraries"
            )
            tech_skills["programming_languages"][lang] = libs

    # Languages Section
    with st.expander("Languages"):
        language_levels = ["A1", "A2", "B1", "B2", "C1", "C2", "Native"]
        language_to_remove = -1

        # Display each language entry with delete button
        for i, lang in enumerate(st.session_state.languages):
            cols = st.columns([2, 1, 0.5])
            with cols[0]:
                lang["language"] = st.selectbox(
                    f"Language #{i + 1}",
                    options=SKILLS.get("languages", []),
                    key=f"lang_{i}",
                    accept_new_options=True
                )
            with cols[1]:
                lang["level"] = st.selectbox(f"Level #{i + 1}", language_levels, key=f"level_{i}")
            with cols[2]:
                # Only show delete button if there's more than one entry
                if len(st.session_state.languages) > 1:
                    if st.button("🗑️", key=f"del_lang_{i}"):
                        language_to_remove = i
            st.divider()

        # Process language entry removal
        if language_to_remove >= 0:
            st.session_state.languages.pop(language_to_remove)
            st.rerun()

        # Add new language button
        if st.button("➕ Add Another Language"):
            st.session_state.languages.append({})
            st.rerun()

    # Generate CV\    
    if st.button("Generate CV"):
        cv_data = {
            "personal_information": {
                "first_name": first,
                "last_name": last,
                "email": email
            },
            "technical_skills": tech_skills,
            "work_experience": st.session_state.experience,
            "education": st.session_state.education,
            "languages": st.session_state.languages,
            "company_information": st.session_state.company_info
        }
        st.json(cv_data)
        st.download_button(
            label="Download CV as JSON",
            data=json.dumps(cv_data, indent=2),
            file_name=f"{first}_{last}_cv.json",
            mime="application/json"
        )
        # Upload to blob storage\        
        try:
            client = connect_to_blob_storage()
            upload_cv_to_blob(cv_data, client, first, last)
            st.success("Uploaded to Azure Blob Storage.")
        except Exception as e:
            st.error(f"Upload failed: {e}")

if __name__ == '__main__':
    main()