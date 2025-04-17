import streamlit as st

########################################################
# Page config
########################################################
st.set_page_config(page_title="Moxie Matching Details", layout="wide")

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
st.markdown("<h1 class='main-header'>Moxie Matching Details</h1>", unsafe_allow_html=True)

st.info(f"This page is under construction. Please check back soon.")

st.markdown("""
    This specialized matching system uses ChatGPT AI to intelligently match nurses with appropriate medical directors based on critical factors:

    1. **State Licensing Requirements**: The system strictly enforces state licensing rules:
        - California nurses can ONLY be matched with California medical directors
        - Other states prioritize same-state matches but allow nearby states when appropriate

    2. **Capacity Verification**: The system checks each medical director's capacity:
        - Verifies capacity specifically for the nurse's license type (RN or NP)
        - Never suggests matches with medical directors who are at capacity
        - Clearly indicates each MD's current capacity status

    3. **Experience Level Compatibility**: The system considers the experience levels of both professionals, matching nurses with appropriate mentors or peers.

    4. **Personality Trait Analysis**: The system analyzes the personality traits and work styles of medical directors to find complementary matches with nurses.

    5. **Service Alignment**: The system analyzes the services provided by nurses and looks for doctors with relevant expertise.

    6. **Detailed Reasoning**: For each match, the system provides a comprehensive explanation highlighting state compatibility, capacity availability, and professional synergies.

    7. **Match Score**: The system provides a score out of 10 with detailed reasoning to explain why each match works well.

    **Technical Features**:

    - Results are cached to improve performance and reduce API usage
    - System automatically switches to a faster AI model during high demand periods
    - Smart filtering prioritizes state compliance and capacity availability first
    - Clear flagging of state restrictions for California providers
    - Transparent capacity information for each medical director
""")