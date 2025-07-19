import streamlit as st
from pages import (
    1_Login, 
    2_Orders,
    3_User_Management,
    4_Menu_Management,
    5_Inventory,
    6_Reports,
    7_Feedback,
    8_Customer_Credit
)

# Session state initialization
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
    st.session_state.user_role = None

# Page router
def main():
    if not st.session_state.user_id:
        1_Login.render()
    else:
        user_role = st.session_state.user_role
        
        # Sidebar navigation
        st.sidebar.title(f"Logged in as: {user_role.capitalize()}")
        if st.sidebar.button("Logout"):
            st.session_state.clear()
            st.rerun()

        # Role-based page access
        if user_role == "admin":
            page = st.sidebar.selectbox("Navigation", [
                "Orders", "User Management", "Menu", 
                "Inventory", "Reports", "Feedback", "Customer Credit"
            ])
        elif user_role == "staff":
            page = st.sidebar.selectbox("Navigation", [
                "Orders", "Menu", "Inventory", "Feedback"
            ])
        else:  # customer
            page = st.sidebar.selectbox("Navigation", ["Orders", "Menu", "Feedback"])

        # Render selected page
        if page == "Orders":
            2_Orders.render()
        elif page == "User Management":
            3_User_Management.render()
        elif page == "Menu":
            4_Menu_Management.render()
        elif page == "Inventory":
            5_Inventory.render()
        elif page == "Reports":
            6_Reports.render()
        elif page == "Feedback":
            7_Feedback.render()
        elif page == "Customer Credit":
            8_Customer_Credit.render()

if __name__ == "__main__":
    main()
