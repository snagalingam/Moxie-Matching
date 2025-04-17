import pandas as pd
import re
import streamlit as st

# Helper function to extract capacity information
def extract_capacity_info(capacity_text, license_type):
    if not isinstance(capacity_text, str):
        return 0
    
    # Check for "at capacity" phrases
    if f"at capacity for {license_type}s" in capacity_text.lower():
        return 0
    
    # Look for capacity numbers
    match = re.search(r'(\d+)\s+more\s+' + license_type + r's', capacity_text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    return 0  # Default to 0 if no capacity info found

# Helper function to create capacity status from NP and RN capacity
def create_capacity_status(np_capacity, rn_capacity):
    np_status = f"Has capacity for {np_capacity} more NPs" if np_capacity > 0 else "At capacity for NPs"
    rn_status = f"Has capacity for {rn_capacity} more RNs" if rn_capacity > 0 else "At capacity for RNs"
    return f"{np_status}, {rn_status}"

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
                 "Residing State  (Lives In)": "CA", "Create Date": "2023-01-15", "Lifecycle Stage": "Medical Director Onboarded",
                 "Capacity Status": "Has capacity for 3 more NPs, 2 more RNs"},
                {"First Name": "Emily", "Last Name": "Johnson", "Email": "emily.j@example.com", 
                 "Residing State  (Lives In)": "TX", "Create Date": "2023-02-20", "Lifecycle Stage": "Medical Director Onboarded",
                 "Capacity Status": "At capacity for NPs, has capacity for 2 more RNs"},
                {"First Name": "Michael", "Last Name": "Brown", "Email": "m.brown@example.com", 
                 "Residing State  (Lives In)": "FL", "Create Date": "2023-03-10", "Lifecycle Stage": "Medical Director Onboarded",
                 "Capacity Status": "Has capacity for 1 more NP, at capacity for RNs"},
                {"First Name": "Sarah", "Last Name": "Garcia", "Email": "s.garcia@example.com", 
                 "Residing State  (Lives In)": "CA", "Create Date": "2023-04-05", "Lifecycle Stage": "Medical Director Onboarded",
                 "Capacity Status": "At capacity for both NPs and RNs"},
                {"First Name": "David", "Last Name": "Martinez", "Email": "d.martinez@example.com", 
                 "Residing State  (Lives In)": "NY", "Create Date": "2023-05-12", "Lifecycle Stage": "Medical Director Onboarded",
                 "Capacity Status": "Has capacity for 2 more NPs, 3 more RNs"}
            ]
            doctors_df = pd.DataFrame(doctor_data)
        
        # Try to load the MD metadata
        try:
            md_metadata_df = pd.read_csv('md_metadata.csv')
        except FileNotFoundError:
            # If not found, create an empty dataframe with appropriate columns
            md_metadata_df = pd.DataFrame(columns=['First Name', 'Last Name', 'Email', 'Residing State  (Lives In)', 
                                                  'MD Preferences', 'Personality Traits'])
        
        # Add capacity information if it doesn't exist
        if 'Capacity Status' not in md_metadata_df.columns:
            md_metadata_df['Capacity Status'] = "Has capacity for 2 more NPs, Has capacity for 3 more RNs"
        
        # Extract capacity information
        md_metadata_df['NP Capacity'] = md_metadata_df['Capacity Status'].apply(
            lambda x: extract_capacity_info(x, 'NP') if isinstance(x, str) else 0
        )
        
        md_metadata_df['RN Capacity'] = md_metadata_df['Capacity Status'].apply(
            lambda x: extract_capacity_info(x, 'RN') if isinstance(x, str) else 0
        )
        
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
            # Create a minimal empty dataframe with required columns
            st.error("No nurse data file found. Please upload the hubspot_moxie.csv file.")
            nurses_df = pd.DataFrame(columns=[
                'Ticket Number Counter', 'Bird Eats Bug Email', 'Provider License Type',
                'Experience Level  ', 'State (MedSpa Premise)', 'Services Provided',
                'Addt\'l Service Notes'
            ])
        
        # Merge MD metadata with main doctors dataframe if possible
        if len(doctors_df) > 0 and len(md_metadata_df) > 0:
            # Try to match by email first (most reliable)
            merged_df = pd.merge(
                doctors_df, 
                md_metadata_df[['Email', 'MD Preferences', 'Personality Traits', 'Multiple States', 
                               'States List', 'Has Preferences', 'Traits List', 'NP Capacity', 'RN Capacity']], 
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
                        merged_df.at[idx, 'NP Capacity'] = metadata['NP Capacity']
                        merged_df.at[idx, 'RN Capacity'] = metadata['RN Capacity']
            
            doctors_df = merged_df
            
            # Fill in missing values
            doctors_df['MD Preferences'] = doctors_df['MD Preferences'].fillna('')
            doctors_df['Personality Traits'] = doctors_df['Personality Traits'].fillna('')
            doctors_df['Multiple States'] = doctors_df['Multiple States'].fillna(False)
            doctors_df['Has Preferences'] = doctors_df['Has Preferences'].fillna(False)
            doctors_df['NP Capacity'] = doctors_df['NP Capacity'].fillna(0)
            doctors_df['RN Capacity'] = doctors_df['RN Capacity'].fillna(0)
            
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
            
            # Always create Capacity Status from the NP and RN capacity for consistency
            doctors_df['Capacity Status'] = doctors_df.apply(
                lambda row: create_capacity_status(row['NP Capacity'], row['RN Capacity']),
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
            if 'NP Capacity' not in doctors_df.columns:
                doctors_df['NP Capacity'] = 2  # Default capacity
            if 'RN Capacity' not in doctors_df.columns:
                doctors_df['RN Capacity'] = 3  # Default capacity
            if 'Capacity Status' not in doctors_df.columns:
                doctors_df['Capacity Status'] = doctors_df.apply(
                    lambda row: create_capacity_status(row['NP Capacity'], row['RN Capacity']),
                    axis=1
                )
        
        return doctors_df, nurses_df
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None 