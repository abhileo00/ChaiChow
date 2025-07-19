# pages/inventory.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime

def init_inventory():
    DATA_DIR = "data"
    os.makedirs(DATA_DIR, exist_ok=True)
    INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.csv")
    
    if not os.path.exists(INVENTORY_FILE):
        pd.DataFrame(columns=[
            "item_id", "name", "quantity", "unit", "threshold", "last_updated"
        ]).to_csv(INVENTORY_FILE, index=False)

def load_inventory():
    try:
        inventory_df = pd.read_csv("data/inventory.csv")
        return inventory_df
    except Exception as e:
        st.error(f"Error loading inventory: {str(e)}")
        return pd.DataFrame()

def save_inventory(df):
    try:
        df.to_csv("data/inventory.csv", index=False)
    except Exception as e:
        st.error(f"Error saving inventory: {str(e)}")

def render():
    st.title("Inventory Management")
    
    # Initialize inventory file if not exists
    init_inventory()
    
    # Load data
    inventory_df = load_inventory()
    if inventory_df.empty:
        st.warning("Inventory is empty. Please add items.")
    
    tab1, tab2 = st.tabs(["Current Stock", "Update Inventory"])
    
    with tab1:
        if not inventory_df.empty:
            low_stock = inventory_df[inventory_df['quantity'] <= inventory_df['threshold']]
            if not low_stock.empty:
                st.warning("Low Stock Alert!")
                st.dataframe(low_stock)
        
        st.dataframe(inventory_df, use_container_width=True)
    
    with tab2:
        if st.session_state.user_role not in ["admin", "staff"]:
            st.error("Staff access required")
            return
        
        action = st.radio("Action", ["Add Item", "Update Stock"], horizontal=True)
        
        if action == "Add Item":
            with st.form("add_inventory_item"):
                name = st.text_input("Item Name")
                quantity = st.number_input("Initial Quantity", min_value=0.0, step=1.0, value=10.0)
                unit = st.selectbox("Unit", ["kg", "g", "l", "ml", "units"])
                threshold = st.number_input("Low Stock Threshold", min_value=1.0, value=5.0)
                
                if st.form_submit_button("Add to Inventory"):
                    new_item = {
                        "item_id": f"INV_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "name": name,
                        "quantity": quantity,
                        "unit": unit,
                        "threshold": threshold,
                        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    inventory_df = pd.concat([inventory_df, pd.DataFrame([new_item])], ignore_index=True)
                    save_inventory(inventory_df)
                    st.success("Inventory item added!")
                    st.rerun()
        
        else:  # Update Stock
            if inventory_df.empty:
                st.warning("No items to update")
            else:
                item_id = st.selectbox("Select Item", inventory_df['item_id'])
                item = inventory_df[inventory_df['item_id'] == item_id].iloc[0]
                
                with st.form("update_stock"):
                    st.metric("Current Stock", f"{item['quantity']} {item['unit']}")
                    adjustment = st.number_input("Adjustment (+/-)", value=0.0, step=1.0)
                    new_threshold = st.number_input("New Threshold", value=float(item['threshold']))
                    
                    if st.form_submit_button("Update"):
                        new_quantity = float(item['quantity']) + adjustment
                        inventory_df.loc[inventory_df['item_id'] == item_id, 'quantity'] = new_quantity
                        inventory_df.loc[inventory_df['item_id'] == item_id, 'threshold'] = new_threshold
                        inventory_df.loc[inventory_df['item_id'] == item_id, 'last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        save_inventory(inventory_df)
                        st.success(f"Updated stock to {new_quantity} {item['unit']}")
                        st.rerun()
