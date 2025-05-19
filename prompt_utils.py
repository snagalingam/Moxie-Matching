import pandas as pd
import re
def get_clean_value(value, default="Unknown"):
    """
    Gets a clean value from a string, handling common formatting issues.
    """
    if pd.isna(value) or str(value).strip().lower() in {"n/a", "na", ""}:
        return default
    return str(value).strip()

def create_prompt(doctors_df, provider, filters=None):
    if filters is None:
        filters = {}
    
    # Extract provider information
    ticket_name = str(provider['SUBJECT'])
    provider_email = str(provider['PROVIDER_EMAIL'])
    provider_license_type = str(provider['PROVIDER_LICENSE_TYPE']) 
    provider_experience_level = str(provider['PROVIDER_EXPERIENCE_LEVEL'])
    provider_state = str(provider['PROVIDER_STATE']) 
    provider_md_location_preference = get_clean_value(provider['PROVIDER_MD_LOCATION_PREFERENCE'], "")
    provider_services = get_clean_value(provider['PROVIDER_SERVICES'], "None Specified") 
    provider_future_services = get_clean_value(provider['PROVIDER_FUTURE_SERVICES'], "")
    provider_additional_services = get_clean_value(provider["PROVIDER_ADDITIONAL_SERVICES"], "")
    
    # Create base prompt
    prompt = f"""
    You are an Operations Manager at Moxie tasked with matching providers with the right medical directors. Providers
    are opening up a new medspa and need a medical director to oversee the practice.
    
    Provider Information:
    - Ticket Name: {ticket_name}
    - Email: {provider_email}
    - License Type: {provider_license_type}
    - Experience Level: {provider_experience_level}
    - State: {provider_state}  
    - MD Location Preference: {provider_md_location_preference}
    - Current Services: {provider_services}
    - Future Services: {provider_future_services}
    - Additional Notes: {provider_additional_services}
    
    Location Restrictions:
    - California: Providers from California can ONLY be matched with medical directors in California due to strict state licensing requirements.
    - For other states, prioritize same state matches, especially if the provider wrote down an MD Location Preference.
    """
    

    prompt += """    
    Using the nurse information above, analyze the following medical directors and identify the top 10 best matches based on:
    1. State licensing requirements (STRICT requirement for California)
    2. MD Location Preference
    3. Services provided. The doctor should have experience with the services the nurse is offering.
    4. Experience level compatibility (experienced doctors can mentor newer nurses)
    5. Personality compatibility
    6. Doctor's preferences and requirements
    7. Any specific notes or requirements mentioned
    
    For each match, provide:
    1. The doctor's name
    2. Contact information
    3. Capacity status
    4. A detailed explanation of why they're a good match, making specific connections between:
        - How they meet state licensing requirements 
        - How the doctor's personality traits and working style benefit this nurse
        - Specific geographic advantages of their locations
        - How their experience levels complement each other
    5. A match score out of 10
    
    Be specific and detailed in your reasoning, drawing direct connections between their profiles.
    
    Available Medical Directors:

    """

    doctors_df = doctors_df.sort_values(by="Residing State  (Lives In)")
    # Add doctor information to the prompt
    for _, doctor in doctors_df.iterrows():
        # Extract provider information
        clean_first_name = re.sub(r"^dr\.?\s*", "", str(doctor['First Name']), flags=re.IGNORECASE).strip()
        doctor_name = f"{clean_first_name} {doctor['Last Name']}"
        doctor_email = str(doctor['Email'])
        doctor_accepted_services = str(doctor['Accepted Services'])
        doctor_residing_state = str(doctor['Residing State  (Lives In)'])
        doctor_licensed_states = str(doctor['Licensed States '])
        doctor_experience_level = str(doctor['Experience Level '])
        doctor_accepting_status = str(doctor['Accepting Status '])

        
        doctor_info = f"""
        Doctor:
        - Name: {doctor_name}
        - Email: {doctor_email}
        - Residing State: {doctor_residing_state}
        - Licensed States: {doctor_licensed_states}
        - Experience Level: {doctor_experience_level}
        - Accepting Status: {doctor_accepting_status}
        - Accepted Services: {doctor_accepted_services}
        """
        
        prompt += doctor_info + "\n"
    
    # Add response format instructions
    prompt += """
    Format your response as JSON with the following structure:
    {
        "matches": [
            {
                "name": "Dr. Name",
                "email": "doctor@email.com",
                "capacity_status": "Has capacity for X more of this license type" (include only if matching with a doctor),
                "match_score": 8.5, 
                "reasoning": "Detailed explanation of why this is a good match that specifically references capacity, state requirements, and personality fit"
            },
            ...
        ]
    }
    
    Only include the JSON in your response, nothing else.
    """
    
    return prompt, None