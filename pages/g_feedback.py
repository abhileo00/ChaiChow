import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

def render():
    st.header("💬 Customer Feedback")
    try:
        feedback_df = pd.read_csv("data/feedback.csv")
    except:
        st.error("Failed to load feedback data")
        return
    
    tab1, tab2 = st.tabs(["Submit Feedback", "View Feedback"])
    
    with tab1:
        with st.form("feedback_form", border=True):
            name = st.text_input("Your Name (optional)")
            rating = st.slider("Rating (1-5 stars)", 1, 5, 5)
            feedback_type = st.selectbox("Type", 
                                       ["General", "Compliment", "Complaint", "Suggestion"])
            comments = st.text_area("Your Feedback")
            
            if st.form_submit_button("Submit", use_container_width=True):
                new_feedback = {
                    "feedback_id": f"FB_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "user_id": st.session_state.user_id,
                    "name": name if name else "Anonymous",
                    "rating": rating,
                    "type": feedback_type,
                    "comment": comments,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                feedback_df = pd.concat([feedback_df, pd.DataFrame([new_feedback])], ignore_index=True)
                feedback_df.to_csv("data/feedback.csv", index=False)
                st.success("✅ Thank you for your feedback!")
                st.balloons()
    
    with tab2:
        if st.session_state.user_role not in ["admin", "staff"]:
            st.error("⛔ Staff access required")
            return
        
        st.dataframe(feedback_df, hide_index=True, use_container_width=True)
        
        # Feedback stats
        if not feedback_df.empty:
            st.subheader("📊 Feedback Statistics")
            avg_rating = feedback_df['rating'].mean()
            st.metric("Average Rating", f"{avg_rating:.1f} ★")
            
            fig = px.histogram(feedback_df, x='rating', 
                             title="Rating Distribution",
                             nbins=5, range_x=[1,6])
            st.plotly_chart(fig, use_container_width=True)
