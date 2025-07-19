import streamlit as st
import pandas as pd
from datetime import datetime

def render():
    st.header("📦 Inventory Management")
    try:
        inventory_df = pd.read_csv("data/inventory.csv")
    except:
        st.error("Failed to load inventory data")
        return
    
    tab1, tab2 = st.tabs(["Current Stock", "Update Inventory"])
    
    with tab1:
        if not inventory_df.empty:
            low_stock = inventory_df[inventory_df['quantity'] <= inventory_df['threshold']]
            if not low_stock.empty:
                st.warning("🚨 Low Stock Alert!")
                st.dataframe(low_stock, hide_index=True, use_container_width=True)
        
        st.dataframe(inventory_df, hide_index=True, use_container_width=True)
    
    with tab2:
        if st.session_state.user_role not in ["admin", "staff"]:
            st.error("⛔ Staff access required")
            return
        
        action = st.radio("Action", ["Add Item", "Update Stock"], horizontal=True)
        
        if action == "Add Item":
            with st.form("add_inventory_item", border=True):
                name = st.text_input("Item Name")
                quantity = st.number_input("Initial Quantity", min_value=0.0, step=1.0, value=10.0)
                unit = st.selectbox("Unit", ["kg", "g", "l", "ml", "units"])
                threshold = st.number_input("Low Stock Threshold", min_value=1.0, value=5.0)
                
                if st.form_submit_button("Add to Inventory", use_container_width=True):
                    new_item = {
                        "item_id": f"INV_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "name": name,
                        "quantity": quantity,
                        "unit": unit,
                        "threshold": threshold,
                        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    inventory_df = pd.concat([inventory_df, pd.DataFrame([new_item])], ignore_index=True)
                    inventory_df.to_csv("data/inventory.csv", index=False)
                    st.success("✅ Inventory item added!")
                    st.rerun()
        
        else:  # Update Stock
            item_id = st.selectbox("Select Item", inventory_df['item_id'])
            item = inventory_df[inventory_df['item_id'] == item_id].iloc[0]
            
            with st.form("update_stock", border=True):
                st.metric("Current Stock", f"{item['quantity']} {item['unit']}")
                adjustment = st.number_input("Adjustment (+/-)", value=0.0, step=1.0)
                new_threshold = st.number_input("New Threshold", value=float(item['threshold']))
                
                if st.form_submit_button("Update", use_container_width=True):
                    new_quantity = float(item['quantity']) + adjustment
                    inventory_df.loc[inventory_df['item_id'] == item_id, 'quantity'] = new_quantity
                    inventory_df.loc[inventory_df['item_id'] == item_id, 'threshold'] = new_threshold
                    inventory_df.loc[inventory_df['item_id'] == item_id, 'last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    inventory_df.to_csv("data/inventory.csv", index=False)
                    st.success(f"✅ Updated stock to {new_quantity} {item['unit']}")
                    st.rerun()
