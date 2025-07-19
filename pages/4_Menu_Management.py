import streamlit as st
import pandas as pd
from datetime import datetime

def render():
    st.title("📜 Menu Management")
    menu_df = pd.read_csv("data/menu.csv")
    
    tab1, tab2 = st.tabs(["View Menu", "Edit Menu"])
    
    with tab1:
        st.dataframe(menu_df, hide_index=True)
    
    with tab2:
        if st.session_state.user_role not in ["admin", "staff"]:
            st.warning("⛔ Staff access required")
            return
        
        action = st.radio("Action", ["Add Item", "Edit Item"], horizontal=True)
        
        if action == "Add Item":
            with st.form("add_item"):
                name = st.text_input("Item Name")
                price = st.number_input("Price", min_value=0.0, step=0.5)
                category = st.text_input("Category")
                available = st.checkbox("Available", True)
                
                if st.form_submit_button("Add"):
                    new_item = {
                        "item_id": f"ITEM_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "name": name,
                        "price": price,
                        "category": category,
                        "available": available,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    menu_df = pd.concat([menu_df, pd.DataFrame([new_item])])
                    menu_df.to_csv("data/menu.csv", index=False)
                    st.success("✅ Item added!")
        
        else:  # Edit
            item_id = st.selectbox("Select Item", menu_df['item_id'])
            item = menu_df[menu_df['item_id'] == item_id].iloc[0]
            
            with st.form("edit_item"):
                name = st.text_input("Name", value=item['name'])
                price = st.number_input("Price", value=float(item['price']))
                available = st.checkbox("Available", bool(item['available']))
                
                if st.form_submit_button("Update"):
                    menu_df.loc[menu_df['item_id'] == item_id, 'name'] = name
                    menu_df.loc[menu_df['item_id'] == item_id, 'price'] = price
                    menu_df.loc[menu_df['item_id'] == item_id, 'available'] = available
                    menu_df.to_csv("data/menu.csv", index=False)
                    st.success("✅ Item updated!")
