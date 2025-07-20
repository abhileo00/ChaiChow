import streamlit as st
import pandas as pd
from datetime import datetime
from utils.helpers import load_data, save_data

st.set_page_config(page_title="Feedback", layout="wide")

# Authentication check
if 'user_role' not in st.session_state:
    st.switch_page("app.py")

feedback = load_data('feedback')

st.title("Feedback")

# Feedback form
with st.form("feedback_form"):
    st.subheader("Submit Feedback")
    rating = st.slider("Rating (1-5 stars)", 1, 5, 3)
    feedback_type = st.selectbox("Feedback Type", 
                               ["General", "Food", "Service", "Ambience", "Other"])
    comments = st.text_area("Your Feedback")
    name = st.text_input("Name (optional)")
    
    if st.form_submit_button("Submit"):
        new_feedback = {
            'feedback_id': len(feedback) + 1,
            'user_id': st.session_state.get('user_id', 'anonymous'),
            'rating': rating,
            'type': feedback_type,
            'comments': comments,
            'name': name if name else 'Anonymous',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        feedback = pd.concat([feedback, pd.DataFrame([new_feedback])], ignore_index=True)
        save_data(feedback, 'feedback')
        st.success("Thank you for your feedback!")

# View feedback (admin/staff)
if st.session_state.user_role in ["admin", "staff"]:
    st.subheader("Customer Feedback")
    
    # Filters
    min_rating = st.slider("Minimum rating", 1, 5, 1)
    type_filter = st.selectbox("Filter by type", ["All"] + feedback['type'].unique().tolist())
    
    filtered_feedback = feedback[feedback['rating'] >= min_rating]
    if type_filter != "All":
        filtered_feedback = filtered_feedback[filtered_feedback['type'] == type_filter]
    
    st.dataframe(filtered_feedback.sort_values('timestamp', ascending=False), hide_index=True)
    
    # Stats
    avg_rating = feedback['rating'].mean()
    st.metric("Average Rating", f"{avg_rating:.1f} stars")
