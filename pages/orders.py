import streamlit as st
import pandas as pd
from datetime import datetime

def render():
    st.title("Place Order")
    
    try:
        menu_df = pd.read_csv("data/menu.csv")
        users_df = pd.read_csv("data/users.csv")
    except:
        st.error("Failed to load data files")
        return
    
    if menu_df.empty:
        st.warning("No menu items available")
        return
    
    with st.expander("View Full Menu"):
        st.dataframe(menu_df[['name', 'description', 'price']], hide_index=True)
    
    with st.form("order_form", border=True):
        items = menu_df['name'].tolist()
        quantities = {item: 0 for item in items}
        
        if st.session_state.user_role == "staff":
            customer_mobile = st.text_input("Customer Mobile (for credit orders)")
        
        st.subheader("Select Items")
        cols = st.columns(4)
        for i, item in enumerate(items):
            quantities[item] = cols[i % 4].number_input(
                f"{item}", min_value=0, max_value=10, value=0
            )
        
        payment_mode = st.selectbox(
            "Payment Mode", 
            ["Paid", "Credit"],
            disabled=st.session_state.user_role == "staff" and not customer_mobile
        )
        
        if st.form_submit_button("Place Order", use_container_width=True):
            selected_items = [item for item, qty in quantities.items() if qty > 0]
            if not selected_items:
                st.error("Please select at least one item")
                return
            
            total = sum(
                quantities[item] * menu_df[menu_df['name'] == item]['price'].values[0] 
                for item in selected_items
            )
            
            customer_id = None
            if payment_mode == "Credit":
                if st.session_state.user_role == "customer":
                    customer_id = st.session_state.user_id
                elif st.session_state.user_role == "staff":
                    customer = users_df[users_df['mobile'] == customer_mobile]
                    if not customer.empty:
                        customer_id = customer.iloc[0]['user_id']
                    else:
                        st.error("Customer not found")
                        return
                
                customer_data = users_df[users_df['user_id'] == customer_id].iloc[0]
                new_balance = float(customer_data['current_balance']) + total
                if new_balance > float(customer_data['credit_limit']):
                    st.warning(f"Credit limit exceeded! Balance: {new_balance}/{customer_data['credit_limit']}")
            
            new_order = {
                "order_id": f"ORD_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "customer_id": customer_id,
                "staff_id": st.session_state.user_id if st.session_state.user_role == "staff" else None,
                "items": ",".join(selected_items),
                "quantities": ",".join(str(quantities[i]) for i in selected_items),
                "total_amount": total,
                "payment_mode": payment_mode,
                "status": "Pending",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            try:
                orders_df = pd.read_csv("data/orders.csv")
                orders_df = pd.concat([orders_df, pd.DataFrame([new_order])], ignore_index=True)
                orders_df.to_csv("data/orders.csv", index=False)
                
                if payment_mode == "Credit":
                    users_df.loc[users_df['user_id'] == customer_id, 'current_balance'] = new_balance
                    users_df.to_csv("data/users.csv", index=False)
                
                st.success(f"Order placed! Total: {total:.2f}")
            except Exception as e:
                st.error(f"Failed to save order: {str(e)}")
