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
    """
    Cleans the JSON response from the OpenAI API
    """
    # Remove code fences if present
    response = re.sub(r"^```(?:json)?|```$", "", response.strip(), flags=re.MULTILINE)
    # Remove any leading/trailing whitespace again
    return response.strip()

def display_provider_details(provider):
    """
    Displays the provider details nicely formatted
    """
    ticket_name = str(provider['Ticket name'])
    provider_email = str(provider['Bird Eats Bug Email'])
    ticket_status = str(provider['Ticket status'])
    priority = str(provider['Priority'])
    kick_off_date = str(provider['Kick-Off Date'])
    provider_license_type = str(provider['Provider License Type']) 
    provider_experience_level = str(provider['Experience Level  '])
    provider_state = str(provider['State (MedSpa Premise)']) 
    provider_md_location_preference = get_clean_value(provider['MD Location Preference (state)'], "")
    provider_services = get_clean_value(provider['Services Provided'], "None Specified") 
    provider_future_services = get_clean_value(provider['FUTURE Services (if known)'], "")
    provider_additional_services = get_clean_value(provider["Addt'l Service Notes"], "")
    
    # Create service tags
    services_html = generate_service_badges(provider_services)
    future_services_html = generate_service_badges(provider_future_services)
    
    # Display state info with special style for California
    state_html = f'<span class="trait-tag state-tag">{provider_state}</span>'
    
    # Add California restriction warning if applicable
    ca_restriction = ""
    if provider_state == "California":
        ca_restriction = """
        <div class="state-restrictions">
            <strong>California Restriction:</strong> This nurse can only be matched with medical directors in California due to state licensing requirements.
        </div>
        """

    st.markdown(f"""
        <div class="nurse-info">
            <div class="nurse-detail">
                <h4>{ticket_name}</h4>
                <p><strong>Ticket Status:</strong> {ticket_status}</p>
                <p><strong>Ticket Priority:</strong> {priority}</p>
                <p><strong>Kick-Off Date:</strong> {kick_off_date}</p>
                <p><strong>Email:</strong> {provider_email}</p>
                <p><strong>License:</strong> {provider_license_type}</p>
                <p><strong>Experience:</strong> {provider_experience_level}</p>
                <p><strong>State:</strong> {state_html} {ca_restriction or ''}</p>
                <p><strong>MD Location Preference:</strong> {provider_md_location_preference}</p>
                <P><p><strong>Services:</strong> {services_html}</P>
                <p><strong>Future Services:</strong> {future_services_html}</p>
                <p><strong>Additional Notes:</strong> {provider_additional_services}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

def generate_service_badges(service_string):
    """
    Converts a semicolon- or comma-separated string of services into HTML badge spans.
    """
    if service_string and service_string != "None specified":
        delimiter = ';' if ';' in service_string else ','
        services = [s.strip() for s in service_string.split(delimiter)]
        return ' '.join(f'<span class="service-badge">{s}</span>' for s in services if s)
    return ""

def get_clean_value(value, default="Unknown"):
    """
    Gets a clean value from a string, handling common formatting issues.
    """
    if pd.isna(value) or str(value).strip().lower() in {"n/a", "na", ""}:
        return default
    return str(value).strip()

# Try to read column names in a case-insensitive way
def get_column_case_insensitive(df, column_name):
    """Get the actual case of a column name regardless of case."""
    for col in df.columns:
        if col.lower() == column_name.lower():
            return col
    return None

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

# Cache the Open API responses for 1 hour
@st.cache_data(ttl=3600) 
def cached_openai_api(prompt, openai_api_key):
    return query_openai(prompt, openai_api_key)

########################################################
# Page config
########################################################
st.set_page_config(page_title="Moxie Provider-MD Matching", layout="wide")

# Load external CSS
with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>Moxie Provider-MD Matching System</h1>", unsafe_allow_html=True)
st.markdown("<div class='powered-by'>Powered by ChatGPT</div>", unsafe_allow_html=True)

########################################################
# Require login
########################################################
def login_screen():
    st.markdown("""
        <div>
            <h2 class="private-header">This app is private.</h2>
            <p class="login-text">Please log in with your Google account to continue.</p>
    """, unsafe_allow_html=True)
    st.button("🔐 Log in with Google", on_click=st.login)
    st.markdown("</div>", unsafe_allow_html=True)

if not st.user.is_logged_in:
    login_screen()
else:
    st.markdown(f"""<h2 class='welcome-header'>Welcome, {st.user.name}!</h2>""", unsafe_allow_html=True)
    st.button("Log out", on_click=st.logout)

########################################################
# Main application (only runs if user is logged in)
########################################################
    # Get OpenAI API key from environment variable
    openai_api_key = os.getenv("OPENAI_API_KEY", "")

    # Load and cache data
    @st.cache_data
    def load_data():
        try: 
            doctors_df = pd.read_csv('md_hubspot.csv')
            providers_df = pd.read_csv('matching_tickets.csv')
            return doctors_df, providers_df
        
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return None, None 

    doctors_df, providers_df = load_data()

    # Display error if data is not loaded
    if doctors_df is None:
        st.error("Failed to load MD data. Please check the data files.")
    if providers_df is None:
        st.error("Failed to load provider data. Please check the data files.")

    # Select a provider to match
    st.markdown("<h3 class='subheader'>Provider Selection</h3><br>", unsafe_allow_html=True)

    # Display how many tickets for matching were found
    st.info(f"Found {len(providers_df)} tickets for matching.")

    # Display a dropdown with a blank option at the beginning
    selected_provider = st.selectbox("Select Provider:", [""] + sorted(providers_df["Ticket name"].dropna()))

    # Filter the dataframe only if a provider is selected
    if selected_provider:
        provider_data = providers_df[providers_df["Ticket name"] == selected_provider]
        provider = provider_data.iloc[0]  
        display_provider_details(provider) 
    else:
        provider = None

    # Now look at the MDs to match with
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
        if provider is not None:
            provider_state = str(provider_data['State (MedSpa Premise)'].iloc[0]) 

            if provider_state == "California":
                st.info("California nurses can only be matched with California medical directors due to state requirements.")
                location_preference = "Same State Only"
            else:
                location_preference = st.radio("Location Priority:", ["Same State Only", "Nearby States Acceptable", "Any Location"])
        else:
            location_preference = st.radio("Location Priority:", ["Same State Only", "Nearby States Acceptable", "Any Location"])
        
        st.markdown('</div>', unsafe_allow_html=True)

    service_requirements = st.text_area("Specific Requirements or Preferences:", height=100, 
                                    placeholder="E.g., Looking for a mentor in fillers, prefer someone with teaching experience, etc.")

    if provider is not None and st.button("Find Matching Medical Directors"):
        if not openai_api_key:
            st.error("API key is not configured. Please set the OPENAI_API_KEY environment variable.")
        else:
            with st.spinner("Finding the best medical director matches..."):
                prompt, error = create_prompt( 
                    doctors_df, 
                    provider,
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
                    response = query_openai(prompt, openai_api_key)
                    matches = None
                    
                    # Format the responses
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
                        st.markdown(f"<h3>Top Medical Director Matches for {provider_data}</h3>", unsafe_allow_html=True)
                        
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