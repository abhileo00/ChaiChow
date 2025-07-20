import streamlit as st
import pandas as pd
from utils.helpers import load_data, save_data

st.set_page_config(page_title="Inventory Management", layout="wide")

# Authentication check
if 'user_role' not in st.session_state:
    st.switch_page("app.py")

inventory = load_data('inventory')

st.title("Inventory Management")

# Low stock warning
low_stock = inventory[inventory['quantity'] < inventory['min_required']]
if not low_stock.empty:
    st.warning("Low stock items detected!")
    st.dataframe(low_stock[['item_name', 'quantity', 'min_required']], hide_index=True)

if st.session_state.user_role == "admin":
    # Admin can edit inventory
    with st.form("add_inventory_form"):
        st.subheader("Add Inventory Item")
        item_name = st.text_input("Item Name")
        quantity = st.number_input("Quantity", min_value=0)
        unit = st.text_input("Unit (kg, pieces, etc.)")
        min_required = st.number_input("Minimum Required", min_value=0)
        
        if st.form_submit_button("Add Item"):
            new_item = {
                'item_id': len(inventory) + 1,
                'item_name': item_name,
                'quantity': quantity,
                'unit': unit,
                'min_required': min_required
            }
            inventory = pd.concat([inventory, pd.DataFrame([new_item])], ignore_index=True)
            save_data(inventory, 'inventory')
            st.success("Item added to inventory")
    
    # Edit existing inventory
    st.subheader("Current Inventory")
    edited_inventory = st.data_editor(
        inventory,
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True
    )
    
    if st.button("Save Inventory"):
        save_data(edited_inventory, 'inventory')
        st.success("Inventory updated")

else:
    # Staff can view inventory
    st.subheader("Current Inventory")
    st.dataframe(inventory, hide_index=True)
