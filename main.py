import streamlit as st
import pandas as pd
import os
import json
import anthropic
import hashlib
import time
import re

# Page config
st.set_page_config(page_title="Moxie MD-Nurse Matching", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .match-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 4px solid #4e7ddd;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .match-reason {
        background-color: #e9f7fe;
        border-radius: 5px;
        padding: 10px;
        margin-top: 5px;
        border-left: 3px solid #3498db;
    }
    .service-badge {
        background-color: #5c88da;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        margin-right: 5px;
        display: inline-block;
    }
    .main-header {
        color: #2c3e50;
        text-align: center;
        margin-bottom: 20px;
    }
    .subheader {
        color: #34495e;
        border-bottom: 1px solid #eee;
        padding-bottom: 10px;
    }
    .explanation {
        background-color: #f5f9ff;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    .password-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        background-color: white;
        text-align: center;
    }
    .password-header {
        margin-bottom: 20px;
        color: #2c3e50;
    }
    .trait-tag {
        background-color: #edf7ff;
        color: #2c5282;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        margin-right: 5px;
        margin-bottom: 5px;
        display: inline-block;
        border: 1px solid #bee3f8;
    }
    .preference-tag {
        background-color: #fff5f5;
        color: #c53030;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        margin-right: 5px;
        margin-bottom: 5px;
        display: inline-block;
        border: 1px solid #fed7d7;
    }
    .multi-state {
        background-color: #fffaf0;
        color: #dd6b20;
        border: 1px solid #feebc8;
    }
    .compatibility-score {
        font-size: 28px;
        font-weight: bold;
        text-align: center;
        margin: 10px 0;
        padding: 10px;
        border-radius: 50%;
        width: 60px;
        height: 60px;
        line-height: 40px;
        display: inline-block;
    }
    .high-score {
        background-color: #9ae6b4;
        color: #22543d;
    }
    .medium-score {
        background-color: #faf089;
        color: #744210;
    }
    .low-score {
        background-color: #feb2b2;
        color: #822727;
    }
    .filter-section {
        background-color: #f9fafb;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        border: 1px solid #e2e8f0;
    }
    .md-info {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 10px;
    }
    .md-detail {
        flex: 1;
        min-width: 200px;
        background-color: #f8f9fa;
        padding: 12px;
        border-radius: 5px;
        border: 1px solid #e2e8f0;
    }
    .md-detail h4 {
        margin-top: 0;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for password
if 'password_correct' not in st.session_state:
    st.session_state['password_correct'] = False

# Simple password screen
if not st.session_state['password_correct']:
    st.markdown("""
    <div class="password-container">
        <h2 class="password-header">Moxie MD-Nurse Matching System</h2>
        <p>Please enter the password to access the system:</p>
    </div>
    """, unsafe_allow_html=True)
    
    password = st.text_input("Password", type="password", key="password_input")
    
    if st.button("Login"):
        # Hard-code the password check for simplicity
        if password == "MoxieAI2025":
            st.session_state['password_correct'] = True
            st.experimental_rerun()
        else:
            st.error("Incorrect password. Please try again.")
    
    # Stop execution here if password is incorrect
    st.stop()

# Main application (only runs if password is correct)
st.markdown("<h1 class='main-header'>Moxie MD-Nurse Matching System</h1>", unsafe_allow_html=True)

# Load data
@st.cache_data
def load_data():
    try:
        # Load medical directors from CSV if available
        try:
            doctors_df = pd.read_csv('Medical_List.csv')
            # Filter for medical directors
            doctors_df = doctors_df[doctors_df['Lifecycle Stage'] == 'Medical Director Onboarded']
        except FileNotFoundError:
            # Create a sample doctor dataframe if CSV is not available
            doctor_data = [
                {"First Name": "John", "Last Name": "Smith", "Email": "john.smith@example.com", 
                 "Residing State  (Lives In)": "CA", "Create Date": "2023-01-15", "Lifecycle Stage": "Medical Director Onboarded"},
                {"First Name": "Emily", "Last Name": "Johnson", "Email": "emily.j@example.com", 
                 "Residing State  (Lives In)": "TX", "Create Date": "2023-02-20", "Lifecycle Stage": "Medical Director Onboarded"},
                {"First Name": "Michael", "Last Name": "Brown", "Email": "m.brown@example.com", 
                 "Residing State  (Lives In)": "FL", "Create Date": "2023-03-10", "Lifecycle Stage": "Medical Director Onboarded"}
            ]
            doctors_df = pd.DataFrame(doctor_data)
        
        # Try to load the MD metadata
        try:
            md_metadata_df = pd.read_csv('md_metadata.csv')
        except FileNotFoundError:
            # If not found, create an empty dataframe with appropriate columns
            md_metadata_df = pd.DataFrame(columns=['First Name', 'Last Name', 'Email', 'Residing State  (Lives In)', 'MD Preferences', 'Personality Traits'])
        
        # Process MD metadata
        # Handle First Name field - remove "Dr. " prefix if present
        md_metadata_df['First Name'] = md_metadata_df['First Name'].apply(
            lambda x: x.replace('Dr. ', '') if isinstance(x, str) and x.startswith('Dr. ') else x
        )
        
        # Process multiple states - convert to individual boolean checks to avoid ambiguity
        md_metadata_df['Multiple States'] = md_metadata_df['Residing State  (Lives In)'].apply(
            lambda x: (isinstance(x, str) and (';' in x or ',' in x))
        )
        
        md_metadata_df['States List'] = md_metadata_df['Residing State  (Lives In)'].apply(
            lambda x: [s.strip() for s in re.split(r'[;,]', str(x))] if isinstance(x, str) else []
        )
        
        # Flag for preferences - convert to individual boolean checks
        md_metadata_df['Has Preferences'] = md_metadata_df['MD Preferences'].apply(
            lambda x: (isinstance(x, str) and len(x.strip()) > 0)
        )
        
        # Split personality traits into a list for easier processing
        md_metadata_df['Traits List'] = md_metadata_df['Personality Traits'].apply(
            lambda x: [trait.strip() for trait in str(x).split(',')] if isinstance(x, str) else []
        )
        
        # Identify if the row is actually a nurse practitioner - use individual boolean checks
        md_metadata_df['Is NP'] = md_metadata_df['Last Name'].apply(
            lambda x: (isinstance(x, str) and 'NP' in x.upper())
        )
        
        # Create a dataframe for just the NPs
        nurse_providers_df = md_metadata_df[md_metadata_df['Is NP'] == True].copy()
        
        # Remove NPs from the MD dataframe
        md_metadata_df = md_metadata_df[md_metadata_df['Is NP'] == False].copy()
        
        # Create nurses dataframe directly from the provided data or from hubspot CSV
        try:
            nurses_df = pd.read_csv('hubspot_moxie.csv')
            # Filter to only relevant columns
            relevant_cols = [
                'Ticket Number Counter', 'Bird Eats Bug Email', 'Provider License Type',
                'Experience Level  ', 'State (MedSpa Premise)', 'Services Provided',
                'Addt\'l Service Notes'
            ]
            # Use columns that are actually in the dataframe
            available_cols = [col for col in relevant_cols if col in nurses_df.columns]
            nurses_df = nurses_df[available_cols].dropna(subset=['Bird Eats Bug Email'])
        except FileNotFoundError:
            # Create a sample dataframe
            nurse_data = [
                {"Name": "April Gage", "License": "RN", "Email": "dnagage@yahoo.com"},
                {"Name": "Michelle Conley", "License": "RN", "Email": "9lmccml9@gmail.com"},
                {"Name": "Jacqueline Murray", "License": "RN", "Email": "inbloomaesthetics24@gmail.com"},
                {"Name": "Gema Castellón", "License": "RN", "Email": "gcastellon05@yahoo.com"},
                {"Name": "Sarah Medina", "License": "NP", "Email": "sarahgmedina1@gmail.com"},
                {"Name": "Carolyn Lopez", "License": "NP", "Email": "defyingtimemt@yahoo.com"},
                {"Name": "Shannon Asuchak", "License": "RN", "Email": "sgoritz@yahoo.com"},
                {"Name": "Bobbi Garcia", "License": "RN", "Email": "radiancebeautyaesthetics@gmail.com"},
                {"Name": "Ilona", "License": "RN", "Email": "regenmed8@gmail.com"},
                {"Name": "Maribel Montes Person", "License": "RN", "Email": "maribelperson@gmail.com"}
            ]
            
            # Add nurse practitioners from the metadata if available
            if len(nurse_providers_df) > 0:
                for _, row in nurse_providers_df.iterrows():
                    name = f"{row['First Name']} {row['Last Name'].replace(', Np', '')}"
                    email = row['Email'] if pd.notna(row['Email']) else "unknown@example.com"
                    traits = row['Personality Traits'] if pd.notna(row['Personality Traits']) else ""
                    
                    nurse_data.append({
                        "Name": name,
                        "License": "NP",
                        "Email": email,
                        "Traits": traits
                    })
            
            # Convert to the format expected by the rest of the code
            nurses_data_formatted = []
            states = ["CA", "TX", "NY", "FL", "IL", "PA", "OH", "MI", "GA", "NC"]  # Sample states
            experience_levels = ["New Graduate", "1-3 years", "3-5 years", "5+ years"]
            
            import random
            
            for nurse in nurse_data:
                # Assign random states and experience for demo purposes
                random_state = random.choice(states)
                random_experience = random.choice(experience_levels)
                
                nurses_data_formatted.append({
                    "Ticket Number Counter": nurse["Name"],
                    "Bird Eats Bug Email": nurse["Email"],
                    "Provider License Type": nurse["License"],
                    "Experience Level  ": random_experience,
                    "State (MedSpa Premise)": random_state,
                    "Services Provided": "Botox, Fillers, Aesthetic services",
                    "Addt'l Service Notes": nurse.get("Traits", f"Experienced in {random.choice(['medical aesthetics', 'cosmetic procedures', 'skincare treatments'])}")
                })
            
            nurses_df = pd.DataFrame(nurses_data_formatted)
        
        # Merge MD metadata with main doctors dataframe if possible
        if len(doctors_df) > 0 and len(md_metadata_df) > 0:
            # Try to match by email first (most reliable)
            merged_df = pd.merge(
                doctors_df, 
                md_metadata_df[['Email', 'MD Preferences', 'Personality Traits', 'Multiple States', 'States List', 'Has Preferences', 'Traits List']], 
                on='Email', 
                how='left'
            )
            
            # For any unmatched rows, try matching by name
            unmatched = merged_df[merged_df['MD Preferences'].isna()]
            if not unmatched.empty:
                # Create a name field for matching
                doctors_df['Full Name'] = doctors_df['First Name'] + ' ' + doctors_df['Last Name']
                md_metadata_df['Full Name'] = md_metadata_df['First Name'] + ' ' + md_metadata_df['Last Name']
                
                # Try matching again
                for idx, row in unmatched.iterrows():
                    full_name = f"{row['First Name']} {row['Last Name']}"
                    matches = md_metadata_df[md_metadata_df['Full Name'].str.contains(full_name, case=False, na=False)]
                    
                    if not matches.empty:
                        metadata = matches.iloc[0]
                        merged_df.at[idx, 'MD Preferences'] = metadata['MD Preferences']
                        merged_df.at[idx, 'Personality Traits'] = metadata['Personality Traits']
                        merged_df.at[idx, 'Multiple States'] = metadata['Multiple States']
                        merged_df.at[idx, 'States List'] = metadata['States List']
                        merged_df.at[idx, 'Has Preferences'] = metadata['Has Preferences']
                        merged_df.at[idx, 'Traits List'] = metadata['Traits List']
            
            doctors_df = merged_df
            
            # Fill in missing values
            doctors_df['MD Preferences'] = doctors_df['MD Preferences'].fillna('')
            doctors_df['Personality Traits'] = doctors_df['Personality Traits'].fillna('')
            doctors_df['Multiple States'] = doctors_df['Multiple States'].fillna(False)
            doctors_df['Has Preferences'] = doctors_df['Has Preferences'].fillna(False)
            
            # Ensure States List is properly filled - handling Series safely
            doctors_df['States List'] = doctors_df.apply(
                lambda row: row['States List'] if isinstance(row['States List'], list) else 
                            [row['Residing State  (Lives In)']] if pd.notna(row['Residing State  (Lives In)']) else [],
                axis=1
            )
            
            # Ensure Traits List is properly filled - handling Series safely
            doctors_df['Traits List'] = doctors_df.apply(
                lambda row: row['Traits List'] if isinstance(row['Traits List'], list) else 
                            [trait.strip() for trait in str(row['Personality Traits']).split(',')] 
                            if pd.notna(row['Personality Traits']) else [],
                axis=1
            )
            
        # If we still don't have metadata for doctors, use the metadata dataframe directly
        elif len(doctors_df) == 0 and len(md_metadata_df) > 0:
            doctors_df = md_metadata_df.copy()
            
            # Add missing columns expected by the application
            if 'Create Date' not in doctors_df.columns:
                doctors_df['Create Date'] = '2023-01-01'  # Default date
            if 'Lifecycle Stage' not in doctors_df.columns:
                doctors_df['Lifecycle Stage'] = 'Medical Director Onboarded'
        
        return doctors_df, nurses_df
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None

# Extract traits/preferences for display
def extract_personality_traits(traits_text):
    if not traits_text or not isinstance(traits_text, str):
        return []
    
    # Split by commas and clean up
    traits = [trait.strip() for trait in traits_text.split(',')]
    return traits

def extract_md_preferences(prefs_text):
    if not prefs_text or not isinstance(prefs_text, str):
        return []
    
    # Split into sentences or by semicolons
    prefs = []
    for pref in re.split(r'[.;]', prefs_text):
        if pref.strip():
            prefs.append(pref.strip())
    
    return prefs

# Function to create a matching prompt
def create_claude_prompt(search_type, search_value, doctors_df, nurses_df, filters=None):
    if filters is None:
        filters = {}
        
    if search_type == "md":
        # Find the doctor in the dataframe
        doctor_row = doctors_df[
            doctors_df.apply(
                lambda row: search_value.lower() in f"{row['First Name']} {row['Last Name']}".lower(), 
                axis=1
            )
        ]
        
        if doctor_row.empty:
            return None, "Doctor not found in database."
        
        doctor = doctor_row.iloc[0]
        
        # Extract personality traits and preferences for more detailed matching
        personality_traits = doctor.get('Personality Traits', '')
        md_preferences = doctor.get('MD Preferences', '')
        states = doctor.get('States List', [])
        if not states and 'Residing State  (Lives In)' in doctor:
            states = [doctor['Residing State  (Lives In)']]
        
        # Create base prompt
        prompt = f"""
        You are an Operations Manager at Moxie tasked with matching medical directors with nurses.
        
        Doctor Information:
        - Name: {doctor['First Name']} {doctor['Last Name']}
        - Email: {doctor['Email']}
        - State(s): {', '.join(str(s) for s in states if s)}
        - Onboarded: {doctor.get('Create Date', 'Unknown')}
        """
        
        # Add personality traits if available
        if personality_traits:
            prompt += f"- Personality: {personality_traits}\n"
        
        # Add MD preferences if available
        if md_preferences:
            prompt += f"- Preferences: {md_preferences}\n"
        
        # Add filter requirements to the prompt
        if filters.get("experience"):
            prompt += f"\n\nPreference for nurses with experience level: {filters['experience']}"
            
        if filters.get("location") == "Same State Only":
            prompt += "\nLocation requirement: Only include nurses in the same state as the doctor."
        elif filters.get("location") == "Nearby States Acceptable":
            prompt += "\nLocation preference: Prioritize nurses in the same state, but nearby states are acceptable."
            
        if filters.get("license_type") and filters.get("license_type") != "Any":
            prompt += f"\n\nOnly looking for nurses with license type: {filters['license_type']}"
            
        if filters.get("requirements") and filters.get("requirements").strip():
            prompt += f"\n\nAdditional requirements to consider:\n{filters['requirements']}"
        
        prompt += """
        
        Using the doctor information above, analyze the following nurse candidates and identify the top 3 best matches based on:
        1. Location match (highest priority - same state is ideal)
        2. Experience level compatibility (experienced doctors can mentor newer nurses)
        3. Service offering alignment
        4. Personality compatibility
        5. Adherence to doctor's preferences
        6. Any specific notes or requirements mentioned
        
        For each match, provide:
        1. The nurse's name
        2. Contact information
        3. A detailed and robust explanation of why they're a good match, making specific connections between:
           - The doctor's personality traits and the nurse's background/experience
           - How the doctor's preferences align with the nurse's profile
           - Shared geographical advantages of their locations
           - Why their experience levels complement each other
           - How the nurse's services match the doctor's expertise
        4. A match score out of 10
        
        Be specific and detailed in your reasoning, drawing direct connections between the doctor's profile and the nurse's background. Mention specific personality traits and work style factors that make them a good team.
        
        Available Nurses:
        """
        
        # Apply filters to nurses
        filtered_nurses = nurses_df.copy()
        
        # Apply experience filter if specified
        if filters.get("experience") and filters.get("experience") != "Any":
            filtered_nurses = filtered_nurses[
                filtered_nurses['Experience Level  '].str.contains(filters.get("experience"), na=False)
            ]
        
        # Apply license type filter
        if filters.get("license_type") and filters.get("license_type") != "Any":
            filtered_nurses = filtered_nurses[
                filtered_nurses['Provider License Type'].str.contains(filters.get("license_type"), na=False)
            ]
        
        # Handle location filtering
        if filters.get("location") == "Same State Only":
            # Get all nurses in any of the doctor's states
            same_state_nurses = filtered_nurses[filtered_nurses['State (MedSpa Premise)'].isin(states)]
            selected_nurses = same_state_nurses
        else:
            # Priority to same state nurses
            same_state_nurses = filtered_nurses[filtered_nurses['State (MedSpa Premise)'].isin(states)]
            other_nurses = filtered_nurses[~filtered_nurses['State (MedSpa Premise)'].isin(states)]
            
            # Combine same state and other nurses, prioritizing same state
            selected_nurses = pd.concat([same_state_nurses, other_nurses])
        
        # Check MD preferences for any exclusions
        if md_preferences:
            # Check for maxed out capacity on certain license types
            if "maxed" in md_preferences.lower() and "np" in md_preferences.lower():
                # Filter out NPs if MD is maxed out
                selected_nurses = selected_nurses[
                    ~selected_nurses['Provider License Type'].str.contains('NP', na=False, case=False)
                ]
            
            # Check for experience requirements
            if "experience" in md_preferences.lower() or "6mo experience" in md_preferences.lower():
                # Filter out new graduates
                selected_nurses = selected_nurses[
                    ~selected_nurses['Experience Level  '].str.contains('New Graduate', na=False, case=False)
                ]
        
        # Apply keyword filter from additional requirements if specified
        if filters.get("requirements") and filters.get("requirements").strip():
            keywords = filters.get("requirements").lower().split()
            keyword_matches = []
            
            for _, nurse in selected_nurses.iterrows():
                # Combine all text fields for keyword search
                all_text = ' '.join([
                    str(nurse['Provider License Type']) if pd.notna(nurse['Provider License Type']) else '',
                    str(nurse['Experience Level  ']) if pd.notna(nurse['Experience Level  ']) else '',
                    str(nurse['Services Provided']) if pd.notna(nurse['Services Provided']) else '',
                    str(nurse['Addt\'l Service Notes']) if pd.notna(nurse['Addt\'l Service Notes']) else ''
                ]).lower()
                
                # Count how many keywords match
                match_count = sum(1 for keyword in keywords if keyword in all_text)
                keyword_matches.append((match_count, nurse))
            
            # Sort by number of keyword matches (highest first)
            keyword_matches.sort(reverse=True, key=lambda x: x[0])
            
            # Take top 20 matches if available
            top_matches = [match[1] for match in keyword_matches[:20]]
            if top_matches:
                selected_nurses = pd.DataFrame(top_matches)
        
        # If no nurses match the filters, fall back to showing some results
        if selected_nurses.empty:
            selected_nurses = nurses_df.head(20)
            prompt += "\nNote: No nurses matched all specified filters, so showing a general selection.\n\n"
        else:
            # Limit to top 20 for prompt length
            selected_nurses = selected_nurses.head(20)
        
        # Add nurse information to the prompt
        for _, nurse in selected_nurses.iterrows():
            # Safe extraction of fields
            nurse_name = str(nurse['Ticket Number Counter']) if pd.notna(nurse['Ticket Number Counter']) else "Unknown"
            nurse_email = str(nurse['Bird Eats Bug Email']) if pd.notna(nurse['Bird Eats Bug Email']) else "No email"
            nurse_license = str(nurse['Provider License Type']) if pd.notna(nurse['Provider License Type']) else "Unknown"
            nurse_experience = str(nurse['Experience Level  ']) if pd.notna(nurse['Experience Level  ']) else "Unknown"
            nurse_state = str(nurse['State (MedSpa Premise)']) if pd.notna(nurse['State (MedSpa Premise)']) else "Unknown"
            nurse_services = str(nurse['Services Provided']) if pd.notna(nurse['Services Provided']) else "None specified"
            nurse_notes = str(nurse['Addt\'l Service Notes']) if pd.notna(nurse['Addt\'l Service Notes']) else "None"
            
            # Add to prompt
            prompt += f"""
            Nurse:
            - Name: {nurse_name}
            - Email: {nurse_email}
            - License Type: {nurse_license}
            - Experience: {nurse_experience}
            - State: {nurse_state}
            - Services: {nurse_services}
            - Notes: {nurse_notes}
            
            """
        
        # Add response format instructions
        prompt += """
        Format your response as JSON with the following structure:
        {
            "matches": [
                {
                    "name": "Nurse Name",
                    "email": "nurse@email.com",
                    "match_score": 8.5,
                    "reasoning": "Detailed explanation of why this is a good match that specifically mentions the doctor's personality traits and how they align with the nurse's profile"
                },
                ...
            ]
        }
        
        Only include the JSON in your response, nothing else.
        """
        
        return prompt, None
    
    elif search_type == "nurse":
        # Find the nurse
        nurse_row = nurses_df[
            nurses_df.apply(
                lambda row: pd.notna(row['Ticket Number Counter']) and search_value.lower() in str(row['Ticket Number Counter']).lower(),
                axis=1
            )
        ]
        
        if nurse_row.empty:
            return None, "Nurse not found in database."
        
        nurse = nurse_row.iloc[0]
        
        # Safe extraction of fields
        nurse_name = str(nurse['Ticket Number Counter']) if pd.notna(nurse['Ticket Number Counter']) else "Unknown"
        nurse_email = str(nurse['Bird Eats Bug Email']) if pd.notna(nurse['Bird Eats Bug Email']) else "No email"
        nurse_license = str(nurse['Provider License Type']) if pd.notna(nurse['Provider License Type']) else "Unknown"
        nurse_experience = str(nurse['Experience Level  ']) if pd.notna(nurse['Experience Level  ']) else "Unknown"
        nurse_state = str(nurse['State (MedSpa Premise)']) if pd.notna(nurse['State (MedSpa Premise)']) else "Unknown"
        nurse_services = str(nurse['Services Provided']) if pd.notna(nurse['Services Provided']) else "None specified"
        nurse_notes = str(nurse['Addt\'l Service Notes']) if pd.notna(nurse['Addt\'l Service Notes']) else "None"
        
        # Create base prompt
        prompt = f"""
        You are an Operations Manager at Moxie tasked with matching nurses with medical directors.
        
        Nurse Information:
        - Name: {nurse_name}
        - Email: {nurse_email}
        - License Type: {nurse_license}
        - Experience Level: {nurse_experience}
        - State: {nurse_state}
        - Services: {nurse_services}
        - Additional Notes: {nurse_notes}
        """
        
        # Add filter requirements to the prompt
        if filters.get("md_age") and filters.get("md_age") != "Any":
            prompt += f"\n\nPreference for medical directors who are: {filters['md_age']}"
            
        if filters.get("interaction_style") and filters.get("interaction_style") != "Any":
            prompt += f"\n\nPreference for medical directors with interaction style: {filters['interaction_style']}"
            
        if filters.get("location") == "Same State Only":
            prompt += "\nLocation requirement: Only include medical directors in the same state as the nurse."
        elif filters.get("location") == "Nearby States Acceptable":
            prompt += "\nLocation preference: Prioritize medical directors in the same state, but nearby states are acceptable."
            
        if filters.get("service_requirements") and filters.get("service_requirements").strip():
            prompt += f"\n\nAdditional service requirements to consider:\n{filters['service_requirements']}"
        
        prompt += """
        
        Using the nurse information above, analyze the following medical directors and identify the top 3 best matches based on:
        1. Location match (highest priority - same state is ideal)
        2. Experience level compatibility (experienced doctors can mentor newer nurses)
        3. Personality compatibility
        4. Doctor's preferences and capacity for the nurse's license type
        5. Any specific notes or requirements mentioned
        
        For each match, provide:
        1. The doctor's name
        2. Contact information
        3. A detailed and robust explanation of why they're a good match, making specific connections between:
           - The doctor's personality traits and how they align with the nurse's experience level
           - Whether the doctor's working style is beneficial for this nurse
           - Specific geographic advantages of their locations
           - How their experience and expertise complement each other
           - How their personalities would likely create a positive working relationship
        4. A match score out of 10
        
        Be specific and detailed in your reasoning, drawing direct connections between their profiles. Mention concrete personality traits and preferences that make them compatible.
        
        Available Medical Directors:
        """
        
        # Filter doctors based on criteria
        filtered_doctors = doctors_df.copy()
        
        # Apply MD age filter if specified
        if filters.get("md_age") and filters.get("md_age") != "Any":
            age_keywords = filters.get("md_age").lower()
            if "younger" in age_keywords:
                filtered_doctors = filtered_doctors[
                    filtered_doctors['Personality Traits'].str.contains('young|younger', case=False, na=False)
                ]
            elif "older" in age_keywords or "experienced" in age_keywords:
                filtered_doctors = filtered_doctors[
                    filtered_doctors['Personality Traits'].str.contains('older|middle|experienced', case=False, na=False)
                ]
        
        # Apply interaction style filter
        if filters.get("interaction_style") and filters.get("interaction_style") != "Any":
            style = filters.get("interaction_style").lower()
            if "hands-on" in style:
                filtered_doctors = filtered_doctors[
                    filtered_doctors['Personality Traits'].str.contains('hands-on|training|collaborative', case=False, na=False)
                ]
            elif "autonomous" in style:
                filtered_doctors = filtered_doctors[
                    filtered_doctors['Personality Traits'].str.contains('autonomous|hands-off|independent', case=False, na=False)
                ]
        
        # Apply location filter - use States List if available
        if filters.get("location") == "Same State Only" and nurse_state != "Unknown":
            filtered_doctors = filtered_doctors[
                filtered_doctors.apply(
                    lambda row: nurse_state in row.get('States List', []) if isinstance(row.get('States List'), list) 
                    else nurse_state == row.get('Residing State  (Lives In)', ''), 
                    axis=1
                )
            ]
        
        # Check for "maxed out" status with the nurse's license type
        if nurse_license:
            # Filter out doctors who are maxed out on this license type
            license_filter = nurse_license.upper()
            filtered_doctors = filtered_doctors[
                ~filtered_doctors['MD Preferences'].str.contains(
                    f'maxed out.*{license_filter}|maxed.*{license_filter}', 
                    case=False, 
                    na=False, 
                    regex=True
                )
            ]
        
        # Apply keyword filter from service requirements if specified
        if filters.get("service_requirements") and filters.get("service_requirements").strip():
            keywords = filters.get("service_requirements").lower().split()
            keyword_matches = []
            
            for _, doctor in filtered_doctors.iterrows():
                # Combine all text fields for keyword search
                all_text = ' '.join([
                    str(doctor['First Name'] + ' ' + doctor['Last Name']),
                    str(doctor['Personality Traits']) if pd.notna(doctor['Personality Traits']) else '',
                    str(doctor['MD Preferences']) if pd.notna(doctor['MD Preferences']) else ''
                ]).lower()
                
                match_count = sum(1 for keyword in keywords if keyword in all_text)
                keyword_matches.append((match_count, doctor))
            
            # Sort by number of keyword matches (highest first)
            keyword_matches.sort(reverse=True, key=lambda x: x[0])
            
            # Take top 20 matches if available
            top_matches = [match[1] for match in keyword_matches[:20]]
            if top_matches:
                filtered_doctors = pd.DataFrame(top_matches)
        
        # If filters resulted in no doctors, fall back to original selection method
        if filtered_doctors.empty:
            filtered_doctors = doctors_df
            prompt += "\nNote: No medical directors matched all specified filters, so showing a general selection.\n\n"
        
        # Select doctors to include
        if nurse_state != "Unknown":
            # Find doctors in the same state (using States List if available)
            same_state_doctors = filtered_doctors[
                filtered_doctors.apply(
                    lambda row: nurse_state in row.get('States List', []) if isinstance(row.get('States List'), list)
                    else nurse_state == row.get('Residing State  (Lives In)', ''),
                    axis=1
                )
            ]
            
            # Find other doctors
            other_doctors = filtered_doctors[
                ~filtered_doctors.apply(
                    lambda row: nurse_state in row.get('States List', []) if isinstance(row.get('States List'), list)
                    else nurse_state == row.get('Residing State  (Lives In)', ''),
                    axis=1
                )
            ]
            
            # Prioritize same state doctors
            selected_doctors = pd.concat([same_state_doctors.head(10), other_doctors.head(10)])
        else:
            selected_doctors = filtered_doctors.head(20)
        
        # Add doctor information to the prompt
        for _, doctor in selected_doctors.iterrows():
            # Get the states (handling multiple states)
            states = doctor.get('States List', []) if isinstance(doctor.get('States List'), list) else [doctor.get('Residing State  (Lives In)', '')]
            states_str = ', '.join(str(s) for s in states if s)
            
            # Get personality traits and preferences
            traits = doctor.get('Personality Traits', '')
            preferences = doctor.get('MD Preferences', '')
            
            doctor_info = f"""
            Doctor:
            - Name: {doctor['First Name']} {doctor['Last Name']}
            - Email: {doctor['Email']}
            - State(s): {states_str}
            """
            
            if traits:
                doctor_info += f"- Personality: {traits}\n"
            
            if preferences:
                doctor_info += f"- Preferences: {preferences}\n"
            
            prompt += doctor_info + "\n"
        
        # Add response format instructions
        prompt += """
        Format your response as JSON with the following structure:
        {
            "matches": [
                {
                    "name": "Dr. Name",
                    "email": "doctor@email.com",
                    "match_score": 8.5, 
                    "reasoning": "Detailed explanation of why this is a good match that specifically references the doctor's personality traits and how they align with the nurse's needs"
                },
                ...
            ]
        }
        
        Only include the JSON in your response, nothing else.
        """
        
        return prompt, None
    
    elif search_type == "manual":
        # Manual entry form with additional filter context
        prompt = f"""
        You are an Operations Manager at Moxie tasked with matching medical directors with nurses.
        
        A user has submitted the following information:
        {search_value}
        
        """
        
        # Add filter requirements
        if filters.get("person_type"):
            prompt += f"This person is identified as a {filters.get('person_type')}.\n\n"
            
        if filters.get("matching_priorities") and filters.get("matching_priorities").strip():
            prompt += f"Matching priorities to consider:\n{filters.get('matching_priorities')}\n\n"
        
        prompt += """
        Based on this information, identify if this is a doctor or a nurse, and suggest potential matches from our database.
        
        For each match, provide:
        1. The name of the matched professional
        2. Contact information if available
        3. A detailed and robust explanation of why they're a good match, specifically:
           - How their personalities would complement each other
           - How their experience levels align or complement each other
           - Specific geographic advantages
           - Any shared specialties or interests
           - Why they would work well as a team based on their traits
        4. A match score out of 10
        
        Be specific in your reasoning, with concrete examples of why these individuals would work well together.
        
        Format your response as JSON with the following structure:
        {
            "person_type": "doctor" or "nurse",
            "matches": [
                {
                    "name": "Name",
                    "email": "email@example.com",
                    "match_score": 8.5,
                    "reasoning": "Detailed explanation of why this is a good match with specific references to personality traits and compatibility factors"
                },
                ...
            ]
        }
        
        Only include the JSON in your response, nothing else.
        """
        
        return prompt, None

# Create a hash from the prompt for caching
def get_prompt_hash(prompt):
    return hashlib.md5(prompt.encode()).hexdigest()

# Cache the Claude API responses
@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_claude_api(prompt_hash, prompt, api_key):
    return query_claude(prompt, api_key)

# Function to call Claude API with fallback to Haiku model
def query_claude(prompt, api_key, max_retries=2):
    # First try with the primary model (Sonnet)
    primary_model = "claude-3-5-sonnet-20240620"
    fallback_model = "claude-3-haiku-20240307"
    
    for attempt in range(max_retries):
        try:
            # Choose model based on the attempt number
            current_model = primary_model if attempt == 0 else fallback_model
            
            # Initialize the client
            client = anthropic.Anthropic(api_key=api_key)
            
            # Make the API request
            message = client.messages.create(
                model=current_model,
                max_tokens=4000,
                temperature=0.2,
                system="You are a medical staffing expert at Moxie. You help match medical directors with nurses based on their location, experience, services offered, personality traits, and other relevant factors. You always respond in JSON format as specified in the prompts.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
            
        except Exception as e:
            error_str = str(e)
            
            # If this was the primary model and we got an overloaded error
            if attempt == 0 and "overloaded_error" in error_str:
                st.warning(f"Primary AI model is busy. Trying with a faster model...")
                time.sleep(1)  # Brief pause before retrying
                continue
                
            # If this was the fallback model or another error
            elif attempt == max_retries - 1:
                st.error(f"API error: {error_str}")
                return json.dumps({"error": f"API error: {error_str}"})
                
            # If this was the primary model but not an overloaded error
            else:
                st.error(f"API error: {error_str}")
                return json.dumps({"error": f"API error: {error_str}"})

# Display MD traits and preferences in a nice way
def display_md_details(doctor):
    # Get traits and preferences
    traits = extract_personality_traits(doctor.get('Personality Traits', ''))
    preferences = extract_md_preferences(doctor.get('MD Preferences', ''))
    states = doctor.get('States List', [])
    if not states and 'Residing State  (Lives In)' in doctor:
        states = [doctor['Residing State  (Lives In)']]
    
    # Display states
    states_html = ""
    for state in states:
        if state and pd.notna(state):
            states_html += f'<span class="trait-tag multi-state">{state}</span>'
    
    # Display traits
    traits_html = ""
    for trait in traits:
        if trait.strip():
            traits_html += f'<span class="trait-tag">{trait.strip()}</span>'
    
    # Display preferences
    prefs_html = ""
    for pref in preferences:
        if pref.strip():
            prefs_html += f'<span class="preference-tag">{pref.strip()}</span>'
    
    st.markdown(f"""
    <div class="md-info">
        <div class="md-detail">
            <h4>States</h4>
            {states_html if states_html else "No state information available"}
        </div>
        <div class="md-detail">
            <h4>Personality Traits</h4>
            {traits_html if traits_html else "No traits information available"}
        </div>
        <div class="md-detail">
            <h4>Preferences</h4>
            {prefs_html if prefs_html else "No preferences specified"}
        </div>
    </div>
    """, unsafe_allow_html=True)

# Main application content
doctors_df, nurses_df = load_data()

if doctors_df is None or nurses_df is None:
    st.error("Failed to load data. Please check the data files.")
else:
    # Display stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Medical Directors", len(doctors_df))
    with col2:
        st.metric("Nurses (RN/NP)", len(nurses_df))
    with col3:
        st.markdown("**Powered by:** Claude AI")
    
    # Get Claude API key from environment variable
    claude_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Search options
    st.markdown("<h2 class='subheader'>Find Matches</h2>", unsafe_allow_html=True)
    
    search_type = st.radio(
        "Search by:",
        ("Medical Director", "Nurse", "Manual Entry"),
        horizontal=True
    )
    
    # Convert the search type to a simpler format
    search_type_key = {
        "Medical Director": "md",
        "Nurse": "nurse",
        "Manual Entry": "manual"
    }[search_type]
    
    if search_type_key == "md":
        # Get a list of all doctors for the dropdown
        doctor_names = [f"{row['First Name']} {row['Last Name']}" for _, row in doctors_df.iterrows()]
        selected_doctor = st.selectbox("Select Medical Director:", [""] + sorted(doctor_names))
        
        # If a doctor is selected, show their details
        if selected_doctor:
            doctor_row = doctors_df[
                doctors_df.apply(
                    lambda row: selected_doctor.lower() in f"{row['First Name']} {row['Last Name']}".lower(), 
                    axis=1
                )
            ]
            
            if not doctor_row.empty:
                doctor = doctor_row.iloc[0]
                display_md_details(doctor)
        
        # Add specific filtering criteria
        st.markdown("<h3 class='subheader'>Nurse Preference Filters</h3>", unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="filter-section">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            
            with col1:
                exp_filter = st.selectbox("Experience Level:", ["Any", "New Graduate", "1-3 years", "3-5 years", "5+ years"])
            
            with col2:
                license_filter = st.selectbox("License Type:", ["Any", "RN", "NP", "PA"])
            
            with col3:
                location_preference = st.radio("Location Priority:", ["Same State Only", "Nearby States Acceptable", "Any Location"])
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        additional_requirements = st.text_area("Additional Requirements (service types, availability, etc.):", height=100)
        
        if selected_doctor and st.button("Find Matching Nurses"):
            if not claude_api_key:
                st.error("API key is not configured. Please set the ANTHROPIC_API_KEY environment variable.")
            else:
                with st.spinner("Finding the best nurse matches..."):
                    # Update prompt creation to include the filters
                    prompt, error = create_claude_prompt(
                        search_type_key, 
                        selected_doctor, 
                        doctors_df, 
                        nurses_df,
                        filters={
                            "experience": exp_filter if exp_filter != "Any" else None,
                            "license_type": license_filter if license_filter != "Any" else None,
                            "location": location_preference,
                            "requirements": additional_requirements
                        }
                    )
                    
                    if error:
                        st.error(error)
                    else:
                        # Create a hash for caching
                        prompt_hash = get_prompt_hash(prompt)
                        
                        # Call Claude API with caching
                        response = cached_claude_api(prompt_hash, prompt, claude_api_key)
                        
                        try:
                            matches = json.loads(response)
                            
                            # Display matches
                            st.markdown(f"<h3>Top Matches for {selected_doctor}</h3>", unsafe_allow_html=True)
                            
                            for match in matches.get("matches", []):
                                # Determine score color class
                                score = float(match['match_score'])
                                score_class = "high-score" if score >= 8.0 else "medium-score" if score >= 6.0 else "low-score"
                                
                                st.markdown(
                                    f"""<div class="match-card">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <h4>{match['name']}</h4>
                                        <div class="compatibility-score {score_class}">{match['match_score']}</div>
                                    </div>
                                    <p><strong>Contact:</strong> {match['email']}</p>
                                    <div class="match-reason">
                                        <p><strong>Why this match works:</strong> {match['reasoning']}</p>
                                    </div>
                                    </div>""",
                                    unsafe_allow_html=True
                                )
                        except json.JSONDecodeError:
                            st.error("Error parsing response. Please try again.")
                            st.text(response)
    
    elif search_type_key == "nurse":
        # Get a list of all nurses for the dropdown
        nurse_names = [str(row['Ticket Number Counter']) for _, row in nurses_df.iterrows() if pd.notna(row['Ticket Number Counter'])]
        selected_nurse = st.selectbox("Select Nurse:", [""] + sorted(nurse_names))
        
        # Add specific filtering criteria
        st.markdown("<h3 class='subheader'>MD Preference Filters</h3>", unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="filter-section">', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            
            with col1:
                md_age = st.selectbox(
                    "MD Age/Experience Preference:", 
                    ["Any", "Younger physicians", "Older/more experienced physicians"]
                )
            
            with col2:
                interaction_style = st.selectbox(
                    "Interaction Style Preference:", 
                    ["Any", "Hands-on/Collaborative", "Autonomous/Hands-off"]
                )
            
            location_preference = st.radio("Location Priority:", ["Same State Only", "Nearby States Acceptable", "Any Location"])
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        service_requirements = st.text_area("Specific Service Requirements:", height=100, 
                                       placeholder="E.g., Must be experienced with Botox, looking for mentor in fillers, etc.")
        
        if selected_nurse and st.button("Find Matching Medical Directors"):
            if not claude_api_key:
                st.error("API key is not configured. Please set the ANTHROPIC_API_KEY environment variable.")
            else:
                with st.spinner("Finding the best medical director matches..."):
                    prompt, error = create_claude_prompt(
                        search_type_key, 
                        selected_nurse, 
                        doctors_df, 
                        nurses_df,
                        filters={
                            "md_age": md_age if md_age != "Any" else None,
                            "interaction_style": interaction_style if interaction_style != "Any" else None,
                            "location": location_preference,
                            "service_requirements": service_requirements
                        }
                    )
                    
                    if error:
                        st.error(error)
                    else:
                        # Create a hash for caching
                        prompt_hash = get_prompt_hash(prompt)
                        
                        # Call Claude API with caching
                        response = cached_claude_api(prompt_hash, prompt, claude_api_key)
                        
                        try:
                            matches = json.loads(response)
                            
                            # Display matches
                            st.markdown(f"<h3>Top Matches for {selected_nurse}</h3>", unsafe_allow_html=True)
                            
                            for match in matches.get("matches", []):
                                # Determine score color class
                                score = float(match['match_score'])
                                score_class = "high-score" if score >= 8.0 else "medium-score" if score >= 6.0 else "low-score"
                                
                                st.markdown(
                                    f"""<div class="match-card">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <h4>{match['name']}</h4>
                                        <div class="compatibility-score {score_class}">{match['match_score']}</div>
                                    </div>
                                    <p><strong>Contact:</strong> {match['email']}</p>
                                    <div class="match-reason">
                                        <p><strong>Why this match works:</strong> {match['reasoning']}</p>
                                    </div>
                                    </div>""",
                                    unsafe_allow_html=True
                                )
                        except json.JSONDecodeError:
                            st.error("Error parsing response. Please try again.")
                            st.text(response)
    
    else:  # Manual entry
        st.markdown("""
        <div class="explanation">
            Enter information about the doctor or nurse you want to match. Include details like:
            <ul>
                <li>Name and role (MD, RN, NP)</li>
                <li>State/location</li>
                <li>Experience level</li>
                <li>Services offered/interested in</li>
                <li>Personality traits</li>
                <li>Any special requirements or notes</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Add more specific options for manual entry
        col1, col2 = st.columns(2)
        with col1:
            person_type = st.radio("This person is a:", ["Unknown", "Medical Director", "Nurse"])
        
        user_input = st.text_area("Enter professional information:", height=150, 
                                placeholder="e.g., Dr. Smith is a younger physician in California who specializes in aesthetics. Communicative and responsive, prefers working with experienced nurses.")
        
        matching_priorities = st.text_area(
            "Specific matching priorities:", 
            height=100,
            placeholder="E.g., Must be in same state, looking for someone with Botox experience, needs collaborative personality, etc."
        )
        
        if user_input and st.button("Find Matches"):
            if not claude_api_key:
                st.error("API key is not configured. Please set the ANTHROPIC_API_KEY environment variable.")
            else:
                with st.spinner("Finding the best matches..."):
                    prompt, error = create_claude_prompt(
                        search_type_key, 
                        user_input, 
                        doctors_df, 
                        nurses_df,
                        filters={
                            "person_type": person_type if person_type != "Unknown" else None,
                            "matching_priorities": matching_priorities
                        }
                    )
                    
                    if error:
                        st.error(error)
                    else:
                        # Create a hash for caching
                        prompt_hash = get_prompt_hash(prompt)
                        
                        # Call Claude API with caching
                        response = cached_claude_api(prompt_hash, prompt, claude_api_key)
                        
                        try:
                            matches = json.loads(response)
                            
                            # Display person type
                            person_type = matches.get("person_type", "professional")
                            st.markdown(f"<h3>Top Matches for this {person_type.capitalize()}</h3>", unsafe_allow_html=True)
                            
                            for match in matches.get("matches", []):
                                # Determine score color class
                                score = float(match['match_score'])
                                score_class = "high-score" if score >= 8.0 else "medium-score" if score >= 6.0 else "low-score"
                                
                                st.markdown(
                                    f"""<div class="match-card">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <h4>{match['name']}</h4>
                                        <div class="compatibility-score {score_class}">{match['match_score']}</div>
                                    </div>
                                    <p><strong>Contact:</strong> {match['email']}</p>
                                    <div class="match-reason">
                                        <p><strong>Why this match works:</strong> {match['reasoning']}</p>
                                    </div>
                                    </div>""",
                                    unsafe_allow_html=True
                                )
                        except json.JSONDecodeError:
                            st.error("Error parsing response. Please try again.")
                            st.text(response)
    
    # Explanation of how it works
    with st.expander("How the Claude AI Matching System Works"):
        st.markdown("""
        This enhanced matching system uses Claude AI to intelligently match medical directors with nurses based on multiple factors:
        
        1. **Location Matching**: The system prioritizes professionals in the same state to ensure licensing compatibility and convenience.
        
        2. **Experience Level Compatibility**: The system considers the experience levels of both professionals, often matching experienced doctors with newer nurses who need mentorship.
        
        3. **Personality Trait Analysis**: The system analyzes the personality traits and work styles of medical directors to find complementary matches with nurses.
        
        4. **Preference Respect**: The system takes into account specific preferences of medical directors (e.g., license types they're willing to supervise).
        
        5. **Service Alignment**: The system analyzes the services provided by nurses and looks for doctors with relevant expertise.
        
        6. **Detailed Reasoning**: For each match, the system provides a comprehensive explanation that specifically highlights personality compatibility and professional synergies.
        
        7. **Match Score**: The system provides a score out of 10 with detailed reasoning to explain why each match works well.
        
        **Technical Features**:
        
        - Results are cached to improve performance and reduce API usage
        - System automatically switches to a faster AI model during high demand periods
        - Smart filtering analyzes professional attributes and prioritizes the best matches
        - Trait-based matching goes beyond basic location and license type compatibility
        """)
