import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px

# App configuration
st.set_page_config(
    page_title="Chai Chow Corner",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Black & Red theme
st.markdown("""
    <style>
    :root {
        --primary-color: #ff4b4b;
        --background-color: #0e1117;
        --secondary-background-color: #262730;
        --text-color: #fafafa;
    }
    .stApp {
        background-color: var(--background-color);
        color: var(--text-color);
    }
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {
        background-color: var(--secondary-background-color) !important;
        color: var(--text-color) !important;
    }
    .st-bb {
        background-color: var(--secondary-background-color);
    }
    .st-at {
        background-color: var(--primary-color);
    }
    .st-ax {
        color: var(--primary-color);
    }
    .css-1aumxhk {
        background-color: #0e1117;
        background-image: none;
    }
    .css-1v3fvcr {
        color: var(--text-color);
    }
    .stButton>button {
        background-color: var(--primary-color);
        color: white;
        border: none;
    }
    .stButton>button:hover {
        background-color: #ff6b6b;
        color: white;
    }
    .stDataFrame {
        background-color: var(--secondary-background-color);
    }
    .css-1q8dd3e {
        color: var(--text-color);
    }
    .css-1v0mbdj {
        color: var(--text-color);
    }
    .css-1inwz65 {
        color: var(--text-color);
    }
    .stMarkdown {
        color: var(--text-color);
    }
    .stAlert {
        background-color: var(--secondary-background-color);
    }
    </style>
""", unsafe_allow_html=True)

# Data directory setup
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# File paths
USERS_FILE = os.path.join(DATA_DIR, "users.csv")
MENU_FILE = os.path.join(DATA_DIR, "menu.csv")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.csv")
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback.csv")
INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.csv")

# Initialize data files if they don't exist
def init_files():
    if not os.path.exists(USERS_FILE):
        pd.DataFrame(columns=[
            "user_id", "name", "mobile", "password", "role", 
            "status", "credit_limit", "current_balance", "created_at"
        ]).to_csv(USERS_FILE, index=False)
    
    if not os.path.exists(MENU_FILE):
        pd.DataFrame(columns=[
            "item_id", "name", "description", "category", "price", 
            "available", "prep_time", "created_at"
        ]).to_csv(MENU_FILE, index=False)
    
    if not os.path.exists(ORDERS_FILE):
        pd.DataFrame(columns=[
            "order_id", "customer_id", "staff_id", "items", "quantities", 
            "total_amount", "payment_mode", "status", "created_at"
        ]).to_csv(ORDERS_FILE, index=False)
    
    if not os.path.exists(FEEDBACK_FILE):
        pd.DataFrame(columns=[
            "feedback_id", "user_id", "name", "rating", "type", 
            "comment", "created_at"
        ]).to_csv(FEEDBACK_FILE, index=False)
    
    if not os.path.exists(INVENTORY_FILE):
        pd.DataFrame(columns=[
            "item_id", "name", "quantity", "unit", "threshold", 
            "last_updated"
        ]).to_csv(INVENTORY_FILE, index=False)

init_files()

# Utility functions
def load_data(file_path):
    try:
        return pd.read_csv(file_path)
    except:
        return pd.DataFrame()

def save_data(df, file_path):
    df.to_csv(file_path, index=False)

def generate_id(prefix):
    return f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

def get_current_user():
    return st.session_state.get('user_id'), st.session_state.get('user_role')

def is_logged_in():
    return 'user_id' in st.session_state

def login_user(user_id, user_role):
    st.session_state.user_id = user_id
    st.session_state.user_role = user_role

def logout_user():
    st.session_state.clear()

# Login Page
def login_page():
    st.title("Chai Chow Corner - Login")
    
    role = st.radio("Select Role", ["Admin", "Staff", "Customer"], horizontal=True)
    
    if role in ["Admin", "Staff"]:
        with st.form(f"{role.lower()}_login_form"):
            user_id = st.text_input("User ID")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Login"):
                users_df = load_data(USERS_FILE)
                user = users_df[(users_df['user_id'] == user_id) & 
                               (users_df['password'] == password) & 
                               (users_df['role'] == role.lower()) & 
                               (users_df['status'] == 'active')]
                
                if not user.empty:
                    login_user(user_id, role.lower())
                    st.rerun()
                else:
                    st.error("Invalid credentials or inactive account")
    
    else:  # Customer
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            with st.form("customer_login_form"):
                mobile = st.text_input("Mobile Number")
                password = st.text_input("Password", type="password")
                
                if st.form_submit_button("Login"):
                    users_df = load_data(USERS_FILE)
                    user = users_df[(users_df['mobile'] == mobile) & 
                                   (users_df['password'] == password) & 
                                   (users_df['role'] == 'customer') & 
                                   (users_df['status'] == 'active')]
                    
                    if not user.empty:
                        login_user(user.iloc[0]['user_id'], 'customer')
                        st.rerun()
                    else:
                        st.error("Invalid credentials or inactive account")
        
        with tab2:
            with st.form("customer_register_form"):
                name = st.text_input("Full Name")
                mobile = st.text_input("Mobile Number")
                password = st.text_input("Password", type="password")
                
                if st.form_submit_button("Register"):
                    users_df = load_data(USERS_FILE)
                    
                    if mobile in users_df['mobile'].values:
                        st.error("Mobile number already registered")
                    else:
                        new_user = pd.DataFrame([{
                            "user_id": generate_id("CUST"),
                            "name": name,
                            "mobile": mobile,
                            "password": password,
                            "role": "customer",
                            "status": "active",
                            "credit_limit": 0,
                            "current_balance": 0,
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }])
                        
                        users_df = pd.concat([users_df, new_user], ignore_index=True)
                        save_data(users_df, USERS_FILE)
                        st.success("Registration successful! Please login.")

# Order Page
def order_page():
    user_id, user_role = get_current_user()
    st.title("Place Order")
    
    menu_df = load_data(MENU_FILE)
    users_df = load_data(USERS_FILE)
    
    if menu_df.empty:
        st.warning("No menu items available")
        return
    
    # Display menu
    st.subheader("Menu")
    st.dataframe(menu_df[['name', 'description', 'price']], hide_index=True)
    
    # Order form
    with st.form("order_form"):
        items = menu_df['name'].tolist()
        quantities = {}
        
        if user_role == 'staff':
            customer_mobile = st.text_input("Customer Mobile (for credit orders, leave blank for walk-in)")
        
        cols = st.columns(4)
        for i, item in enumerate(items):
            quantities[item] = cols[i % 4].number_input(f"{item} Quantity", min_value=0, max_value=10, value=0)
        
        payment_mode = st.selectbox("Payment Mode", ["Paid", "Credit"]) if user_role != 'customer' else st.selectbox("Payment Mode", ["Paid", "Credit"])
        
        if st.form_submit_button("Place Order"):
            selected_items = [item for item in items if quantities[item] > 0]
            
            if not selected_items:
                st.error("Please select at least one item")
                return
            
            # Calculate total
            total = sum(quantities[item] * menu_df[menu_df['name'] == item]['price'].values[0] for item in selected_items)
            
            # Handle credit orders
            if payment_mode == "Credit":
                if user_role == "staff" and not customer_mobile:
                    st.error("Please enter customer mobile for credit order")
                    return
                
                customer_id = None
                if user_role == "customer":
                    customer_id = user_id
                elif user_role == "staff":
                    customer = users_df[(users_df['mobile'] == customer_mobile) & (users_df['role'] == 'customer')]
                    if customer.empty:
                        st.error("Customer not found")
                        return
                    customer_id = customer.iloc[0]['user_id']
                
                # Check credit limit
                customer_data = users_df[users_df['user_id'] == customer_id].iloc[0]
                new_balance = float(customer_data['current_balance']) + total
                credit_limit = float(customer_data['credit_limit'])
                
                if new_balance > credit_limit:
                    st.warning(f"Credit limit exceeded! Current balance: {new_balance}/{credit_limit}")
            
            # Create order
            new_order = pd.DataFrame([{
                "order_id": generate_id("ORD"),
                "customer_id": customer_id if payment_mode == "Credit" else None,
                "staff_id": user_id if user_role == "staff" else None,
                "items": ",".join(selected_items),
                "quantities": ",".join(str(quantities[item]) for item in selected_items),
                "total_amount": total,
                "payment_mode": payment_mode,
                "status": "pending",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }])
            
            orders_df = load_data(ORDERS_FILE)
            orders_df = pd.concat([orders_df, new_order], ignore_index=True)
            save_data(orders_df, ORDERS_FILE)
            
            # Update customer balance if credit order
            if payment_mode == "Credit":
                users_df.loc[users_df['user_id'] == customer_id, 'current_balance'] = new_balance
                save_data(users_df, USERS_FILE)
            
            st.success("Order placed successfully!")

# User Management Page (Admin Only)
def user_management_page():
    st.title("User Management")
    
    users_df = load_data(USERS_FILE)
    
    tab1, tab2, tab3 = st.tabs(["View Users", "Add User", "Edit User"])
    
    with tab1:
        st.subheader("All Users")
        
        role_filter = st.selectbox("Filter by Role", ["All", "admin", "staff", "customer"])
        status_filter = st.selectbox("Filter by Status", ["All", "active", "inactive"])
        
        filtered_df = users_df
        if role_filter != "All":
            filtered_df = filtered_df[filtered_df['role'] == role_filter]
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df['status'] == status_filter]
        
        st.dataframe(filtered_df, hide_index=True)
    
    with tab2:
        st.subheader("Add New User")
        
        with st.form("add_user_form"):
            name = st.text_input("Full Name")
            role = st.selectbox("Role", ["admin", "staff", "customer"])
            mobile = st.text_input("Mobile Number") if role == "customer" else None
            password = st.text_input("Password", type="password")
            status = st.selectbox("Status", ["active", "inactive"])
            credit_limit = st.number_input("Credit Limit", min_value=0, value=0) if role == "customer" else 0
            
            if st.form_submit_button("Add User"):
                new_user = pd.DataFrame([{
                    "user_id": generate_id(role.upper()),
                    "name": name,
                    "mobile": mobile if role == "customer" else None,
                    "password": password,
                    "role": role,
                    "status": status,
                    "credit_limit": credit_limit,
                    "current_balance": 0,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                
                users_df = pd.concat([users_df, new_user], ignore_index=True)
                save_data(users_df, USERS_FILE)
                st.success("User added successfully!")
    
    with tab3:
        st.subheader("Edit User")
        
        user_to_edit = st.selectbox("Select User", users_df['user_id'])
        user_data = users_df[users_df['user_id'] == user_to_edit].iloc[0]
        
        with st.form("edit_user_form"):
            name = st.text_input("Full Name", value=user_data['name'])
            status = st.selectbox("Status", ["active", "inactive"], index=0 if user_data['status'] == "active" else 1)
            
            if user_data['role'] == 'customer':
                credit_limit = st.number_input("Credit Limit", min_value=0, value=int(user_data['credit_limit']))
                current_balance = st.number_input("Current Balance", value=int(user_data['current_balance']))
            
            new_password = st.text_input("New Password (leave blank to keep current)", type="password")
            
            if st.form_submit_button("Update User"):
                users_df.loc[users_df['user_id'] == user_to_edit, 'name'] = name
                users_df.loc[users_df['user_id'] == user_to_edit, 'status'] = status
                
                if user_data['role'] == 'customer':
                    users_df.loc[users_df['user_id'] == user_to_edit, 'credit_limit'] = credit_limit
                    users_df.loc[users_df['user_id'] == user_to_edit, 'current_balance'] = current_balance
                
                if new_password:
                    users_df.loc[users_df['user_id'] == user_to_edit, 'password'] = new_password
                
                save_data(users_df, USERS_FILE)
                st.success("User updated successfully!")

# Menu Management Page
def menu_management_page():
    user_id, user_role = get_current_user()
    st.title("Menu Management")
    
    menu_df = load_data(MENU_FILE)
    
    if user_role in ['admin']:
        tab1, tab2, tab3 = st.tabs(["View Menu", "Add Item", "Edit Item"])
    else:
        tab1 = st.tabs(["View Menu"])[0]
    
    with tab1:
        st.subheader("Current Menu")
        st.dataframe(menu_df, hide_index=True)
    
    if user_role in ['admin']:
        with tab2:
            st.subheader("Add New Menu Item")
            
            with st.form("add_menu_item_form"):
                name = st.text_input("Item Name")
                description = st.text_area("Description")
                category = st.text_input("Category")
                price = st.number_input("Price", min_value=0.0, step=0.5)
                available = st.checkbox("Available", value=True)
                prep_time = st.number_input("Preparation Time (mins)", min_value=1, value=15)
                
                if st.form_submit_button("Add Item"):
                    new_item = pd.DataFrame([{
                        "item_id": generate_id("ITEM"),
                        "name": name,
                        "description": description,
                        "category": category,
                        "price": price,
                        "available": available,
                        "prep_time": prep_time,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    
                    menu_df = pd.concat([menu_df, new_item], ignore_index=True)
                    save_data(menu_df, MENU_FILE)
                    st.success("Menu item added successfully!")
        
        with tab3:
            st.subheader("Edit Menu Item")
            
            item_to_edit = st.selectbox("Select Item", menu_df['item_id'], key="edit_item_select")
            item_data = menu_df[menu_df['item_id'] == item_to_edit].iloc[0]
            
            with st.form("edit_menu_item_form"):
                name = st.text_input("Item Name", value=item_data['name'])
                description = st.text_area("Description", value=item_data['description'])
                category = st.text_input("Category", value=item_data['category'])
                price = st.number_input("Price", min_value=0.0, step=0.5, value=float(item_data['price']))
                available = st.checkbox("Available", value=bool(item_data['available']))
                prep_time = st.number_input("Preparation Time (mins)", min_value=1, value=int(item_data['prep_time']))
                
                if st.form_submit_button("Update Item"):
                    menu_df.loc[menu_df['item_id'] == item_to_edit, 'name'] = name
                    menu_df.loc[menu_df['item_id'] == item_to_edit, 'description'] = description
                    menu_df.loc[menu_df['item_id'] == item_to_edit, 'category'] = category
                    menu_df.loc[menu_df['item_id'] == item_to_edit, 'price'] = price
                    menu_df.loc[menu_df['item_id'] == item_to_edit, 'available'] = available
                    menu_df.loc[menu_df['item_id'] == item_to_edit, 'prep_time'] = prep_time
                    
                    save_data(menu_df, MENU_FILE)
                    st.success("Menu item updated successfully!")

# Inventory Page
def inventory_page():
    user_id, user_role = get_current_user()
    st.title("Inventory Management")
    
    inventory_df = load_data(INVENTORY_FILE)
    
    if user_role in ['admin']:
        tab1, tab2, tab3 = st.tabs(["View Inventory", "Add Item", "Edit Item"])
    else:
        tab1 = st.tabs(["View Inventory"])[0]
    
    with tab1:
        st.subheader("Current Inventory")
        
        # Show low stock alerts
        if not inventory_df.empty:
            low_stock = inventory_df[inventory_df['quantity'] <= inventory_df['threshold']]
            if not low_stock.empty:
                st.warning("Low Stock Alert!")
                st.dataframe(low_stock[['name', 'quantity', 'unit', 'threshold']], hide_index=True)
        
        st.dataframe(inventory_df, hide_index=True)
    
    if user_role in ['admin']:
        with tab2:
            st.subheader("Add Inventory Item")
            
            with st.form("add_inventory_item_form"):
                name = st.text_input("Item Name")
                quantity = st.number_input("Quantity", min_value=0.0, step=0.1)
                unit = st.text_input("Unit (kg, ltr, etc.)")
                threshold = st.number_input("Threshold for Alert", min_value=0.0, step=0.1)
                
                if st.form_submit_button("Add Item"):
                    new_item = pd.DataFrame([{
                        "item_id": generate_id("INV"),
                        "name": name,
                        "quantity": quantity,
                        "unit": unit,
                        "threshold": threshold,
                        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    
                    inventory_df = pd.concat([inventory_df, new_item], ignore_index=True)
                    save_data(inventory_df, INVENTORY_FILE)
                    st.success("Inventory item added successfully!")
        
        with tab3:
            st.subheader("Edit Inventory Item")
            
            item_to_edit = st.selectbox("Select Item", inventory_df['item_id'], key="edit_inv_select")
            item_data = inventory_df[inventory_df['item_id'] == item_to_edit].iloc[0]
            
            with st.form("edit_inventory_item_form"):
                name = st.text_input("Item Name", value=item_data['name'])
                quantity = st.number_input("Quantity", min_value=0.0, step=0.1, value=float(item_data['quantity']))
                unit = st.text_input("Unit (kg, ltr, etc.)", value=item_data['unit'])
                threshold = st.number_input("Threshold for Alert", min_value=0.0, step=0.1, value=float(item_data['threshold']))
                
                if st.form_submit_button("Update Item"):
                    inventory_df.loc[inventory_df['item_id'] == item_to_edit, 'name'] = name
                    inventory_df.loc[inventory_df['item_id'] == item_to_edit, 'quantity'] = quantity
                    inventory_df.loc[inventory_df['item_id'] == item_to_edit, 'unit'] = unit
                    inventory_df.loc[inventory_df['item_id'] == item_to_edit, 'threshold'] = threshold
                    inventory_df.loc[inventory_df['item_id'] == item_to_edit, 'last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    save_data(inventory_df, INVENTORY_FILE)
                    st.success("Inventory item updated successfully!")

# Reports Page (Admin Only)
def reports_page():
    st.title("Business Reports")
    
    orders_df = load_data(ORDERS_FILE)
    
    if orders_df.empty:
        st.warning("No orders data available")
        return
    
    # Convert date column to datetime
    orders_df['created_at'] = pd.to_datetime(orders_df['created_at'])
    
    # Date range selector
    col1, col2 = st.columns(2)
    start_date = col1.date_input("Start Date", value=orders_df['created_at'].min())
    end_date = col2.date_input("End Date", value=orders_df['created_at'].max())
    
    # Filter data
    filtered_df = orders_df[(orders_df['created_at'].dt.date >= start_date) & 
                          (orders_df['created_at'].dt.date <= end_date)]
    
    if filtered_df.empty:
        st.warning("No data for selected date range")
        return
    
    # Summary stats
    total_orders = len(filtered_df)
    total_revenue = filtered_df['total_amount'].sum()
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    st.subheader(f"Summary ({start_date} to {end_date})")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Orders", total_orders)
    col2.metric("Total Revenue", f"₹{total_revenue:,.2f}")
    col3.metric("Avg Order Value", f"₹{avg_order_value:,.2f}")
    
    # Daily trends
    st.subheader("Daily Trends")
    daily_df = filtered_df.set_index('created_at').resample('D').agg({
        'order_id': 'count',
        'total_amount': 'sum'
    }).rename(columns={'order_id': 'orders', 'total_amount': 'revenue'}).reset_index()
    
    fig1 = px.line(daily_df, x='created_at', y='orders', title="Daily Orders")
    fig2 = px.line(daily_df, x='created_at', y='revenue', title="Daily Revenue")
    
    st.plotly_chart(fig1, use_container_width=True)
    st.plotly_chart(fig2, use_container_width=True)
    
    # Payment mode breakdown
    st.subheader("Payment Mode Breakdown")
    payment_df = filtered_df.groupby('payment_mode').agg({
        'order_id': 'count',
        'total_amount': 'sum'
    }).rename(columns={'order_id': 'orders', 'total_amount': 'revenue'}).reset_index()
    
    col1, col2 = st.columns(2)
    fig3 = px.pie(payment_df, values='orders', names='payment_mode', title="Orders by Payment Mode")
    fig4 = px.pie(payment_df, values='revenue', names='payment_mode', title="Revenue by Payment Mode")
    
    col1.plotly_chart(fig3, use_container_width=True)
    col2.plotly_chart(fig4, use_container_width=True)

# Feedback Page
def feedback_page():
    user_id, user_role = get_current_user()
    st.title("Feedback")
    
    feedback_df = load_data(FEEDBACK_FILE)
    
    tab1, tab2 = st.tabs(["Submit Feedback", "View Feedback"])
    
    with tab1:
        with st.form("feedback_form"):
            name = st.text_input("Your Name (optional)")
            rating = st.slider("Rating", 1, 5, 5)
            feedback_type = st.selectbox("Type", ["General", "Complaint", "Suggestion", "Compliment"])
            comment = st.text_area("Your Feedback")
            
            if st.form_submit_button("Submit"):
                new_feedback = pd.DataFrame([{
                    "feedback_id": generate_id("FB"),
                    "user_id": user_id,
                    "name": name if name else "Anonymous",
                    "rating": rating,
                    "type": feedback_type,
                    "comment": comment,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                
                feedback_df = pd.concat([feedback_df, new_feedback], ignore_index=True)
                save_data(feedback_df, FEEDBACK_FILE)
                st.success("Thank you for your feedback!")
    
    with tab2:
        if user_role in ['admin', 'staff']:
            st.subheader("All Feedback")
            
            type_filter = st.selectbox("Filter by Type", ["All", "General", "Complaint", "Suggestion", "Compliment"])
            
            filtered_feedback = feedback_df
            if type_filter != "All":
                filtered_feedback = feedback_df[feedback_df['type'] == type_filter]
            
            st.dataframe(filtered_feedback, hide_index=True)
            
            # Feedback stats
            st.subheader("Feedback Statistics")
            if not feedback_df.empty:
                avg_rating = feedback_df['rating'].mean()
                st.metric("Average Rating", f"{avg_rating:.1f}/5")
                
                fig = px.histogram(feedback_df, x='rating', title="Rating Distribution")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Only staff and admin can view feedback")

# Customer Credit Page (Admin Only)
def customer_credit_page():
    st.title("Customer Credit Management")
    
    users_df = load_data(USERS_FILE)
    orders_df = load_data(ORDERS_FILE)
    
    customers_df = users_df[users_df['role'] == 'customer']
    
    if customers_df.empty:
        st.warning("No registered customers")
        return
    
    # Calculate due amounts
    st.subheader("Customer Credit Status")
    st.dataframe(customers_df[['name', 'mobile', 'credit_limit', 'current_balance']], hide_index=True)
    
    # Update credit limits
    st.subheader("Update Credit Limits")
    customer_to_update = st.selectbox("Select Customer", customers_df['user_id'])
    customer_data = customers_df[customers_df['user_id'] == customer_to_update].iloc[0]
    
    with st.form("credit_update_form"):
        new_limit = st.number_input("New Credit Limit", min_value=0, value=int(customer_data['credit_limit']))
        new_balance = st.number_input("Adjust Balance", value=int(customer_data['current_balance']))
        
        if st.form_submit_button("Update"):
            users_df.loc[users_df['user_id'] == customer_to_update, 'credit_limit'] = new_limit
            users_df.loc[users_df['user_id'] == customer_to_update, 'current_balance'] = new_balance
            save_data(users_df, USERS_FILE)
            st.success("Customer credit updated successfully!")

# Main App
def main():
    if not is_logged_in():
        login_page()
    else:
        user_id, user_role = get_current_user()
        
        # Sidebar with user info and logout
        with st.sidebar:
            st.markdown(f"**Logged in as:** {user_role.capitalize()}")
            if st.button("Logout"):
                logout_user()
                st.rerun()
        
        # Navigation based on user role
        if user_role == 'admin':
            pages = {
                "Place Order": order_page,
                "User Management": user_management_page,
                "Menu Management": menu_management_page,
                "Inventory": inventory_page,
                "Reports": reports_page,
                "Feedback": feedback_page,
                "Customer Credit": customer_credit_page
            }
        elif user_role == 'staff':
            pages = {
                "Place Order": order_page,
                "Menu": menu_management_page,
                "Inventory": inventory_page,
                "Feedback": feedback_page
            }
        else:  # customer
            pages = {
                "Place Order": order_page,
                "Menu": menu_management_page,
                "Feedback": feedback_page
            }
        
        selected_page = st.sidebar.selectbox("Navigation", list(pages.keys()))
        pages[selected_page]()

if __name__ == "__main__":
    main()
