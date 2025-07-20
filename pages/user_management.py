import streamlit as st
import pandas as pd
from utils.helpers import load_data, save_data

st.set_page_config(page_title="User Management", layout="wide")

# Admin access only
if 'user_role' not in st.session_state or st.session_state.user_role != "admin":
    st.warning("Unauthorized access")
    st.switch_page("app.py")

users = load_data('users')

st.title("User Management")

# Create tabs
add_tab, manage_tab, credit_tab = st.tabs(["Add User", "Manage Users", "Credit Management"])

with add_tab:
    with st.form("add_user_form"):
        st.subheader("Add New User")
        role = st.selectbox("User Role", ["admin", "staff", "customer"])
        user_id = st.text_input("Username")
        name = st.text_input("Full Name")
        password = st.text_input("Password", type="password")
        email = st.text_input("Email")
        
        if role == "customer":
            credit_limit = st.number_input("Credit Limit", min_value=0, value=1000)
        
        if st.form_submit_button("Create User"):
            if user_id in users['user_id'].values:
                st.error("Username already exists")
            else:
                new_user = {
                    'user_id': user_id,
                    'name': name,
                    'password': password,
                    'role': role,
                    'email': email,
                    'status': 'active',
                    'credit_limit': credit_limit if role == "customer" else 0,
                    'current_balance': 0
                }
                users = pd.concat([users, pd.DataFrame([new_user])], ignore_index=True)
                save_data(users, 'users')
                st.success("User created successfully")

with manage_tab:
    st.subheader("User List")
    
    # Filters
    role_filter = st.selectbox("Filter by role", ["All", "admin", "staff", "customer"])
    status_filter = st.selectbox("Filter by status", ["All", "active", "inactive"])
    
    filtered_users = users.copy()
    if role_filter != "All":
        filtered_users = filtered_users[filtered_users['role'] == role_filter]
    if status_filter != "All":
        filtered_users = filtered_users[filtered_users['status'] == status_filter]
    
    # Editable table
    edited_users = st.data_editor(
        filtered_users,
        disabled=["user_id"],
        hide_index=True,
        use_container_width=True
    )
    
    if st.button("Save Changes"):
        users.update(edited_users)
        save_data(users, 'users')
        st.success("Changes saved")

with credit_tab:
    st.subheader("Customer Credit Management")
    customers = users[users['role'] == 'customer']
    
    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(customers[['user_id', 'name', 'credit_limit', 'current_balance']], hide_index=True)
    
    with col2:
        with st.form("credit_adjustment"):
            customer_id = st.selectbox("Select customer", customers['user_id'])
            new_limit = st.number_input("New credit limit", min_value=0)
            balance_adjust = st.number_input("Balance adjustment")
            
            if st.form_submit_button("Update Credit"):
                users.loc[users['user_id'] == customer_id, 'credit_limit'] = new_limit
                users.loc[users['user_id'] == customer_id, 'current_balance'] += balance_adjust
                save_data(users, 'users')
                st.success("Credit updated")
