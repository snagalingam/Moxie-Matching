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
        doctors_df = pd.read_csv('md_hubspot.csv')
        nurses_df = pd.read_csv('matching_tickets.csv')
        return doctors_df, nurses_df
    
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None 