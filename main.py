import hashlib
import json
import openai
import os
import pandas as pd
import re
import streamlit as st
import time

from data_loader import load_data, extract_personality_traits, extract_md_preferences
from prompt_utils import create_prompt

########################################################
# Helper functions
########################################################
def clean_json_response(response):
    # Remove code fences if present
    response = re.sub(r"^```(?:json)?|```$", "", response.strip(), flags=re.MULTILINE)
    # Remove any leading/trailing whitespace again
    return response.strip()

########################################################
# Page config
########################################################
st.set_page_config(page_title="Moxie Provider-MD Matching", layout="wide")

# Load external CSS
with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

########################################################
# Password screen
########################################################
# Initialize session state for password
if 'password_correct' not in st.session_state:
    st.session_state['password_correct'] = False

# Simple password screen
if not st.session_state['password_correct']:
    st.markdown("""
    <div class="password-container">
        <h2 class="password-header">Moxie Provider-MD Matching System</h2>
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

########################################################
# Main application (only runs if password is correct)
########################################################
# Get OpenAI API key from environment variable
openai_api_key = os.getenv("OPENAI_API_KEY", "")

st.markdown("<h1 class='main-header'>Moxie Provider-MD Matching System</h1>", unsafe_allow_html=True)
st.markdown("<div class='powered-by'>Powered by ChatGPT</div>", unsafe_allow_html=True)

# Load data
@st.cache_data
def cached_load_data():
    return load_data()

# Create a hash from the prompt for caching
def get_prompt_hash(prompt):
    return hashlib.md5(prompt.encode()).hexdigest()

# Cache the Open API responses
#@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_openai_api(prompt_hash, prompt, openai_api_key):
    return query_openai(prompt, openai_api_key)

# Function to call OpenAI API with fallback to GPT-3.5
def query_openai(prompt, api_key, max_retries=2):
    # First try with the primary model (GPT-4)
    primary_model = "gpt-4-turbo-preview"
    fallback_model = "gpt-3.5-turbo"
    
    for attempt in range(max_retries):
        try:
            # Choose model based on the attempt number
            current_model = primary_model if attempt == 0 else fallback_model
            
            # Initialize the client
            client = openai.OpenAI(api_key=openai_api_key)
            
            # Make the API request
            response = client.chat.completions.create(
                model=current_model,
                max_tokens=4000,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": "You are a medical staffing expert at Moxie. You help match nurses with medical directors based on their location, experience, services offered, personality traits, and other relevant factors. You always prioritize state licensing requirements (especially for California) and capacity limitations. You always respond in JSON format as specified in the prompts."},
                    {"role": "user", "content": prompt}
                ]
            )
            # Get the content and clean it
            content = response.choices[0].message.content.strip()
            
            # Try to parse the JSON
            try:
                parsed = json.loads(content)
                # Return the parsed JSON directly without re-serializing
                return parsed
            except json.JSONDecodeError:
                # If parsing fails, return the cleaned content as is
                return content
            
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
                return {"error": f"API error: {error_str}"}
                
            # If this was the primary model but not an overloaded error
            else:
                st.error(f"API error: {error_str}")
                return {"error": f"API error: {error_str}"}

# Display nurse information in a nice way
def display_nurse_details(nurse):
    nurse_name = str(nurse['Ticket Number Counter']) if pd.notna(nurse['Ticket Number Counter']) else "Unknown"
    nurse_license = str(nurse['Provider License Type']) if pd.notna(nurse['Provider License Type']) else "Unknown"
    nurse_experience = str(nurse['Experience Level  ']) if pd.notna(nurse['Experience Level  ']) else "Unknown"
    nurse_state = str(nurse['State (MedSpa Premise)']) if pd.notna(nurse['State (MedSpa Premise)']) else "Unknown"
    nurse_services = str(nurse['Services Provided']) if pd.notna(nurse['Services Provided']) else "None specified"
    
    # Create service tags
    services_html = ""
    if nurse_services and nurse_services != "None specified":
        services = [service.strip() for service in nurse_services.split(';' if ';' in nurse_services else ',')]
        for service in services:
            if service:
                services_html += f'<span class="service-badge">{service}</span> '
    
    # Display state info with special style for California
    state_html = f'<span class="trait-tag state-tag">{nurse_state}</span>'
    
    # Add California restriction warning if applicable
    ca_restriction = ""
    if nurse_state.upper() == "CA":
        ca_restriction = """
        <div class="state-restrictions">
            <strong>California Restriction:</strong> This nurse can only be matched with medical directors in California due to state licensing requirements.
        </div>
        """
    st.markdown(f"""
        <div class="nurse-info">
            <div class="nurse-detail">
                <h4>License & Experience</h4>
                <p><strong>License:</strong> {nurse_license}</p>
                <p><strong>Experience:</strong> {nurse_experience}</p>
            </div>
            <div class="nurse-detail">
                <h4>Location</h4>
                {state_html}
                {ca_restriction or ''}
            </div>
        </div>
        """, unsafe_allow_html=True)

########################################################
# Main application content
########################################################
# load and cache data
@st.cache_data
def cached_load_data():
    return load_data()

doctors_df, nurses_df = cached_load_data()

# error if data is not loaded
if doctors_df is None or nurses_df is None:
    st.error("Failed to load data. Please check the data files.")

# Add specific filtering criteria
st.markdown("<h3 class='subheader'>Provider Selection</h3><br>", unsafe_allow_html=True)
# Try to read column names in a case-insensitive way
def get_column_case_insensitive(df, column_name):
    """Get the actual case of a column name regardless of case."""
    for col in df.columns:
        if col.lower() == column_name.lower():
            return col
    return None

# Find nurse identifiers using multiple possible columns
nurse_name_col = get_column_case_insensitive(nurses_df, 'Ticket Number Counter')
nurse_email_col = get_column_case_insensitive(nurses_df, 'Bird Eats Bug Email')

# Extract nurse identifiers, prioritizing names but falling back to emails
nurse_identifiers = []

# Try different columns to find identifiers
if nurse_email_col:  # First, collect emails since they're likely to be more reliable
    for _, row in nurses_df.iterrows():
        if pd.notna(row[nurse_email_col]):
            email = str(row[nurse_email_col]).strip()
            if email and '@' in email:  # Simple validation to ensure it's an email
                nurse_identifiers.append(email)

# If we also have names, prefer those but keep emails as fallback
if nurse_name_col:
    name_based_identifiers = []
    for _, row in nurses_df.iterrows():
        if pd.notna(row[nurse_name_col]):
            name = str(row[nurse_name_col]).strip()
            if name:  # Only add non-empty names
                name_based_identifiers.append(name)
    
    # If we have names, use those instead of emails
    if name_based_identifiers:
        nurse_identifiers = name_based_identifiers

# Display the dropdown
if not nurse_identifiers:
    st.warning("No nurse identifiers found in the data. Please check your data file's 'Ticket Number Counter' or 'Bird Eats Bug Email' columns.")
    selected_nurse = st.selectbox("Select Nurse:", ["No nurses available"])
    st.stop()  # Stop execution if no nurses are available
else:
    # Display how many nurses were found
    st.info(f"Found {len(nurse_identifiers)} nurses in the data.")
    # Sort and add a blank option at the beginning
    selected_nurse = st.selectbox("Select Nurse:", [""] + sorted(nurse_identifiers))

# Find the selected nurse in the dataframe - checking both name and email columns
if selected_nurse and selected_nurse != "No nurses available":
    nurse_row = None
    
    # Try to find by name first
    if nurse_name_col:
        name_matches = nurses_df[
            nurses_df.apply(
                lambda row: pd.notna(row[nurse_name_col]) and selected_nurse.lower() in str(row[nurse_name_col]).lower(),
                axis=1
            )
        ]
        if not name_matches.empty:
            nurse_row = name_matches
    
    # If not found by name, try email
    if (nurse_row is None or nurse_row.empty) and nurse_email_col:
        email_matches = nurses_df[
            nurses_df.apply(
                lambda row: pd.notna(row[nurse_email_col]) and selected_nurse.lower() in str(row[nurse_email_col]).lower(),
                axis=1
            )
        ]
        if not email_matches.empty:
            nurse_row = email_matches
    
    if nurse_row is not None and not nurse_row.empty:
        nurse = nurse_row.iloc[0]
        display_nurse_details(nurse)

# Add specific filtering criteria
st.markdown("<h3 class='subheader'>MD Selection</h3><br>", unsafe_allow_html=True)
# Display how many MDs were found
st.info(f"Found {len(doctors_df)} medical directors in the data.")

with st.container():
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
    
    # Determine location options based on nurse state
    if selected_nurse and nurse_row is not None and not nurse_row.empty:
        nurse_state = str(nurse_row.iloc[0]['State (MedSpa Premise)']).upper() if pd.notna(nurse_row.iloc[0]['State (MedSpa Premise)']) else "Unknown"
        
        if nurse_state == "CA":
            st.info("California nurses can only be matched with California medical directors due to state requirements.")
            location_preference = "Same State Only"
        else:
            location_preference = st.radio("Location Priority:", ["Same State Only", "Nearby States Acceptable", "Any Location"])
    else:
        location_preference = st.radio("Location Priority:", ["Same State Only", "Nearby States Acceptable", "Any Location"])
    
    st.markdown('</div>', unsafe_allow_html=True)

service_requirements = st.text_area("Specific Requirements or Preferences:", height=100, 
                                placeholder="E.g., Looking for a mentor in fillers, prefer someone with teaching experience, etc.")

if selected_nurse and selected_nurse != "No nurses available" and st.button("Find Matching Medical Directors"):
    if not openai_api_key:
        st.error("API key is not configured. Please set the OPENAI_API_KEY environment variable.")
    else:
        with st.spinner("Finding the best medical director matches..."):
            prompt, error = create_prompt(
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
                
                # Call OpenAI API with caching
                response = cached_openai_api(prompt_hash, prompt, openai_api_key)
                
                matches = None
                
                if isinstance(response, dict):
                    matches = response
                elif isinstance(response, str):
                    cleaned_response = clean_json_response(response)
                    try:
                        matches = json.loads(cleaned_response)
                    except json.JSONDecodeError as e:
                        st.error(f"Error parsing JSON response here: {str(e)}")
                        st.text(f"Raw response: {response}")
                        matches = None
                else:
                    st.error("The AI did not return a valid JSON response. Please try again or check your API key/usage.")
                    st.text(f"Raw response: {response}")

                if matches:    
                    # Display matches
                    st.markdown(f"<h3>Top Medical Director Matches for {selected_nurse}</h3>", unsafe_allow_html=True)
                    
                    for match in matches.get("matches", []):
                        # Determine score color class
                        score = float(match['match_score'])
                        score_class = "high-score" if score >= 8.0 else "medium-score" if score >= 6.0 else "low-score"
                        
                        # Find the MD in the dataframe to get their traits and state
                        md_name = match['name']
                        md_row = doctors_df[
                            doctors_df.apply(
                                lambda row: md_name.lower() in f"{row['First Name']} {row['Last Name']}".lower(), 
                                axis=1
                            )
                        ]
                        
                        # Get MD traits and location if available
                        traits_html = ""
                        states_html = ""
                        
                        if not md_row.empty:
                            md = md_row.iloc[0]
                            traits = extract_personality_traits(md.get('Personality Traits', ''))
                            
                            # Get states
                            states = md.get('States List', [])
                            if not states and 'Residing State  (Lives In)' in md:
                                states = [md.get('Residing State  (Lives In)', '')]
                            
                            # Create state tags
                            for state in states:
                                if state and pd.notna(state):
                                    state_class = "trait-tag state-tag"
                                    if state.upper() == "CA":
                                        state_class += " warning-tag"
                                    states_html += f'<span class="{state_class}">{state}</span> '
                            
                            # Create trait tags
                            for trait in traits:
                                if trait.strip():
                                    traits_html += f'<span class="trait-tag">{trait.strip()}</span> '
                        
                        # Build the match card with traits and fixed location included
                        st.markdown(
                            f"""<div class="match-card">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h4>{match['name']}</h4>
                                <div class="compatibility-score {score_class}">{match['match_score']}</div>
                            </div>
                            <p><strong>Contact:</strong> {match['email']}</p>
                            <p><strong>Capacity:</strong> {match.get('capacity_status', 'Available')}</p>
                            <div class="nurse-info">
                                <div class="nurse-detail">
                                    <h4>Location</h4>
                                    {states_html if states_html else "Location not specified"}
                                </div>
                                <div class="nurse-detail">
                                    <h4>Personality Traits</h4>
                                    {traits_html if traits_html else "No traits specified"}
                                </div>
                            </div>
                            <div class="match-reason">
                                <p><strong>Why this match works:</strong> {match['reasoning']}</p>
                            </div>
                            </div>""",
                            unsafe_allow_html=True
                        )

def process_matches(nurses_df, medical_directors_df):
    try:
        # Create the prompt for matching
        prompt = create_prompt(nurses_df, medical_directors_df)
        
        # Get the API key from session state
        api_key = st.session_state.get('openai_api_key')
        if not api_key:
            st.error("Please enter your OpenAI API key first.")
            return None
        
        # Get the response from OpenAI
        response = query_openai(prompt, api_key)
        
        # Try to parse the response as JSON
        try:
            matches = response if isinstance(response, dict) else json.loads(response)
            # Validate the structure of the matches
            if not isinstance(matches, dict):
                st.error("Invalid response format: expected a dictionary")
                return None
                
            if 'matches' not in matches:
                st.error("Invalid response format: missing 'matches' key")
                return None
                
            if not isinstance(matches['matches'], list):
                st.error("Invalid response format: 'matches' must be a list")
                return None
                
            # Validate each match in the list
            for match in matches['matches']:
                required_fields = ['name', 'email', 'match_score', 'reasoning']
                missing_fields = [field for field in required_fields if field not in match]
                if missing_fields:
                    st.error(f"Invalid match format: missing required fields: {', '.join(missing_fields)}")
                    return None
                    
            return matches
            
        except json.JSONDecodeError as e:
            st.error(f"Error parsing JSON response: {str(e)}")
            st.text(f"Raw response: {response}")
            return None
            
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return None