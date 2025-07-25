import ast
import json
import openai
import orjson
import os
import pandas as pd
import re
import streamlit as st
import time

from prompt_utils import create_prompt
from streamlit_gsheets import GSheetsConnection
from sql_queries import TICKETS_QUERY, AVAILABLE_MDS_QUERY


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
    subject = str(provider['SUBJECT'])
    provider_email = str(provider['PROVIDER_EMAIL'])
    ticket_status = str(provider['TICKET_STATUS'])
    ticket_priority = str(provider['TICKET_PRIORITY'])
    kick_off_date = str(provider['KICK_OFF_DATE'])
    provider_license_type = str(provider['PROVIDER_LICENSE_TYPE']) 
    provider_experience_level = str(provider['PROVIDER_EXPERIENCE_LEVEL'])
    provider_state = str(provider['PROVIDER_STATE']) 
    provider_md_location_preference = get_clean_value(provider['PROVIDER_MD_LOCATION_PREFERENCE'], "")
    provider_services = get_clean_value(provider['PROVIDER_SERVICES'], "None Specified") 
    provider_future_services = get_clean_value(provider['PROVIDER_FUTURE_SERVICES'], "")
    provider_additional_services = get_clean_value(provider["PROVIDER_ADDITIONAL_SERVICES"], "") 
    
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
                <h4>{subject}</h4>
                <p><strong>Ticket Status:</strong> {ticket_status}</p>
                <p><strong>Ticket Priority:</strong> {ticket_priority}</p>
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
    Converts a list-like string or delimited string of services into HTML badge spans.
    Handles cases where services are passed in as a list string like '["Botox", "Filler"]'
    or as a comma/semicolon-separated string.
    """
    if not service_string or service_string == "None specified":
        return ""

    try:
        # Try parsing as a list string (e.g., '["Botox", "Filler"]')
        services = ast.literal_eval(service_string)
        if isinstance(services, list):
            return ' '.join(f'<span class="service-badge">{s.strip()}</span>' for s in services if s)
    except (ValueError, SyntaxError):
        pass

    # Fallback: treat as delimited string
    delimiter = ';' if ';' in service_string else ','
    services = [s.strip() for s in service_string.split(delimiter)]
    return ' '.join(f'<span class="service-badge">{s}</span>' for s in services if s)

def get_clean_value(value, default="Unknown"):
    """
    Gets a clean value from a string, handling common formatting issues.
    """
    if pd.isna(value) or str(value).strip().lower() in {"n/a", "na", ""}:
        return default
    return str(value).strip()

# Function to call OpenAI API with fallback to GPT-3.5
def query_openai(prompt, api_key, max_retries=2):
    """Call the OpenAI API and return the raw response text along with
    the model and parameters used. Falls back to GPT-3.5 if the primary
    model fails.
    """

    primary_model = "gpt-4-turbo-preview"
    fallback_model = "gpt-3.5-turbo"
    
    for attempt in range(max_retries):
        try:
            # Choose model based on the attempt number
            current_model = primary_model if attempt == 0 else fallback_model

            params = {
                "model": current_model,
                "max_tokens": 4000,
                "temperature": 0.2,
            }

            # Initialize the client
            client = openai.OpenAI(api_key=openai_api_key)

            # Make the API request
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": """
                        You are a medical staffing expert at Moxie. You help match nurses with medical
                        directors based on their location, experience, services offered, personality traits,
                        and other relevant factors. You always prioritize state licensing requirements (especially
                        for California) and capacity limitations. You always respond in JSON format as specified
                        in the prompts.
                    """},
                    {"role": "user", "content": prompt},
                ],
                **params,
            )

            content = response.choices[0].message.content.strip()

            return content, params
            
        except Exception as e:
            error_str = str(e)

            if attempt == 0 and "overloaded_error" in error_str:
                st.warning("Primary AI model is busy. Trying with a faster model...")
                time.sleep(1)
                continue

            elif attempt == max_retries - 1:
                st.error(f"API error: {error_str}")
                return orjson.dumps({"error": f"API error: {error_str}"}), {"model": current_model}

            else:
                st.error(f"API error: {error_str}")
                return orjson.dumps({"error": f"API error: {error_str}"}), {"model": current_model}

########################################################
# Page config
########################################################
st.set_page_config(page_title="Moxie Provider-MD Matching", layout="wide")

# Load external CSS
with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

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
    st.markdown("<h1 class='main-header'>Moxie Provider-MD Matching System</h1>", unsafe_allow_html=True)
    st.markdown("<div class='powered-by'>Powered by ChatGPT</div>", unsafe_allow_html=True)
    
    # Get OpenAI API key from environment variable
    openai_api_key = os.getenv("OPENAI_API_KEY", "")

    # Connect to Snowflake
    conn = st.connection("snowflake")

    # Load and cache data
    @st.cache_data
    def load_md_data():
        try: 
            doctors_df = conn.query(AVAILABLE_MDS_QUERY, ttl=0)
            return doctors_df
        except Exception as e:
            return None

    @st.cache_data
    def load_provider_data():
        try: 
            providers_df = conn.query(TICKETS_QUERY, ttl=0)
            return providers_df
        except Exception as e:
            return None

    doctors_df = load_md_data()
    providers_df = load_provider_data()

    # Display error if data is not loaded
    if doctors_df is None:
        st.error("Failed to load MD data. Contact Sinthuja to troubleshoot.")
    if providers_df is None:
        st.error("Failed to load provider data. Contact Sinthuja to troubleshoot.")

    # Select a provider to match
    st.markdown("<h3 class='subheader'>Provider Selection</h3><br>", unsafe_allow_html=True)

    # Display how many tickets for matching were found
    st.info(f"Found {len(providers_df)} tickets in pending status.")

    # Create a new column for display: "Subject - Status"
    providers_df["DISPLAY"] = providers_df["SUBJECT"] + " - " + providers_df["TICKET_STATUS"]

    # Sort by TICKET_STATUS
    providers_sorted = providers_df.sort_values("TICKET_STATUS", ascending=False)

    # Initialize dict to keep matches for each provider
    if "provider_matches" not in st.session_state:
        st.session_state["provider_matches"] = {}

    # Display a dropdown with a blank option at the beginning
    selected_provider = st.selectbox(
        "Select a provider to match:",
        [""] + providers_sorted["DISPLAY"].tolist(),
        key="selected_provider",
    )

    # Filter the dataframe only if a provider is selected
    if selected_provider:
        provider_data = providers_df[providers_df["DISPLAY"] == selected_provider]
        provider = provider_data.iloc[0]
        display_provider_details(provider)

        provider_key = provider["PROVIDER_EMAIL"]
        matches_by_provider = st.session_state["provider_matches"]
        if provider_key in matches_by_provider:
            st.session_state["last_matches"] = matches_by_provider[provider_key]
        else:
            st.session_state.pop("last_matches", None)
    else:
        provider = None
        st.session_state.pop("last_matches", None)

    service_requirements = st.text_area("Any additional requirements or preferences:", height=100, 
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
                        "service_requirements": service_requirements
                    }
                )

                if error:
                    st.error(error)
                else:
                    query_start = time.time()
                    raw_response, model_params = query_openai(prompt, openai_api_key)
                    duration = time.time() - query_start

                    matches = None
                    cleaned_response = clean_json_response(raw_response)
                    try:
                        matches = json.loads(cleaned_response)
                    except json.JSONDecodeError as e:
                        st.error(f"Error parsing JSON response here: {str(e)}")
                        st.text(f"Raw response: {raw_response}")
                        matches = None

                    # Cache relevant information in session state for logging
                    st.session_state["last_matches"] = matches
                    st.session_state["prompt_text"] = prompt
                    st.session_state["model_params"] = model_params
                    st.session_state["raw_results"] = cleaned_response
                    st.session_state["provider_data"] = provider.to_dict()
                    st.session_state["query_start"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(query_start))
                    st.session_state["query_duration"] = round(duration, 2)

                    provider_key = provider["PROVIDER_EMAIL"]
                    st.session_state["provider_matches"][provider_key] = matches

                    provider_key = provider["PROVIDER_EMAIL"]
                    st.session_state["provider_matches"][provider_key] = matches

                    provider_key = provider["PROVIDER_EMAIL"]
                    st.session_state["provider_matches"][provider_key] = matches

    if "last_matches" in st.session_state:    
        # Display matches
        st.markdown(f"<h3 class='subheader'>Top MD Matches for {provider['SUBJECT']}</h3><br>", unsafe_allow_html=True)
        
        matches = st.session_state["last_matches"]
        for match in matches.get("matches", []):
            # Determine score color class
            score = float(match['match_score'])
            score_class = "high-score" if score >= 8.0 else "medium-score" if score >= 6.0 else "low-score"
            
            # Find the MD in the dataframe to get their traits and state
            md_email = match['email']
            md_row = doctors_df[
                doctors_df.apply(
                    lambda row: md_email.lower() in row['EMAIL'].lower(), 
                    axis=1
                )
            ].iloc[0] 

            md_traits = get_clean_value(md_row.get('MD_TRAITS', ''), '')
            md_bio = get_clean_value(md_row.get('MD_BIO', ''), 'No bio provided')

            # Build the match card with traits, bio, and fixed location included
            st.markdown(
                f"""<div class="match-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4>{match['name']}</h4>
                    <div class="compatibility-score {score_class}">{match['match_score']}</div>
                </div>
                <p><strong>Email:</strong> {md_row['EMAIL']}</p>
                <p><strong>Capacity:</strong> {match.get('capacity_status', 'Available')}</p>
                <p><strong>Residing State:</strong> <span class="trait-tag state-tag">{md_row['RESIDING_STATE']}</span></p>
                <p><strong>Personality Traits:</strong> {md_row['MD_TRAITS']}</p>
                <div class="match-details">
                    <p><strong>Personal Bio:</strong> {md_bio}</p>
                </div>
                <div class="match-reason">
                    <p><strong>Why this match works:</strong> {match['reasoning']}</p>
                </div>
                </div>""",
                unsafe_allow_html=True
            )
            
        # Collect final decision and feedback
        st.markdown(f"<h3 class='subheader'>Matching Feedback</h3><br>", unsafe_allow_html=True)
        st.markdown("""
            Use this form to provide feedback on the quality and accuracy of the matching algorithm.
            This helps us improve future matches and track performance over time.
        """)
        
        # Clear form state BEFORE rendering
        if st.session_state.get("clear_form"):
            st.session_state["selected_match_names"] = []
            st.session_state["feedback_text"] = ""
            st.session_state["clear_form"] = False

        with st.form("final_match_form"):
            selected_match_names = st.multiselect(
                "Which MDs will you be reaching out to match with this provider? (leave blank if none)",
                [match["name"] for match in matches["matches"]],
                key="selected_match_names"
            )

            feedback = st.text_area(
                "Provide any feedback or rationale on how well the matching process went.",
                placeholder="E.g., Excellent personality alignment. Preferred teaching experience was met.",
                key="feedback_text"
            )

            submit = st.form_submit_button("Submit to Google Sheets")

            if submit:
                conn_gsheet = st.connection("gsheets", type=GSheetsConnection)

                row = {
                    "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "User": st.user.name,
                    "Provider": provider["SUBJECT"],
                    "Provider Email": provider["PROVIDER_EMAIL"],
                    "Provider Data": orjson.dumps(st.session_state.get("provider_data", {})),
                    "AI Model": st.session_state.get("model_params", {}).get("model", ""),
                    "Model Params": orjson.dumps(st.session_state.get("model_params", {})),
                    "Raw Results": st.session_state.get("raw_results", ""),
                    "Query Sent At": st.session_state.get("query_start", ""),
                    "Request Duration (s)": st.session_state.get("query_duration", ""),
                    "Selected MD(s)": (
                        orjson.dumps(selected_match_names)
                        if selected_match_names
                        else "None"
                    ),
                    "Feedback": feedback,
                }

                try:
                    # Fetch the latest data each time to avoid overwriting
                    existing_data = conn_gsheet.read(ttl=0)

                    # Add new row
                    new_row_df = pd.DataFrame([row])
                    updated_data = pd.concat([existing_data, new_row_df], ignore_index=True)

                    # Push update
                    conn_gsheet.update(data=updated_data)
                    
                    # Clear any cached data so the next read fetches fresh rows
                    st.toast("✅ Your decision and feedback have been submitted successfully!")

                    time.sleep(2)
                    
                    # Set flag and rerun to clear form on next cycle
                    st.session_state["clear_form"] = True
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Failed to write to Google Sheet: {e}")    # Clear session state
                    