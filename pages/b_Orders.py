import streamlit as st
import pandas as pd
from datetime import datetime

def render():
    st.title("🍽️ Place Order")
    
    # Load data
    menu_df = pd.read_csv("data/menu.csv")
    users_df = pd.read_csv("data/users.csv")
    
    # Display menu
    st.subheader("Menu Items")
    st.dataframe(menu_df[['name', 'price']], hide_index=True)
    
    # Order form
    with st.form("order_form"):
        items = menu_df['name'].tolist()
        quantities = {item: 0 for item in items}
        
        if st.session_state.user_role == "staff":
            customer_mobile = st.text_input("Customer Mobile (for credit orders)")
        
        # Dynamic quantity inputs
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
        
        if st.form_submit_button("Place Order"):
            selected_items = [item for item, qty in quantities.items() if qty > 0]
            if not selected_items:
                st.error("Please select at least one item")
                return
            
            # Calculate total
            total = sum(
                quantities[item] * menu_df[menu_df['name'] == item]['price'].values[0] 
                for item in selected_items
            )
            
            # Process order
            new_order = {
                "order_id": f"ORD_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "customer_id": st.session_state.user_id if payment_mode == "Credit" else None,
                "staff_id": st.session_state.user_id if st.session_state.user_role == "staff" else None,
                "items": ",".join(selected_items),
                "quantities": ",".join(str(quantities[i]) for i in selected_items),
                "total_amount": total,
                "payment_mode": payment_mode,
                "status": "Pending",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Save order
            orders_df = pd.read_csv("data/orders.csv")
            orders_df = pd.concat([orders_df, pd.DataFrame([new_order])])
            orders_df.to_csv("data/orders.csv", index=False)
            
            st.success(f"✅ Order placed! Total: ₹{total:.2f}")
