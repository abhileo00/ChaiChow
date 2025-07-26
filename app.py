import streamlit as st
import pandas as pd
from utils.db import init_db, get_data_as_df
from modules.auth import login_form
from modules.expenses import manage_expenses
from modules.sales import manage_sales
from modules.inventory import manage_inventory
from modules.reports import generate_reports

# Initialize database
init_db()

# App configuration
st.set_page_config(
    page_title="Smart Food Business Manager",
    layout="wide",
    page_icon="🍕"
)

# Session state initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Login form
login_form()

# Main app if logged in
if st.session_state.logged_in:
    st.title("🍕 Smart Food Business Manager")
    st.markdown("---")
    
    # Navigation
    pages = {
        "📊 Dashboard": "dashboard",
        "💸 Expenses": "expenses",
        "💰 Sales": "sales",
        "📦 Inventory": "inventory",
        "📝 Reports": "reports"
    }
    
    # Sidebar navigation
    with st.sidebar:
        st.title("Navigation")
        selected = st.radio("Go to", list(pages.keys()))
    
    # Page routing
    if pages[selected] == "dashboard":
        st.header("Business Dashboard")
        col1, col2, col3 = st.columns(3)
        
        # Get metrics
        sales_df = get_data_as_df("sales")
        expenses_df = get_data_as_df("expenses")
        
        total_sales = (sales_df['quantity'] * sales_df['rate']).sum() if not sales_df.empty else 0
        total_expenses = expenses_df['amount'].sum() if not expenses_df.empty else 0
        profit_loss = total_sales - total_expenses
        
        with col1:
            st.metric("Total Sales", f"${total_sales:.2f}")
        with col2:
            st.metric("Total Expenses", f"${total_expenses:.2f}")
        with col3:
            st.metric("Profit/Loss", f"${profit_loss:.2f}", 
                      delta_color="inverse" if profit_loss < 0 else "normal")
        
        st.markdown("---")
        st.subheader("Recent Activities")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Recent Sales**")
            st.dataframe(sales_df.tail(3) if not sales_df.empty else pd.DataFrame())
        
        with col2:
            st.write("**Recent Expenses**")
            st.dataframe(expenses_df.tail(3) if not expenses_df.empty else pd.DataFrame())
    
    elif pages[selected] == "expenses":
        manage_expenses()
    
    elif pages[selected] == "sales":
        manage_sales()
    
    elif pages[selected] == "inventory":
        manage_inventory()
    
    elif pages[selected] == "reports":
        generate_reports()
else:
    st.title("Smart Food Business Manager")
    st.markdown("""
    ## Welcome to SFBM!
    Please login using the sidebar to access the business management tools.
    
    **Admin Credentials:**
    - Username: `admin`
    - Password: `admin123`
    """)
    st.image("https://cdn.pixabay.com/photo/2017/09/30/15/10/pizza-2802332_1280.jpg", 
             use_column_width=True)
