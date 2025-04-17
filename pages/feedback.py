import streamlit as st
import pandas as pd
import datetime
import json
import os

# Page configuration
st.set_page_config(page_title="Moxie Matching Feedback Log", layout="wide")

# Custom CSS
st.markdown("""
<style>
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
    .feedback-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 4px solid #5c88da;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .positive-feedback {
        border-left: 4px solid #28a745;
    }
    .neutral-feedback {
        border-left: 4px solid #ffc107;
    }
    .negative-feedback {
        border-left: 4px solid #dc3545;
    }
    .feedback-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .timestamp {
        color: #6c757d;
        font-size: 14px;
    }
    .rating-badge {
        font-weight: bold;
        padding: 5px 10px;
        border-radius: 15px;
        color: white;
    }
    .rating-high {
        background-color: #28a745;
    }
    .rating-medium {
        background-color: #ffc107;
        color: #212529;
    }
    .rating-low {
        background-color: #dc3545;
    }
    .feedback-filter {
        background-color: #f5f9ff;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
        border: 1px solid #d1e1ff;
    }
    .feedback-stats {
        display: flex;
        gap: 15px;
        margin-bottom: 20px;
    }
    .stat-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        flex: 1;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .stat-value {
        font-size: 24px;
        font-weight: bold;
        margin: 5px 0;
    }
    .stat-label {
        color: #6c757d;
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
    .match-details {
        background-color: #f0f5ff;
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
        margin-bottom: 10px;
    }
    .export-section {
        margin-top: 30px;
        padding-top: 20px;
        border-top: 1px solid #eee;
    }
</style>
""", unsafe_allow_html=True)

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
st.markdown("<h1 class='main-header'>Moxie Matching Feedback Log</h1>", unsafe_allow_html=True)

# Feedback data file path
FEEDBACK_FILE = "matching_feedback.json"

# Function to load feedback data
def load_feedback_data():
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading feedback data: {e}")
            return []
    return []

# Function to save feedback data
def save_feedback_data(feedback_data):
    try:
        with open(FEEDBACK_FILE, 'w') as f:
            json.dump(feedback_data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving feedback data: {e}")
        return False

# Function to add new feedback
def add_feedback(md_name, nurse_name, match_score, user_rating, comments, match_reasoning):
    feedback_data = load_feedback_data()
    
    # Create new feedback entry
    new_feedback = {
        "id": len(feedback_data) + 1,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "md_name": md_name,
        "nurse_name": nurse_name,
        "match_score": float(match_score),
        "user_rating": int(user_rating),
        "accuracy": int(user_rating) / 10.0,  # Calculate accuracy as a percentage of max rating
        "comments": comments,
        "match_reasoning": match_reasoning
    }
    
    # Add to existing data
    feedback_data.append(new_feedback)
    
    # Save updated data
    return save_feedback_data(feedback_data)

# Main app sections using tabs
tab1, tab2 = st.tabs(["Add Feedback", "View Feedback"])

# Tab 1: Add Feedback
with tab1:
    st.markdown("<h2 class='subheader'>Submit Matching Feedback</h2>", unsafe_allow_html=True)
    
    st.markdown("""
    Use this form to provide feedback on the quality and accuracy of the matching algorithm.
    This helps us improve future matches and track performance over time.
    """)
    
    # Feedback form
    col1, col2 = st.columns(2)
    
    with col1:
        md_name = st.text_input("Medical Director Name", placeholder="e.g., Dr. John Smith")
    
    with col2:
        nurse_name = st.text_input("Nurse Name", placeholder="e.g., Sarah Johnson, RN")
    
    col3, col4 = st.columns(2)
    
    with col3:
        match_score = st.number_input("Original Match Score (out of 10)", min_value=0.0, max_value=10.0, step=0.1)
    
    with col4:
        user_rating = st.slider("Your Rating of Match Quality", 1, 10, 5, 
                             help="How accurate do you think this match recommendation was?")
    
    # Match reasoning from the algorithm
    match_reasoning = st.text_area("Original Match Reasoning", 
                               placeholder="Paste the match reasoning provided by the algorithm",
                               height=150)
    
    # User comments
    comments = st.text_area("Your Comments", 
                          placeholder="What was good or bad about this match? Any specific observations?",
                          height=100)
    
    if st.button("Submit Feedback"):
        if md_name and nurse_name and match_reasoning:
            success = add_feedback(md_name, nurse_name, match_score, user_rating, comments, match_reasoning)
            if success:
                st.success("Feedback submitted successfully!")
            else:
                st.error("There was an error saving your feedback.")
        else:
            st.warning("Please fill in all required fields (Doctor Name, Nurse Name, and Match Reasoning).")

# Tab 2: View Feedback
with tab2:
    st.markdown("<h2 class='subheader'>Feedback History & Analytics</h2>", unsafe_allow_html=True)
    
    # Load feedback data
    feedback_data = load_feedback_data()
    
    if not feedback_data:
        st.info("No feedback data available yet. Submit feedback in the 'Add Feedback' tab.")
    else:
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(feedback_data)
        
        # Calculate statistics
        avg_algorithm_score = df['match_score'].mean()
        avg_user_rating = df['user_rating'].mean()
        avg_accuracy = (df['user_rating'] / 10.0).mean() * 100  # as percentage
        total_entries = len(df)
        
        # Display statistics
        st.markdown("<div class='feedback-stats'>", unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class='stat-card'>
                <div class='stat-label'>Average Algorithm Score</div>
                <div class='stat-value'>{avg_algorithm_score:.1f}/10</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
            <div class='stat-card'>
                <div class='stat-label'>Average User Rating</div>
                <div class='stat-value'>{avg_user_rating:.1f}/10</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown(f"""
            <div class='stat-card'>
                <div class='stat-label'>Perceived Accuracy</div>
                <div class='stat-value'>{avg_accuracy:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col4:
            st.markdown(f"""
            <div class='stat-card'>
                <div class='stat-label'>Total Feedback Entries</div>
                <div class='stat-value'>{total_entries}</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Filtering options
        st.markdown("<div class='feedback-filter'>", unsafe_allow_html=True)
        
        st.markdown("<h3>Filter Feedback</h3>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Get unique MDs
            md_options = ["All"] + sorted(df["md_name"].unique().tolist())
            selected_md = st.selectbox("Filter by Medical Director:", md_options)
            
        with col2:
            # Get unique nurses
            nurse_options = ["All"] + sorted(df["nurse_name"].unique().tolist())
            selected_nurse = st.selectbox("Filter by Nurse:", nurse_options)
            
        with col3:
            # Rating filter
            rating_options = ["All", "High (8-10)", "Medium (5-7)", "Low (1-4)"]
            selected_rating = st.selectbox("Filter by User Rating:", rating_options)
        
        # Date range filter
        if 'timestamp' in df.columns:
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            min_date = df['date'].min()
            max_date = df['date'].max()
            
            date_col1, date_col2 = st.columns(2)
            with date_col1:
                start_date = st.date_input("From Date:", min_date)
            with date_col2:
                end_date = st.date_input("To Date:", max_date)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Apply filters
        filtered_df = df.copy()
        
        if selected_md != "All":
            filtered_df = filtered_df[filtered_df["md_name"] == selected_md]
            
        if selected_nurse != "All":
            filtered_df = filtered_df[filtered_df["nurse_name"] == selected_nurse]
            
        if selected_rating != "All":
            if selected_rating == "High (8-10)":
                filtered_df = filtered_df[filtered_df["user_rating"] >= 8]
            elif selected_rating == "Medium (5-7)":
                filtered_df = filtered_df[(filtered_df["user_rating"] >= 5) & (filtered_df["user_rating"] < 8)]
            elif selected_rating == "Low (1-4)":
                filtered_df = filtered_df[filtered_df["user_rating"] < 5]
        
        if 'date' in filtered_df.columns:
            filtered_df = filtered_df[(filtered_df['date'] >= start_date) & (filtered_df['date'] <= end_date)]
        
        # Display filtered feedback
        st.markdown(f"<h3>Showing {len(filtered_df)} Feedback Entries</h3>", unsafe_allow_html=True)
        
        # Sort by timestamp (newest first)
        if not filtered_df.empty and 'timestamp' in filtered_df.columns:
            filtered_df = filtered_df.sort_values(by='timestamp', ascending=False)
        
        # Display feedback cards
        for idx, row in filtered_df.iterrows():
            # Determine card style based on rating
            card_class = "feedback-card"
            rating_class = "rating-badge "
            
            if row['user_rating'] >= 8:
                card_class += " positive-feedback"
                rating_class += "rating-high"
            elif row['user_rating'] >= 5:
                card_class += " neutral-feedback"
                rating_class += "rating-medium"
            else:
                card_class += " negative-feedback"
                rating_class += "rating-low"
            
            st.markdown(f"""
            <div class='{card_class}'>
                <div class='feedback-header'>
                    <h4>{row['md_name']} + {row['nurse_name']}</h4>
                    <span class='{rating_class}'>{row['user_rating']}/10</span>
                </div>
                <p class='timestamp'>{row['timestamp']}</p>
                
                <div class='match-details'>
                    <p><strong>Algorithm Score:</strong> {row['match_score']}/10</p>
                    <p><strong>Match Reasoning:</strong> {row['match_reasoning']}</p>
                </div>
                
                <p><strong>User Comments:</strong> {row['comments'] if row['comments'] else "No comments provided."}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Export section
        st.markdown("<div class='export-section'>", unsafe_allow_html=True)
        st.markdown("<h3>Export Feedback Data</h3>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Export All Feedback as CSV"):
                # Convert dataframe to CSV
                csv = df.to_csv(index=False)
                
                # Create download link
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="moxie_matching_feedback.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("Export Filtered Feedback as CSV"):
                # Convert filtered dataframe to CSV
                csv = filtered_df.to_csv(index=False)
                
                # Create download link
                st.download_button(
                    label="Download Filtered CSV",
                    data=csv,
                    file_name="moxie_matching_feedback_filtered.csv",
                    mime="text/csv"
                )
        
        st.markdown("</div>", unsafe_allow_html=True)

# Optional: Add link to go back to main matching page
st.markdown("---")
st.markdown("Return to [Matching System](#) (link will need to be updated based on your deployment)")
