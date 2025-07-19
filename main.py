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
        st.sidebar.title(f"👤 {st.session_state.user_role.capitalize()} Panel")
        if st.sidebar.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

        # Role-based navigation
        pages = {
            "admin": ["Orders", "User Management", "Menu", "Inventory", "Reports", "Feedback", "Credit"],
            "staff": ["Orders", "Menu", "Inventory", "Feedback"],
            "customer": ["Orders", "Menu", "Feedback"]
        }
        
        selection = st.sidebar.selectbox("Navigation", pages[st.session_state.user_role])
        
        if selection == "Orders":
            orders_page.render()
        elif selection == "User Management":
            user_management_page.render()
        elif selection == "Menu":
            menu_page.render()
        elif selection == "Inventory":
            inventory_page.render()
        elif selection == "Reports":
            reports_page.render()
        elif selection == "Feedback":
            feedback_page.render()
        elif selection == "Credit":
            credit_page.render()

if __name__ == "__main__":
    main()
