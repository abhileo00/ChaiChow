import streamlit as st
import pandas as pd
from datetime import datetime

def render():
    if st.session_state.user_role != "admin":
        st.warning("⛔ Admin access required")
        return
    
    st.title("👥 User Management")
    users_df = pd.read_csv("data/users.csv")
    
    tab1, tab2 = st.tabs(["View Users", "Add/Edit Users"])
    
    with tab1:
        st.dataframe(users_df, hide_index=True)
    
    with tab2:
        action = st.radio("Action", ["Add New", "Edit Existing"], horizontal=True)
        
        if action == "Add New":
            with st.form("add_user"):
                name = st.text_input("Full Name")
                role = st.selectbox("Role", ["admin", "staff", "customer"])
                mobile = st.text_input("Mobile") if role == "customer" else ""
                password = st.text_input("Password", type="password")
                status = st.selectbox("Status", ["active", "inactive"])
                credit_limit = st.number_input("Credit Limit", value=1000) if role == "customer" else 0
                
                if st.form_submit_button("Save User"):
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
                    users_df = pd.concat([users_df, pd.DataFrame([new_user])])
                    users_df.to_csv("data/users.csv", index=False)
                    st.success("✅ User added successfully!")
        
        else:  # Edit
            user_id = st.selectbox("Select User", users_df['user_id'])
            user = users_df[users_df['user_id'] == user_id].iloc[0]
            
            with st.form("edit_user"):
                name = st.text_input("Name", value=user['name'])
                status = st.selectbox("Status", ["active", "inactive"], index=0 if user['status'] == "active" else 1)
                new_password = st.text_input("New Password", type="password")
                
                if st.form_submit_button("Update User"):
                    users_df.loc[users_df['user_id'] == user_id, 'name'] = name
                    users_df.loc[users_df['user_id'] == user_id, 'status'] = status
                    if new_password:
                        users_df.loc[users_df['user_id'] == user_id, 'password'] = new_password
                    users_df.to_csv("data/users.csv", index=False)
                    st.success("✅ User updated!")
