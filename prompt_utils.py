import pandas as pd

def create_prompt(search_value, doctors_df, nurses_df, filters=None):
    if filters is None:
        filters = {}
    
    # Find the nurse
    nurse_row = nurses_df[
        nurses_df.apply(
            lambda row: pd.notna(row['Ticket Number Counter']) and search_value.lower() in str(row['Ticket Number Counter']).lower() or
                        pd.notna(row['Bird Eats Bug Email']) and search_value.lower() in str(row['Bird Eats Bug Email']).lower(),
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
    You are an Operations Manager at Moxie tasked with matching nurses with the right medical directors.
    
    Nurse Information:
    - Name: {nurse_name}
    - Email: {nurse_email}
    - License Type: {nurse_license}
    - Experience Level: {nurse_experience}
    - State: {nurse_state}
    - Services: {nurse_services}
    - Additional Notes: {nurse_notes}
    
    IMPORTANT STATE RESTRICTIONS:
    - California: Nurses from California can ONLY be matched with medical directors in California due to strict state licensing requirements.
    - For other states, prioritize same-state matches but nearby states are acceptable if specified in filters.
    """
    
    # Add capacity note
    prompt += """
    CAPACITY REQUIREMENTS:
    - Medical directors have limits on how many nurses they can supervise
    - Check each MD's capacity for the specific license type (RN or NP)
    - Do NOT match the nurse with any MD who is at capacity for their license type
    """
    
    # Add filter requirements to the prompt
    if filters.get("md_age") and filters.get("md_age") != "Any":
        prompt += f"\n\nPreference for medical directors who are: {filters['md_age']}"
        
    if filters.get("interaction_style") and filters.get("interaction_style") != "Any":
        prompt += f"\n\nPreference for medical directors with interaction style: {filters['interaction_style']}"
        
    if filters.get("location") == "Same State Only":
        prompt += "\nLocation requirement: Only include medical directors in the same state as the nurse."
    elif filters.get("location") == "Nearby States Acceptable":
        prompt += "\nLocation preference: Prioritize medical directors in the same state, but nearby states are acceptable if not in California."
    elif filters.get("location") == "Any Location":
        prompt += "\nLocation preference: While prioritizing same-state matches, any location is acceptable EXCEPT for California nurses who must be matched with California medical directors only."
        
    if filters.get("service_requirements") and filters.get("service_requirements").strip():
        prompt += f"\n\nAdditional service requirements to consider:\n{filters['service_requirements']}"
    
    prompt += """
    
    Using the nurse information above, analyze the following medical directors and identify the top 3 best matches based on:
    1. State licensing requirements (STRICT requirement for California)
    2. Capacity availability for this nurse's license type (STRICT requirement)
    3. Experience level compatibility (experienced doctors can mentor newer nurses)
    4. Personality compatibility
    5. Doctor's preferences and requirements
    6. Any specific notes or requirements mentioned
    
    For each match, provide:
    1. The doctor's name
    2. Contact information
    3. Capacity status
    4. A detailed explanation of why they're a good match, making specific connections between:
        - How this specific doctor has capacity for this nurse's license type
        - How they meet state licensing requirements 
        - How the doctor's personality traits and working style benefit this nurse
        - Specific geographic advantages of their locations
        - How their experience levels complement each other
    5. A match score out of 10
    
    Be specific and detailed in your reasoning, drawing direct connections between their profiles.
    
    Available Medical Directors:
    """
    
    # Filter doctors based on criteria
    filtered_doctors = doctors_df.copy()
    
    # STRICT FILTER: Apply California restriction
    if nurse_state.upper() == "CA":
        filtered_doctors = filtered_doctors[
            filtered_doctors.apply(
                lambda row: "CA" in row.get('States List', []) if isinstance(row.get('States List'), list)
                else row.get('Residing State  (Lives In)', '').upper() == "CA",
                axis=1
            )
        ]
    
    # STRICT FILTER: Apply capacity check based on license type
    if nurse_license.upper() == "NP":
        filtered_doctors = filtered_doctors[
            filtered_doctors.apply(
                lambda row: row.get('NP Capacity', 0) > 0 if 'NP Capacity' in row else 
                ("at capacity for np" not in str(row.get('Capacity Status', '')).lower() and 
                    "capacity for" in str(row.get('Capacity Status', '')).lower() and
                    "np" in str(row.get('Capacity Status', '')).lower()),
                axis=1
            )
        ]
    elif nurse_license.upper() == "RN":
        filtered_doctors = filtered_doctors[
            filtered_doctors.apply(
                lambda row: row.get('RN Capacity', 0) > 0 if 'RN Capacity' in row else
                ("at capacity for rn" not in str(row.get('Capacity Status', '')).lower() and
                    "capacity for" in str(row.get('Capacity Status', '')).lower() and
                    "rn" in str(row.get('Capacity Status', '')).lower()),
                axis=1
            )
        ]
    
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
    
    # If filters resulted in no doctors, provide clear feedback
    if filtered_doctors.empty:
        if nurse_state.upper() == "CA":
            return None, "No California medical directors found with capacity for this nurse's license type. Please check back later or adjust requirements."
        else:
            return None, "No medical directors found with available capacity for this nurse's license type. Please check back later or adjust requirements."
    
    # Select doctors to include, prioritizing state matches
    if nurse_state != "Unknown":
        # Find doctors in the same state (using States List if available)
        same_state_doctors = filtered_doctors[
            filtered_doctors.apply(
                lambda row: nurse_state in row.get('States List', []) if isinstance(row.get('States List'), list)
                else nurse_state == row.get('Residing State  (Lives In)', ''),
                axis=1
            )
        ]
        
        # Find other doctors (only if not a CA nurse)
        if nurse_state.upper() != "CA" and filters.get("location") != "Same State Only":
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
            selected_doctors = same_state_doctors.head(20)
    else:
        selected_doctors = filtered_doctors.head(20)
    
    # Add doctor information to the prompt
    for _, doctor in selected_doctors.iterrows():
        # Get the states (handling multiple states)
        states = doctor.get('States List', []) if isinstance(doctor.get('States List'), list) else [doctor.get('Residing State  (Lives In)', '')]
        states_str = ', '.join(str(s) for s in states if s)
        
        # Get capacity information based on nurse's license type
        capacity_status = doctor.get('Capacity Status', '')
        if nurse_license.upper() == "NP":
            capacity_info = f"NP Capacity: {doctor.get('NP Capacity', 'Unknown')}"
        else:  # RN or other
            capacity_info = f"RN Capacity: {doctor.get('RN Capacity', 'Unknown')}"
        
        # Get personality traits and preferences
        traits = doctor.get('Personality Traits', '')
        preferences = doctor.get('MD Preferences', '')
        
        doctor_info = f"""
        Doctor:
        - Name: {doctor['First Name']} {doctor['Last Name']}
        - Email: {doctor['Email']}
        - State(s): {states_str}
        - {capacity_info}
        - Capacity Status: {capacity_status}
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