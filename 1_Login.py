import streamlit as st
import pandas as pd
from datetime import datetime
import os

DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.csv")

def init_files():
    if not os.path.exists(USERS_FILE):
        pd.DataFrame(columns=[
            "user_id", "name", "mobile", "password", "role", 
            "status", "credit_limit", "current_balance", "created_at"
        ]).to_csv(USERS_FILE, index=False)

def login_user(user_id, role):
    st.session_state.user_id = user_id
    st.session_state.user_role = role

def render():
    st.title("🔐 Chai Chow Corner - Login")
    init_files()
    
    role = st.radio("Select Role", ["Admin", "Staff", "Customer"], horizontal=True)
    
    if role in ["Admin", "Staff"]:
        with st.form(f"{role}_login"):
            user_id = st.text_input("User ID")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Login"):
                users_df = pd.read_csv(USERS_FILE)
                user = users_df[
                    (users_df['user_id'] == user_id) & 
                    (users_df['password'] == password) & 
                    (users_df['role'] == role.lower())
                ]
                if not user.empty:
                    login_user(user_id, role.lower())
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    
    else:  # Customer
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            with st.form("Customer Login"):
                mobile = st.text_input("Mobile Number")
                password = st.text_input("Password", type="password")
                
                if st.form_submit_button("Login"):
                    users_df = pd.read_csv(USERS_FILE)
                    user = users_df[
                        (users_df['mobile'] == mobile) & 
                        (users_df['password'] == password)
                    ]
                    if not user.empty:
                        login_user(user.iloc[0]['user_id'], 'customer')
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
        
        with tab2:
            with st.form("Customer Register"):
                name = st.text_input("Full Name")
                mobile = st.text_input("Mobile Number")
                password = st.text_input("Password", type="password")
                
                if st.form_submit_button("Register"):
                    users_df = pd.read_csv(USERS_FILE)
                    if mobile not in users_df['mobile'].values:
                        new_user = pd.DataFrame([{
                            "user_id": f"CUST_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                            "name": name,
                            "mobile": mobile,
                            "password": password,
                            "role": "customer",
                            "status": "active",
                            "credit_limit": 1000,  # Default credit
                            "current_balance": 0,
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }])
                        users_df = pd.concat([users_df, new_user])
                        users_df.to_csv(USERS_FILE, index=False)
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Mobile already registered")