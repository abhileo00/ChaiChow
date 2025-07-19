import streamlit as st
import pandas as pd
from datetime import datetime

def render():
    st.title("💬 Feedback System")
    feedback_df = pd.read_csv("data/feedback.csv")
    
    tab1, tab2 = st.tabs(["Submit Feedback", "View Feedback"])
    
    with tab1:
        with st.form("feedback_form"):
            rating = st.slider("Rating (1-5)", 1, 5, 5)
            comment = st.text_area("Your Feedback")
            submit = st.form_submit_button("Submit")
            
            if submit:
                new_feedback = {
                    "feedback_id": f"FB_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "user_id": st.session_state.user_id,
                    "rating": rating,
                    "comment": comment,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                feedback_df = pd.concat([feedback_df, pd.DataFrame([new_feedback])])
                feedback_df.to_csv("data/feedback.csv", index=False)
                st.success("✅ Thank you for your feedback!")
    
    with tab2:
        if st.session_state.user_role in ["admin", "staff"]:
            st.dataframe(feedback_df, hide_index=True)
            
            # Feedback stats
            avg_rating = feedback_df['rating'].mean()
            st.metric("Average Rating", f"{avg_rating:.1f}/5")
        else:
            st.warning("⛔ Staff access required to view feedback")
