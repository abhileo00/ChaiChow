import streamlit as st
import pandas as pd
from utils.helpers import load_data, save_data

st.set_page_config(page_title="Menu Management", layout="wide")

# Authentication check
if 'user_role' not in st.session_state:
    st.switch_page("app.py")

menu = load_data('menu')

st.title("Menu Management")

if st.session_state.user_role == "admin":
    # Admin can edit menu
    with st.form("add_item_form"):
        st.subheader("Add New Item")
        item_name = st.text_input("Item Name")
        description = st.text_area("Description")
        price = st.number_input("Price", min_value=0.0, step=0.5)
        category = st.text_input("Category")
        available = st.checkbox("Available", value=True)
        
        if st.form_submit_button("Add Item"):
            new_item = {
                'item_id': len(menu) + 1,
                'item_name': item_name,
                'description': description,
                'price': price,
                'category': category,
                'available': available
            }
            menu = pd.concat([menu, pd.DataFrame([new_item])], ignore_index=True)
            save_data(menu, 'menu')
            st.success("Item added to menu")
    
    # Edit existing menu
    st.subheader("Current Menu")
    edited_menu = st.data_editor(
        menu,
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True
    )
    
    if st.button("Save Menu"):
        save_data(edited_menu, 'menu')
        st.success("Menu updated")

else:
    # Staff and customers can view
    st.subheader("Our Menu")
    st.dataframe(menu[menu['available']][['item_name', 'description', 'price']], hide_index=True)
