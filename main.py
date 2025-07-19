import streamlit as st
from pages.login import render as login_page
from pages.orders import render as orders_page
from pages.user_management import render as user_management_page
from pages.menu import render as menu_page
from pages.inventory import render as inventory_page
from pages.reports import render as reports_page
from pages.feedback import render as feedback_page
from pages.credit import render as credit_page

# Custom CSS for tabs
st.markdown("""
<style>
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    padding: 10px 20px;
    border-radius: 4px 4px 0 0;
    transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    background-color: #ff4b4b;
    color: white;
}
.stTabs [data-baseweb="tab"]:hover {
    background-color: #f0f2f6;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
    st.session_state.user_role = None

def main():
    if not st.session_state.user_id:
        login_page()
    else:
        # Header with logout
        header_col1, header_col2 = st.columns([5,1])
        with header_col1:
            st.title(f"Chai Chow Corner - {st.session_state.user_role.capitalize()} View")
        with header_col2:
            if st.button("Logout", use_container_width=True):
                st.session_state.clear()
                st.rerun()
        
        # Role-based tabs
        if st.session_state.user_role == "admin":
            tabs = st.tabs([
                "Orders", "User Management", "Menu", 
                "Inventory", "Reports", "Feedback", "Credit"
            ])
            with tabs[0]: orders_page()
            with tabs[1]: user_management_page()
            with tabs[2]: menu_page()
            with tabs[3]: inventory_page()
            with tabs[4]: reports_page()
            with tabs[5]: feedback_page()
            with tabs[6]: credit_page()
        
        elif st.session_state.user_role == "staff":
            tabs = st.tabs(["Orders", "Menu", "Inventory", "Feedback"])
            with tabs[0]: orders_page()
            with tabs[1]: menu_page()
            with tabs[2]: inventory_page()
            with tabs[3]: feedback_page()
        
        else:  # customer
            tabs = st.tabs(["Orders", "Menu", "Feedback"])
            with tabs[0]: orders_page()
            with tabs[1]: menu_page()
            with tabs[2]: feedback_page()

if __name__ == "__main__":
    main()
