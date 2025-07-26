import streamlit as st
import pandas as pd
from utils.db import get_db_connection

def update_inventory(item, quantity_change):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if item exists
    cursor.execute("SELECT quantity FROM inventory WHERE item = ?", (item,))
    result = cursor.fetchone()
    
    if result:
        new_quantity = result[0] + quantity_change
        if new_quantity < 0:
            return False
        cursor.execute(
            "UPDATE inventory SET quantity = ? WHERE item = ?",
            (new_quantity, item)
        )
    else:
        if quantity_change < 0:
            return False
        cursor.execute(
            "INSERT INTO inventory (item, quantity) VALUES (?, ?)",
            (item, quantity_change)
        )
    
    conn.commit()
    conn.close()
    return True

def manage_inventory():
    st.header("Inventory Management")
    
    # Add new inventory
    with st.form("inventory_form"):
        st.subheader("Add/Update Inventory")
        item = st.text_input("Item Name")
        quantity = st.number_input("Quantity", min_value=0, step=1)
        
        if st.form_submit_button("Update Inventory"):
            if item and quantity >= 0:
                if update_inventory(item, quantity):
                    st.success("Inventory updated successfully!")
                else:
                    st.error("Error updating inventory")
            else:
                st.error("Please enter valid values")
    
    # View current inventory
    st.subheader("Current Inventory")
    conn = get_db_connection()
    inventory_df = pd.read_sql("SELECT * FROM inventory", conn)
    conn.close()
    
    if not inventory_df.empty:
        st.dataframe(inventory_df)
    else:
        st.info("Inventory is empty")
