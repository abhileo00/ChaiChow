import streamlit as st
import pandas as pd
from utils.helpers import load_data, save_data

st.set_page_config(page_title="Customer Credit", layout="wide")

# Admin only
if 'user_role' not in st.session_state or st.session_state.user_role != "admin":
    st.warning("Unauthorized access")
    st.switch_page("app.py")

users = load_data('users')
orders = load_data('orders')

st.title("Customer Credit")

# Get customers with credit
customers = users[users['role'] == 'customer']
credit_customers = customers[customers['credit_limit'] > 0]

# Display credit status
st.subheader("Customer Credit Status")
st.dataframe(
    credit_customers[['user_id', 'name', 'credit_limit', 'current_balance']],
    hide_index=True
)

# Credit adjustment
with st.expander("Adjust Credit"):
    with st.form("credit_form"):
        customer_id = st.selectbox("Select Customer", credit_customers['user_id'])
        new_limit = st.number_input("New Credit Limit", 
                                  value=int(credit_customers[credit_customers['user_id'] == customer_id]['credit_limit'].values[0]))
        balance_adjust = st.number_input("Balance Adjustment", value=0)
        
        if st.form_submit_button("Update"):
            users.loc[users['user_id'] == customer_id, 'credit_limit'] = new_limit
            users.loc[users['user_id'] == customer_id, 'current_balance'] += balance_adjust
            save_data(users, 'users')
            st.success("Credit updated")
            st.rerun()

# Overdue accounts
overdue = credit_customers[credit_customers['current_balance'] > 0]
if not overdue.empty:
    st.subheader("Overdue Accounts")
    st.dataframe(overdue[['user_id', 'name', 'current_balance']], hide_index=True)
