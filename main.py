import streamlit as st
from pages import (
    a_login as login_page,
    b_orders as orders_page,
    c_user_management as user_management_page,
    d_menu as menu_page,
    e_inventory as inventory_page,
    f_reports as reports_page,
    g_feedback as feedback_page,
    h_credit as credit_page
)

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
    st.session_state.user_role = None

def main():
    if not st.session_state.user_id:
        login_page.render()
    else:
        st.title(f"Chai Chow Corner - {st.session_state.user_role.capitalize()} Dashboard")
        
        # Logout button at top right
        col1, col2 = st.columns([5,1])
        with col2:
            if st.button("🚪 Logout"):
                st.session_state.clear()
                st.rerun()
        
        # Role-based tab selection
        if st.session_state.user_role == "admin":
            tabs = st.tabs([
                "Orders", "User Management", "Menu", 
                "Inventory", "Reports", "Feedback", "Credit"
            ])
            
            with tabs[0]: orders_page.render()
            with tabs[1]: user_management_page.render()
            with tabs[2]: menu_page.render()
            with tabs[3]: inventory_page.render()
            with tabs[4]: reports_page.render()
            with tabs[5]: feedback_page.render()
            with tabs[6]: credit_page.render()
            
        elif st.session_state.user_role == "staff":
            tabs = st.tabs(["Orders", "Menu", "Inventory", "Feedback"])
            
            with tabs[0]: orders_page.render()
            with tabs[1]: menu_page.render()
            with tabs[2]: inventory_page.render()
            with tabs[3]: feedback_page.render()
            
        else:  # customer
            tabs = st.tabs(["Orders", "Menu", "Feedback"])
            
            with tabs[0]: orders_page.render()
            with tabs[1]: menu_page.render()
            with tabs[2]: feedback_page.render()

if __name__ == "__main__":
    main()
