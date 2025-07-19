import streamlit as st
import pandas as pd
from datetime import datetime

def render():
    if st.session_state.user_role != "admin":
        st.error("⛔ Admin access required")
        return

    st.title("👥 User Management")
    users_df = pd.read_csv("data/users.csv")
    
    tab1, tab2 = st.tabs(["View Users", "Manage Users"])
    
    with tab1:
        st.dataframe(users_df, hide_index=True)
    
    with tab2:
        action = st.radio("Action", ["Create User", "Edit User"], horizontal=True)
        
        if action == "Create User":
            with st.form("create_user"):
                name = st.text_input("Full Name")
                role = st.selectbox("Role", ["admin", "staff", "customer"])
                mobile = st.text_input("Mobile") if role == "customer" else ""
                password = st.text_input("Password", type="password")
                status = st.selectbox("Status", ["active", "inactive"])
                credit_limit = st.number_input("Credit Limit", value=1000) if role == "customer" else 0
                
                if st.form_submit_button("Create"):
                    new_user = {
                        "user_id": f"{role.upper()}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "name": name,
                        "mobile": mobile,
                        "password": password,
                        "role": role,
                        "status": status,
                        "credit_limit": credit_limit,
                        "current_balance": 0,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    users_df = pd.concat([users_df, pd.DataFrame([new_user])], ignore_index=True)
                    users_df.to_csv("data/users.csv", index=False)
                    st.success("✅ User created successfully!")
        
        else:  # Edit User
            user_id = st.selectbox("Select User", users_df['user_id'])
            user = users_df[users_df['user_id'] == user_id].iloc[0]
            
            with st.form("edit_user"):
                st.write(f"Editing: {user['name']} ({user['role']})")
                name = st.text_input("Name", value=user['name'])
                status = st.selectbox("Status", ["active", "inactive"], 
                                   index=0 if user['status'] == "active" else 1)
                
                if user['role'] == 'customer':
                    credit_limit = st.number_input("Credit Limit", 
                                                 value=float(user['credit_limit']))
                    current_balance = st.number_input("Current Balance", 
                                                   value=float(user['current_balance']))
                
                new_password = st.text_input("New Password", type="password", 
                                          placeholder="Leave blank to keep current")
                
                if st.form_submit_button("Update"):
                    users_df.loc[users_df['user_id'] == user_id, 'name'] = name
                    users_df.loc[users_df['user_id'] == user_id, 'status'] = status
                    
                    if user['role'] == 'customer':
                        users_df.loc[users_df['user_id'] == user_id, 'credit_limit'] = credit_limit
                        users_df.loc[users_df['user_id'] == user_id, 'current_balance'] = current_balance
                    
                    if new_password:
                        users_df.loc[users_df['user_id'] == user_id, 'password'] = new_password
                    
                    users_df.to_csv("data/users.csv", index=False)
                    st.success("✅ User updated successfully!")
