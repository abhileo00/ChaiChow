import streamlit as st
import pandas as pd
from utils.db import get_db_connection, execute_query, get_data_as_df
from datetime import date
import modules.inventory as inventory

def manage_sales():
    st.header("💰 Sales Management")
    
    # Get available inventory items
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT item FROM inventory WHERE quantity > 0")
    items = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not items:
        st.warning("No items available in inventory. Add inventory first.")
        return
    
    with st.form("sales_form"):
        item = st.selectbox("Item", items)
        quantity = st.number_input("Quantity", min_value=1, step=1)
        rate = st.number_input("Rate per unit ($)", min_value=0.0, step=0.1)
        sale_date = st.date_input("Date", date.today())
        
        if st.form_submit_button("Record Sale"):
            if quantity <= 0 or rate <= 0:
                st.error("Quantity and rate must be positive")
            else:
                # Update inventory
                if inventory.update_inventory(item, -quantity):
                    execute_query(
                        "INSERT INTO sales (item, quantity, rate, date) VALUES (?, ?, ?, ?)",
                        (item, quantity, rate, sale_date)
                    )
                    st.success("Sale recorded successfully!")
                else:
                    st.error("Insufficient inventory or item not found")
    
    st.subheader("Sales Records")
    sales_df = get_data_as_df("sales")
    
    if not sales_df.empty:
        st.dataframe(sales_df)
        st.download_button(
            "Export as CSV",
            sales_df.to_csv(index=False),
            "sales.csv",
            "text/csv"
        )
    else:
        st.info("No sales recorded yet")
