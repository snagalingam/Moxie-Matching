import streamlit as st
import pandas as pd
import os
import json
import anthropic
import hashlib
import time

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
        
        # Create nurses dataframe directly from the provided data
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
            {"Name": "Maribel Montes Person", "License": "RN", "Email": "maribelperson@gmail.com"},
            {"Name": "Wendy Ferguson", "License": "RN", "Email": "wnelson810@hotmail.com"},
            {"Name": "Daija Nolcox", "License": "RN", "Email": "Daija.nolcox@gmail.com"},
            {"Name": "Marsha Sheakalee", "License": "RN", "Email": "marshasheakalee@aol.com"},
            {"Name": "Saloumeh", "License": "RN", "Email": "sallyvafaei@gmail.com"},
            {"Name": "Amir Mahrabkhani", "License": "NP", "Email": "amirmahrabi123@gmail.com"},
            {"Name": "Ali Gludt", "License": "NP", "Email": "jillephillips@yahoo.com"},
            {"Name": "MJ Chevalier", "License": "NP", "Email": "layannakai@gmail.com"},
            {"Name": "Sarah Bremer", "License": "RN", "Email": "christinalackland@gmail.com"},
            {"Name": "Ashley Pope", "License": "NP", "Email": "mmgalam@yahoo.com"},
            {"Name": "Joyce Jaugar", "License": "RN", "Email": "info@youthfulpractice.com"},
            {"Name": "Leslie Nichols", "License": "RN/NP", "Email": "heathermmott@gmail.com"},
            {"Name": "Jessica Hojaij", "License": "RN", "Email": "cherylannrn@aol.com"},
            {"Name": "Danelle Hamilton", "License": "NP", "Email": "Dhamilton876@gmail.com"},
            {"Name": "Izza Marie Yeed", "License": "RN", "Email": "ftan08@gmail.com"},
            {"Name": "Katherine Oganesyan", "License": "NP", "Email": "oganesyankatherine@gmail.com"}
        ]
        
        # Convert to the format expected by the rest of the code
        nurses_data_formatted = []
        states = ["CA", "TX", "NY", "FL", "IL", "PA", "OH", "MI", "GA", "NC"]  # Sample states
        experience_levels = ["New Graduate", "1-3 years", "3-5 years", "5+ years"]
        
        import random
        
        for idx, nurse in enumerate(nurse_data):
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
                "Addt'l Service Notes": f"Experienced in {random.choice(['medical aesthetics', 'cosmetic procedures', 'skincare treatments'])}"
            })
        
        nurses_df = pd.DataFrame(nurses_data_formatted)
        
        return doctors_df, nurses_df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None

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
        
        # Create base prompt
        prompt = f"""
        You are an Operations Manager at Moxie tasked with matching medical directors with nurses.
        
        Doctor Information:
        - Name: {doctor['First Name']} {doctor['Last Name']}
        - Email: {doctor['Email']}
        - State: {doctor['Residing State  (Lives In)']}
        - Onboarded: {doctor['Create Date']}
        """
        
        # Add filter requirements to the prompt
        if filters.get("experience"):
            prompt += f"\n\nPreference for nurses with experience level: {filters['experience']}"
            
        if filters.get("location") == "Same State Only":
            prompt += "\nLocation requirement: Only include nurses in the same state as the doctor."
        elif filters.get("location") == "Nearby States Acceptable":
            prompt += "\nLocation preference: Prioritize nurses in the same state, but nearby states are acceptable."
            
        if filters.get("requirements") and filters.get("requirements").strip():
            prompt += f"\n\nAdditional requirements to consider:\n{filters['requirements']}"
        
        prompt += """
        
        Using the doctor information above, analyze the following nurse candidates and identify the top 3 best matches based on:
        1. Location match (highest priority - same state is ideal)
        2. Experience level compatibility (experienced doctors can mentor newer nurses)
        3. Service offering alignment
        4. Any specific notes or requirements mentioned
        
        For each match, provide:
        1. The nurse's name
        2. Contact information
        3. A detailed explanation of why they're a good match (be specific about shared location, services, experience level)
        4. A match score out of 10
        
        Available Nurses:
        """
        
        # Add nurse candidates - prioritize by filters
        filtered_nurses = nurses_df.copy()
        
        # Apply experience filter if specified
        if filters.get("experience") and filters.get("experience") != "Any":
            filtered_nurses = filtered_nurses[
                filtered_nurses['Experience Level  '].str.contains(filters.get("experience"), na=False)
            ]
        
        # Handle location filtering
        if filters.get("location") == "Same State Only":
            same_state_nurses = filtered_nurses[filtered_nurses['State (MedSpa Premise)'] == doctor['Residing State  (Lives In)']]
            selected_nurses = same_state_nurses.head(20)
        else:
            same_state_nurses = filtered_nurses[filtered_nurses['State (MedSpa Premise)'] == doctor['Residing State  (Lives In)']]
            other_nurses = filtered_nurses[filtered_nurses['State (MedSpa Premise)'] != doctor['Residing State  (Lives In)']]
            
            # If "Nearby States" is selected, we could implement a more sophisticated 
            # state proximity filter here in the future
            
            selected_nurses = pd.concat([same_state_nurses.head(10), other_nurses.head(10)])
        
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
        
        for _, nurse in selected_nurses.iterrows():
            # Safe extraction of fields
            nurse_name = str(nurse['Ticket Number Counter']) if pd.notna(nurse['Ticket Number Counter']) else "Unknown"
            nurse_email = str(nurse['Bird Eats Bug Email']) if pd.notna(nurse['Bird Eats Bug Email']) else "No email"
            nurse_license = str(nurse['Provider License Type']) if pd.notna(nurse['Provider License Type']) else "Unknown"
            nurse_experience = str(nurse['Experience Level  ']) if pd.notna(nurse['Experience Level  ']) else "Unknown"
            nurse_state = str(nurse['State (MedSpa Premise)']) if pd.notna(nurse['State (MedSpa Premise)']) else "Unknown"
            nurse_services = str(nurse['Services Provided']) if pd.notna(nurse['Services Provided']) else "None specified"
            nurse_notes = str(nurse['Addt\'l Service Notes']) if pd.notna(nurse['Addt\'l Service Notes']) else "None"
            
            # Append to prompt without using f-string for the notes field
            prompt += f"""
            Nurse:
            - Name: {nurse_name}
            - Email: {nurse_email}
            - License Type: {nurse_license}
            - Experience: {nurse_experience}
            - State: {nurse_state}
            - Services: {nurse_services}
            - Notes: """
            prompt += nurse_notes + "\n\n"
        
        # Add response format instructions
        prompt += """
        Format your response as JSON with the following structure:
        {
            "matches": [
                {
                    "name": "Nurse Name",
                    "email": "nurse@email.com",
                    "match_score": 8.5,
                    "reasoning": "Detailed explanation of why this is a good match"
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
        prompt = """
        You are an Operations Manager at Moxie tasked with matching nurses with medical directors.
        
        Nurse Information:
        """
        prompt += f"""
        - Name: {nurse_name}
        - Email: {nurse_email}
        - License Type: {nurse_license}
        - Experience Level: {nurse_experience}
        - State: {nurse_state}
        - Services: {nurse_services}
        - Additional Notes: """
        prompt += nurse_notes + "\n\n"
        
        # Add filter requirements to the prompt
        if filters.get("onboarding") and filters.get("onboarding") != "Any":
            prompt += f"\nPreference for medical directors who {filters['onboarding']}"
            
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
        3. Service offering alignment
        4. Any specific notes or requirements mentioned
        
        For each match, provide:
        1. The doctor's name
        2. Contact information
        3. A detailed explanation of why they're a good match (be specific about shared location, potential service alignment, experience level)
        4. A match score out of 10
        
        Available Medical Directors:
        """
        
        # Filter doctors based on criteria
        filtered_doctors = doctors_df.copy()
        
        # Apply location filter
        if filters.get("location") == "Same State Only" and nurse_state != "Unknown":
            filtered_doctors = filtered_doctors[filtered_doctors['Residing State  (Lives In)'] == nurse_state]
        
        # Apply keyword filter from service requirements if specified
        if filters.get("service_requirements") and filters.get("service_requirements").strip():
            keywords = filters.get("service_requirements").lower().split()
            filtered_list = []
            
            for _, doctor in filtered_doctors.iterrows():
                doctor_info = f"{doctor['First Name']} {doctor['Last Name']} {doctor['Email']} {doctor['Residing State  (Lives In)']}"
                match_count = sum(1 for keyword in keywords if keyword.lower() in doctor_info.lower())
                if match_count > 0:
                    filtered_list.append(doctor)
            
            if filtered_list:
                filtered_doctors = pd.DataFrame(filtered_list)
        
        # If filters resulted in no doctors, fall back to original selection method
        if filtered_doctors.empty:
            filtered_doctors = doctors_df
            prompt += "\nNote: No medical directors matched all specified filters, so showing a general selection.\n\n"
        
        # Select doctors to include
        if nurse_state != "Unknown":
            same_state_doctors = filtered_doctors[filtered_doctors['Residing State  (Lives In)'] == nurse_state]
            other_doctors = filtered_doctors[filtered_doctors['Residing State  (Lives In)'] != nurse_state]
            selected_doctors = pd.concat([same_state_doctors.head(10), other_doctors.head(10)])
        else:
            selected_doctors = filtered_doctors.head(20)
        
        for _, doctor in selected_doctors.iterrows():
            doctor_info = f"""
            Doctor:
            - Name: {doctor['First Name']} {doctor['Last Name']}
            - Email: {doctor['Email']}
            - State: {doctor['Residing State  (Lives In)']}
            - Onboarded: {doctor['Create Date']}
            
            """
            prompt += doctor_info
        
        # Add response format instructions
        prompt += """
        Format your response as JSON with the following structure:
        {
            "matches": [
                {
                    "name": "Dr. Name",
                    "email": "doctor@email.com",
                    "match_score": 8.5, 
                    "reasoning": "Detailed explanation of why this is a good match"
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
        3. A detailed explanation of why they're a good match
        4. A match score out of 10
        
        Format your response as JSON with the following structure:
        {
            "person_type": "doctor" or "nurse",
            "matches": [
                {
                    "name": "Name",
                    "email": "email@example.com",
                    "match_score": 8.5,
                    "reasoning": "Detailed explanation of why this is a good match"
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
#@st.cache_data(ttl=3600)  # Cache for 1 hour
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
                system="You are a medical staffing expert at Moxie. You help match medical directors with nurses based on their location, experience, services offered, and other relevant factors. You always respond in JSON format as specified in the prompts.",
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
        selected_doctor = st.selectbox("Select Medical Director:", [""] + doctor_names)
        
        # Add specific filtering criteria
        st.subheader("Nurse Preference Filters")
        col1, col2 = st.columns(2)
        with col1:
            exp_filter = st.selectbox("Experience Level:", ["Any", "New Graduate", "1-3 years", "3-5 years", "5+ years"])
        with col2:
            location_preference = st.radio("Location Priority:", ["Same State Only", "Nearby States Acceptable", "Any Location"])
        
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
                                st.markdown(
                                    f"""<div class="match-card">
                                    <h4>{match['name']} <span style="float:right; background-color:#4CAF50; color:white; padding:5px 10px; border-radius:15px;">Match Score: {match['match_score']}/10</span></h4>
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
        selected_nurse = st.selectbox("Select Nurse:", [""] + nurse_names)
        
        # Add specific filtering criteria
        st.subheader("MD Preference Filters")
        col1, col2 = st.columns(2)
        with col1:
            onboarding_filter = st.radio("Onboarding Support:", ["Any", "Needs Significant Support", "Minimal Support Needed"])
        with col2:
            location_preference = st.radio("Location Priority:", ["Same State Only", "Nearby States Acceptable", "Any Location"])
        
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
                            "onboarding": onboarding_filter if onboarding_filter != "Any" else None,
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
                                st.markdown(
                                    f"""<div class="match-card">
                                    <h4>{match['name']} <span style="float:right; background-color:#4CAF50; color:white; padding:5px 10px; border-radius:15px;">Match Score: {match['match_score']}/10</span></h4>
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
                <li>Any special requirements or notes</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Add more specific options for manual entry
        col1, col2 = st.columns(2)
        with col1:
            person_type = st.radio("This person is a:", ["Unknown", "Medical Director", "Nurse"])
        
        user_input = st.text_area("Enter professional information:", height=150)
        
        matching_priorities = st.text_area(
            "Specific matching priorities:", 
            height=100,
            placeholder="E.g., Must be in same state, looking for someone with Botox experience, etc."
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
                                st.markdown(
                                    f"""<div class="match-card">
                                    <h4>{match['name']} <span style="float:right; background-color:#4CAF50; color:white; padding:5px 10px; border-radius:15px;">Match Score: {match['match_score']}/10</span></h4>
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
    with st.expander("How the ChatGPT Matching System Works"):
        st.markdown("""
        This matching system uses ChatGPT, OpenAI's advanced AI assistant, to intelligently match medical directors with nurses based on multiple factors:
        
        1. **Location Matching**: ChatGPT prioritizes professionals in the same state to ensure licensing compatibility.
        
        2. **Experience Level Compatibility**: ChatGPT considers the experience levels of both professionals, often matching experienced doctors with newer nurses who need mentorship.
        
        3. **Service Alignment**: ChatGPT analyzes the services provided by nurses and looks for doctors with relevant expertise.
        
        4. **Notes Analysis**: ChatGPT reviews additional notes for special requirements or preferences that might impact matching.
        
        5. **Match Score**: ChatGPT provides a score out of 10 with detailed reasoning to explain why each match works well.
        
        The system intelligently processes information from your CSV files to find the most compatible professional pairings based on context and details that might not be captured by a simple algorithm.
        
        **Technical Performance Features**:
        
        - Results are cached to improve performance and reduce API usage
        - System automatically switches to a faster AI model during high demand periods
        - Smart filtering analyzes professional requirements and prioritizes the best matches
        """)
