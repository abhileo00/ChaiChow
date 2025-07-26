import streamlit as st
from utils.db import init_db
from modules.auth import login_form, check_login
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
    
    # Dashboard
    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"
    
    # Sidebar navigation
    with st.sidebar:
        st.title("Navigation")
        pages = {
            "Dashboard": "📊 Dashboard",
            "Expenses": "💸 Expenses",
            "Sales": "💰 Sales",
            "Inventory": "📦 Inventory",
            "Reports": "📝 Reports"
        }
        
        for page_name, page_icon in pages.items():
            if st.button(f"{page_icon} {page_name}"):
                st.session_state.page = page_name
    
    # Page routing
    if st.session_state.page == "Dashboard":
        st.header("Business Dashboard")
        col1, col2, col3 = st.columns(3)
        
        # Get business metrics
        from utils.db import get_db_connection
        conn = get_db_connection()
        
        # Total Sales
        sales_df = pd.read_sql("SELECT * FROM sales", conn)
        if not sales_df.empty:
            total_sales = (sales_df['quantity'] * sales_df['rate']).sum()
        else:
            total_sales = 0
        
        # Total Expenses
        expenses_df = pd.read_sql("SELECT * FROM expenses", conn)
        total_expenses = expenses_df['amount'].sum() if not expenses_df.empty else 0
        
        # Profit/Loss
        profit_loss = total_sales - total_expenses
        
        conn.close()
        
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
            if not sales_df.empty:
                st.dataframe(sales_df.tail(3))
            else:
                st.info("No recent sales")
        
        with col2:
            st.write("**Recent Expenses**")
            if not expenses_df.empty:
                st.dataframe(expenses_df.tail(3))
            else:
                st.info("No recent expenses")
    
    elif st.session_state.page == "Expenses":
        manage_expenses()
    
    elif st.session_state.page == "Sales":
        manage_sales()
    
    elif st.session_state.page == "Inventory":
        manage_inventory()
    
    elif st.session_state.page == "Reports":
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
