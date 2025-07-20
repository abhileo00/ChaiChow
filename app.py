import streamlit as st
from utils.auth import authenticate_user, register_customer
from utils.helpers import load_data, save_data

# Initialize session state
if 'users' not in st.session_state:
    st.session_state.users = load_data('users')

st.set_page_config(page_title="Chai Chow Corner", layout="wide")

def show_login_page():
    st.title("Chai Chow Corner")
    st.write("Welcome to our restaurant management system")
    
    role = st.radio("Select your role:", ["Admin", "Staff", "Customer"], horizontal=True)
    
    if role in ["Admin", "Staff"]:
        with st.form(f"{role.lower()}_login"):
            st.subheader(f"{role} Login")
            user_id = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                if authenticate_user(user_id, password, role.lower()):
                    st.session_state.user_role = role.lower()
                    st.session_state.user_id = user_id
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    
    else:  # Customer
        login_tab, register_tab = st.tabs(["Login", "Register"])
        
        with login_tab:
            with st.form("customer_login"):
                st.subheader("Customer Login")
                mobile = st.text_input("Mobile Number")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login")
                
                if submitted:
                    if authenticate_user(mobile, password, "customer"):
                        st.session_state.user_role = "customer"
                        st.session_state.user_id = mobile
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
        
        with register_tab:
            with st.form("customer_register"):
                st.subheader("Customer Registration")
                name = st.text_input("Full Name")
                mobile = st.text_input("Mobile Number")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Register")
                
                if submitted:
                    if register_customer(name, mobile, password):
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Mobile number already registered")

# Main app logic
if 'user_role' not in st.session_state:
    show_login_page()
else:
    if st.session_state.user_role == "admin":
        st.switch_page("pages/UserManagement.py")
    elif st.session_state.user_role == "staff":
        st.switch_page("pages/Orders.py")
    elif st.session_state.user_role == "customer":
        st.switch_page("pages/Orders.py")
