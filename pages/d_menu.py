import streamlit as st
import pandas as pd
from datetime import datetime

def render():
    st.header("📜 Menu Management")
    try:
        menu_df = pd.read_csv("data/menu.csv")
    except:
        st.error("Failed to load menu data")
        return
    
    tab1, tab2 = st.tabs(["View Menu", "Manage Items"])
    
    with tab1:
        st.dataframe(menu_df, hide_index=True, use_container_width=True)
    
    with tab2:
        if st.session_state.user_role not in ["admin", "staff"]:
            st.error("⛔ Staff access required")
            return
        
        action = st.radio("Action", ["Add Item", "Edit Item"], horizontal=True)
        
        if action == "Add Item":
            with st.form("add_item", border=True):
                name = st.text_input("Item Name")
                description = st.text_area("Description")
                category = st.text_input("Category")
                price = st.number_input("Price", min_value=0.0, step=0.5, value=10.0)
                prep_time = st.number_input("Prep Time (mins)", min_value=1, value=15)
                available = st.checkbox("Available", True)
                
                if st.form_submit_button("Add Item", use_container_width=True):
                    new_item = {
                        "item_id": f"ITEM_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "name": name,
                        "description": description,
                        "category": category,
                        "price": price,
                        "prep_time": prep_time,
                        "available": available,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    menu_df = pd.concat([menu_df, pd.DataFrame([new_item])], ignore_index=True)
                    menu_df.to_csv("data/menu.csv", index=False)
                    st.success("✅ Item added to menu!")
                    st.rerun()
        
        else:  # Edit Item
            item_id = st.selectbox("Select Item", menu_df['item_id'])
            item = menu_df[menu_df['item_id'] == item_id].iloc[0]
            
            with st.form("edit_item", border=True):
                name = st.text_input("Name", value=item['name'])
                description = st.text_area("Description", value=item['description'])
                category = st.text_input("Category", value=item['category'])
                price = st.number_input("Price", value=float(item['price']))
                prep_time = st.number_input("Prep Time", value=int(item['prep_time']))
                available = st.checkbox("Available", value=bool(item['available']))
                
                if st.form_submit_button("Update Item", use_container_width=True):
                    menu_df.loc[menu_df['item_id'] == item_id, 'name'] = name
                    menu_df.loc[menu_df['item_id'] == item_id, 'description'] = description
                    menu_df.loc[menu_df['item_id'] == item_id, 'category'] = category
                    menu_df.loc[menu_df['item_id'] == item_id, 'price'] = price
                    menu_df.loc[menu_df['item_id'] == item_id, 'prep_time'] = prep_time
                    menu_df.loc[menu_df['item_id'] == item_id, 'available'] = available
                    menu_df.to_csv("data/menu.csv", index=False)
                    st.success("✅ Menu item updated!")
                    st.rerun()
