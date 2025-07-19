import streamlit as st
import pandas as pd
from datetime import datetime

def render():
    st.title("📦 Inventory Management")
    inv_df = pd.read_csv("data/inventory.csv")
    
    tab1, tab2 = st.tabs(["Current Stock", "Update Stock"])
    
    with tab1:
        st.dataframe(inv_df, hide_index=True)
        low_stock = inv_df[inv_df['quantity'] <= inv_df['threshold']]
        if not low_stock.empty:
            st.warning("🚨 Low Stock Items")
            st.dataframe(low_stock)
    
    with tab2:
        if st.session_state.user_role not in ["admin", "staff"]:
            st.warning("⛔ Staff access required")
            return
        
        item_id = st.selectbox("Select Item", inv_df['item_id'])
        item = inv_df[inv_df['item_id'] == item_id].iloc[0]
        
        with st.form("update_stock"):
            new_qty = st.number_input("Quantity", value=float(item['quantity']))
            threshold = st.number_input("Alert Threshold", value=float(item['threshold']))
            
            if st.form_submit_button("Update"):
                inv_df.loc[inv_df['item_id'] == item_id, 'quantity'] = new_qty
                inv_df.loc[inv_df['item_id'] == item_id, 'threshold'] = threshold
                inv_df.to_csv("data/inventory.csv", index=False)
                st.success("✅ Inventory updated!")
