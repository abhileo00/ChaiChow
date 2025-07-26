import streamlit as st

def login_form():
    with st.sidebar:
        st.header("Admin Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if username == "admin" and password == "admin123":
                st.session_state.logged_in = True
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid credentials")
        
        if st.session_state.get("logged_in"):
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.success("Logged out successfully!")
                st.rerun()

def check_login():
    if not st.session_state.get("logged_in"):
        st.warning("Please login to access this page")
        st.stop()
