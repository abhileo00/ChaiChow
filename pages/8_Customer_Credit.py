import streamlit as st
import pandas as pd

def render():
    if st.session_state.user_role != "admin":
        st.warning("⛔ Admin access required")
        return
    
    st.title("💰 Customer Credit")
    users_df = pd.read_csv("data/users.csv")
    customers = users_df[users_df['role'] == "customer"]
    
    st.dataframe(customers[['name', 'mobile', 'credit_limit', 'current_balance']])
    
    # Credit adjustment
    customer_id = st.selectbox("Select Customer", customers['user_id'])
    customer = customers[customers['user_id'] == customer_id].iloc[0]
    
    with st.form("credit_form"):
        new_limit = st.number_input("Credit Limit", value=float(customer['credit_limit']))
        adjust_balance = st.number_input("Adjust Balance", value=float(customer['current_balance']))
        
        if st.form_submit_button("Update"):
            users_df.loc[users_df['user_id'] == customer_id, 'credit_limit'] = new_limit
            users_df.loc[users_df['user_id'] == customer_id, 'current_balance'] = adjust_balance
            users_df.to_csv("data/users.csv", index=False)
            st.success("✅ Credit updated!")
