import streamlit as st
import pandas as pd
from datetime import datetime
from utils.helpers import load_data, save_data

st.set_page_config(page_title="Order Management", layout="wide")

# Authentication check
if 'user_role' not in st.session_state:
    st.switch_page("app.py")

# Load data
menu = load_data('menu')
users = load_data('users')
orders = load_data('orders')

st.title("Order Management")

def place_order_form(user_role, customer_id=None):
    with st.form("order_form"):
        st.subheader("Create New Order")
        
        # Item selection
        items = st.multiselect("Select menu items", menu['item_name'].tolist())
        quantities = {}
        cols = st.columns(len(items))
        for i, item in enumerate(items):
            with cols[i]:
                quantities[item] = st.number_input(f"Quantity for {item}", min_value=1, value=1)
        
        # Payment options
        payment_options = ["Paid"]
        if user_role in ["admin", "staff"] or (user_role == "customer" and customer_id):
            payment_options.append("Credit")
        
        payment_mode = st.radio("Payment Mode", payment_options)
        
        if st.form_submit_button("Place Order"):
            # Calculate total
            total = sum(menu.loc[menu['item_name'] == item, 'price'].values[0] * quantities[item] for item in items)
            
            # Credit validation
            if payment_mode == "Credit":
                user = users[users['user_id'] == customer_id].iloc[0]
                if user['current_balance'] + total > user['credit_limit']:
                    st.warning(f"Credit limit exceeded! New balance: {user['current_balance'] + total}")
            
            # Create order record
            new_order = {
                'order_id': len(orders) + 1,
                'customer_id': customer_id if customer_id else 'WALK-IN',
                'staff_id': st.session_state.user_id if user_role in ["admin", "staff"] else None,
                'items': str({item: quantities[item] for item in items}),
                'total': total,
                'payment_mode': payment_mode,
                'status': 'Pending',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Update data
            orders = pd.concat([orders, pd.DataFrame([new_order])], ignore_index=True)
            if payment_mode == "Credit":
                users.loc[users['user_id'] == customer_id, 'current_balance'] += total
            
            save_data(orders, 'orders')
            save_data(users, 'users')
            st.success("Order placed successfully!")

# Customer view
if st.session_state.user_role == "customer":
    place_order_form("customer", st.session_state.user_id)

# Staff/Admin view
else:
    st.subheader("Walk-in Orders")
    customer_mobile = st.text_input("Customer Mobile (for credit orders)")
    if customer_mobile and customer_mobile not in users[users['role'] == 'customer']['user_id'].values:
        st.error("Customer not found")
    else:
        place_order_form(st.session_state.user_role, customer_mobile if customer_mobile else None)
    
    # Order management
    st.subheader("Recent Orders")
    st.dataframe(orders.sort_values('timestamp', ascending=False).head(20), hide_index=True)
