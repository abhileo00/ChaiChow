import streamlit as st
import pandas as pd

def render():
    if st.session_state.user_role != "admin":
        st.error("Admin access required")
        return

    st.title("Customer Credit Management")
    try:
        users_df = pd.read_csv("data/users.csv")
        customers = users_df[users_df['role'] == "customer"]
    except:
        st.error("Failed to load user data")
        return
    
    if customers.empty:
        st.warning("No registered customers")
        return
    
    # Customer selection
    customer_id = st.selectbox("Select Customer", customers['user_id'])
    customer = customers[customers['user_id'] == customer_id].iloc[0]
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Current Balance", f"{customer['current_balance']:,.2f}")
    with col2:
        st.metric("Credit Limit", f"{customer['credit_limit']:,.2f}")
    
    # Credit adjustment
    with st.form("credit_form", border=True):
        new_limit = st.number_input("New Credit Limit", 
                                  value=float(customer['credit_limit']),
                                  min_value=0.0)
        balance_adjustment = st.number_input("Balance Adjustment", 
                                           value=0.0,
                                           help="Positive to add credit, negative to deduct")
        
        if st.form_submit_button("Update Credit", use_container_width=True):
            new_balance = float(customer['current_balance']) + balance_adjustment
            users_df.loc[users_df['user_id'] == customer_id, 'credit_limit'] = new_limit
            users_df.loc[users_df['user_id'] == customer_id, 'current_balance'] = new_balance
            users_df.to_csv("data/users.csv", index=False)
            st.success(f"Updated {customer['name']}'s credit limit to {new_limit:,.2f}")
            st.rerun()
