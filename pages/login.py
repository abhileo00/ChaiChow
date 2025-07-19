import streamlit as st
import pandas as pd
import os
from datetime import datetime

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
USERS_FILE = os.path.join(DATA_DIR, "users.csv")

def init_users():
    if not os.path.exists(USERS_FILE):
        # Create default admin account
        default_admin = pd.DataFrame([{
            "user_id": "ADMIN_001",
            "name": "Admin User",
            "mobile": None,
            "password": "admin123",  # Change in production
            "role": "admin",
            "status": "active",
            "credit_limit": 0,
            "current_balance": 0,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        default_admin.to_csv(USERS_FILE, index=False)

def render():
    init_users()
    st.title("Login to Chai Chow Corner")
    
    role = st.radio("I am a:", ["Admin", "Staff", "Customer"], horizontal=True)
    
    if role in ["Admin", "Staff"]:
        with st.form(f"{role.lower()}_login"):
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
                    st.session_state.user_id = user_id
                    st.session_state.user_role = role.lower()
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    
    else:  # Customer
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            with st.form("customer_login"):
                mobile = st.text_input("Mobile Number")
                password = st.text_input("Password", type="password")
                
                if st.form_submit_button("Login"):
                    users_df = pd.read_csv(USERS_FILE)
                    user = users_df[
                        (users_df['mobile'] == mobile) & 
                        (users_df['password'] == password)
                    ]
                    if not user.empty:
                        st.session_state.user_id = user.iloc[0]['user_id']
                        st.session_state.user_role = 'customer'
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
        
        with tab2:
            with st.form("customer_register"):
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
                            "credit_limit": 1000,
                            "current_balance": 0,
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }])
                        users_df = pd.concat([users_df, new_user], ignore_index=True)
                        users_df.to_csv(USERS_FILE, index=False)
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Mobile already registered")
