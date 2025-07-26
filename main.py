import streamlit as st
import pandas as pd
import os
import datetime
from streamlit_option_menu import option_menu

# Create data directory if not exists
if not os.path.exists('data'):
    os.makedirs('data')

# Initialize CSV files with headers
def init_csv(file_path, columns):
    if not os.path.exists(file_path):
        df = pd.DataFrame(columns=columns)
        df.to_csv(file_path, index=False)

# Initialize all data files
init_csv('data/users.csv', ['user_id', 'name', 'mobile', 'password', 'role', 'status', 'credit_limit', 'current_balance'])
init_csv('data/menu.csv', ['item_id', 'name', 'description', 'price', 'category'])
init_csv('data/inventory.csv', ['item_id', 'item_name', 'quantity', 'unit'])
init_csv('data/orders.csv', ['order_id', 'user_id', 'mobile', 'items', 'total', 'date', 'payment_mode', 'status'])
init_csv('data/feedback.csv', ['feedback_id', 'user_id', 'name', 'rating', 'type', 'comment', 'date'])

# Custom CSS for black and red theme
st.markdown("""
<style>
:root {
    --primary: #ff4b4b;
    --background: #000000;
    --secondary-background: #1a1a1a;
    --text: #ffffff;
}

body {
    color: var(--text);
    background-color: var(--background);
}

.stApp {
    background-color: var(--background);
}

.stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {
    color: white;
    background-color: var(--secondary-background) !important;
}

.stButton>button {
    background-color: var(--primary) !important;
    color: black !important;
    font-weight: bold;
    border: none;
}

.stSelectbox>div>div>div {
    background-color: var(--secondary-background);
    color: white;
}

.st-bb, .st-at, .st-ag, .st-af, .st-ae, .st-ad, .st-ac, .st-ab, .st-aa, .st-df {
    border-color: #ff4b4b !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
}

.stTabs [data-baseweb="tab"] {
    background-color: var(--secondary-background);
    color: white;
    border-radius: 4px;
    padding: 8px 16px;
    margin: 0 2px;
}

.stTabs [aria-selected="true"] {
    background-color: var(--primary) !important;
    color: black !important;
}
</style>
""", unsafe_allow_html=True)

# Session state initialization
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.user_id = None
    st.session_state.current_page = 'Login'

# Data loading functions
def load_data(file_name):
    try:
        return pd.read_csv(f'data/{file_name}.csv')
    except:
        return pd.DataFrame()

def save_data(df, file_name):
    df.to_csv(f'data/{file_name}.csv', index=False)

# Login functions
def admin_staff_login():
    with st.form("Admin/Staff Login"):
        user_id = st.text_input("User ID")
        password = st.text_input("Password", type='password')
        submit = st.form_submit_button("Login")
        
        if submit:
            users = load_data('users')
            user = users[(users['user_id'] == user_id) & (users['password'] == password) & (users['role'].isin(['Admin', 'Staff']))]
            if not user.empty:
                st.session_state.logged_in = True
                st.session_state.user_role = user['role'].values[0]
                st.session_state.user_id = user_id
                st.session_state.current_page = 'Order'
                st.rerun()
            else:
                st.error("Invalid credentials")

def customer_login():
    with st.form("Customer Login"):
        mobile = st.text_input("Mobile Number")
        password = st.text_input("Password", type='password')
        col1, col2 = st.columns([1, 2])
        with col1:
            login_btn = st.form_submit_button("Login")
        with col2:
            register_btn = st.form_submit_button("Register")
        
        if login_btn:
            users = load_data('users')
            user = users[(users['mobile'] == mobile) & (users['password'] == password) & (users['role'] == 'Customer')]
            if not user.empty:
                st.session_state.logged_in = True
                st.session_state.user_role = 'Customer'
                st.session_state.user_id = user['user_id'].values[0]
                st.session_state.current_page = 'Order'
                st.rerun()
            else:
                st.error("Invalid credentials")
        elif register_btn:
            users = load_data('users')
            if mobile in users['mobile'].values:
                st.error("Mobile number already registered")
            else:
                new_user = pd.DataFrame([{
                    'user_id': f"C{datetime.datetime.now().timestamp()}",
                    'name': 'New Customer',
                    'mobile': mobile,
                    'password': password,
                    'role': 'Customer',
                    'status': 'Active',
                    'credit_limit': 0,
                    'current_balance': 0
                }])
                save_data(pd.concat([users, new_user], ignore_index=True), 'users')
                st.success("Registration successful! Please login")

# Page functions
def order_page():
    st.title("🧾 Place Order")
    menu = load_data('menu')
    
    if menu.empty:
        st.warning("No menu items available")
        return
    
    # Display menu items
    items = {}
    for _, row in menu.iterrows():
        with st.container():
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image("https://via.placeholder.com/100?text=Food+Image", width=100)
            with col2:
                st.subheader(row['name'])
                st.caption(row['description'])
                st.write(f"₹{row['price']}")
                quantity = st.number_input(f"Quantity for {row['name']}", min_value=0, max_value=10, key=row['item_id'])
                items[row['item_id']] = quantity
    
    # Payment section
    total = sum(menu.loc[menu['item_id'] == item_id, 'price'].values[0] * qty 
                for item_id, qty in items.items() if qty > 0)
    
    if total > 0:
        st.subheader(f"Total: ₹{total:.2f}")
        
        payment_mode = None
        if st.session_state.user_role == 'Customer':
            payment_mode = st.radio("Payment Mode", ["Paid", "Credit"])
        else:
            payment_mode = st.radio("Payment Mode", ["Paid", "Credit"], index=0)
            if payment_mode == "Credit":
                mobile = st.text_input("Customer Mobile Number")
        
        if st.button("Place Order"):
            orders = load_data('orders')
            order_id = f"ORD{datetime.datetime.now().timestamp()}"
            
            # Handle credit payment validation
            if payment_mode == "Credit":
                users = load_data('users')
                if st.session_state.user_role == 'Customer':
                    user = users[users['user_id'] == st.session_state.user_id]
                else:
                    user = users[users['mobile'] == mobile]
                
                if user.empty:
                    st.error("Customer not found")
                    return
                
                user = user.iloc[0]
                new_balance = user['current_balance'] + total
                
                if new_balance > user['credit_limit']:
                    st.warning("Credit limit exceeded. Order marked as due")
                
                # Update user balance
                users.loc[users['user_id'] == user['user_id'], 'current_balance'] = new_balance
                save_data(users, 'users')
            
            # Save order
            order_data = {
                'order_id': order_id,
                'user_id': st.session_state.user_id if st.session_state.user_role == 'Customer' else '',
                'mobile': mobile if payment_mode == "Credit" and st.session_state.user_role != 'Customer' else '',
                'items': ",".join([f"{item_id}:{qty}" for item_id, qty in items.items() if qty > 0]),
                'total': total,
                'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'payment_mode': payment_mode,
                'status': "Due" if payment_mode == "Credit" and new_balance > user['credit_limit'] else "Paid"
            }
            
            save_data(pd.concat([orders, pd.DataFrame([order_data])], ignore_index=True), 'orders')
            st.success("Order placed successfully!")

def user_management():
    st.title("👤 User Management")
    users = load_data('users')
    
    tabs = st.tabs(["Add User", "Manage Users"])
    
    with tabs[0]:
        with st.form("add_user_form"):
            name = st.text_input("Name")
            mobile = st.text_input("Mobile Number")
            password = st.text_input("Password", type='password')
            role = st.selectbox("Role", ["Admin", "Staff", "Customer"])
            status = st.selectbox("Status", ["Active", "Inactive"])
            credit_limit = st.number_input("Credit Limit", min_value=0, value=1000) if role == "Customer" else 0
            
            if st.form_submit_button("Add User"):
                new_user = pd.DataFrame([{
                    'user_id': f"{role[0]}{datetime.datetime.now().timestamp()}",
                    'name': name,
                    'mobile': mobile,
                    'password': password,
                    'role': role,
                    'status': status,
                    'credit_limit': credit_limit,
                    'current_balance': 0
                }])
                
                save_data(pd.concat([users, new_user], ignore_index=True), 'users')
                st.success("User added successfully")
    
    with tabs[1]:
        st.subheader("User List")
        
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            filter_role = st.selectbox("Filter by Role", ["All", "Admin", "Staff", "Customer"])
        with col2:
            filter_status = st.selectbox("Filter by Status", ["All", "Active", "Inactive"])
        
        # Apply filters
        filtered_users = users.copy()
        if filter_role != "All":
            filtered_users = filtered_users[filtered_users['role'] == filter_role]
        if filter_status != "All":
            filtered_users = filtered_users[filtered_users['status'] == filter_status]
        
        # Display user table
        for _, user in filtered_users.iterrows():
            with st.expander(f"{user['name']} ({user['role']})"):
                with st.form(key=f"edit_{user['user_id']}"):
                    name = st.text_input("Name", value=user['name'])
                    mobile = st.text_input("Mobile", value=user['mobile'])
                    password = st.text_input("Password", value=user['password'], type='password')
                    status = st.selectbox("Status", ["Active", "Inactive"], index=0 if user['status'] == "Active" else 1)
                    credit_limit = st.number_input("Credit Limit", value=user['credit_limit']) if user['role'] == "Customer" else 0
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Update"):
                            users.loc[users['user_id'] == user['user_id'], ['name', 'mobile', 'password', 'status', 'credit_limit']] = [name, mobile, password, status, credit_limit]
                            save_data(users, 'users')
                            st.success("User updated")
                    with col2:
                        if st.button("Delete", key=f"del_{user['user_id']}"):
                            users = users[users['user_id'] != user['user_id']]
                            save_data(users, 'users')
                            st.rerun()

def menu_management():
    st.title("🍽 Menu Management")
    menu = load_data('menu')
    
    tabs = st.tabs(["Add Item", "Manage Menu"])
    
    with tabs[0]:
        with st.form("add_item_form"):
            name = st.text_input("Item Name")
            description = st.text_area("Description")
            price = st.number_input("Price", min_value=0.0, format="%.2f")
            category = st.selectbox("Category", ["Beverage", "Main Course", "Appetizer", "Dessert"])
            
            if st.form_submit_button("Add Item"):
                new_item = pd.DataFrame([{
                    'item_id': f"ITM{datetime.datetime.now().timestamp()}",
                    'name': name,
                    'description': description,
                    'price': price,
                    'category': category
                }])
                
                save_data(pd.concat([menu, new_item], ignore_index=True), 'menu')
                st.success("Menu item added")
    
    with tabs[1]:
        st.subheader("Current Menu")
        for _, item in menu.iterrows():
            with st.expander(item['name']):
                with st.form(key=f"edit_{item['item_id']}"):
                    name = st.text_input("Name", value=item['name'])
                    description = st.text_area("Description", value=item['description'])
                    price = st.number_input("Price", value=item['price'])
                    category = st.selectbox("Category", ["Beverage", "Main Course", "Appetizer", "Dessert"], 
                                          index=["Beverage", "Main Course", "Appetizer", "Dessert"].index(item['category']))
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Update"):
                            menu.loc[menu['item_id'] == item['item_id'], ['name', 'description', 'price', 'category']] = [name, description, price, category]
                            save_data(menu, 'menu')
                            st.success("Item updated")
                    with col2:
                        if st.button("Delete", key=f"del_{item['item_id']}"):
                            menu = menu[menu['item_id'] != item['item_id']]
                            save_data(menu, 'menu')
                            st.rerun()

def inventory_page():
    st.title("📦 Inventory Management")
    inventory = load_data('inventory')
    
    tabs = st.tabs(["Add Item", "Manage Inventory"])
    
    with tabs[0]:
        with st.form("add_inventory_form"):
            item_name = st.text_input("Item Name")
            quantity = st.number_input("Quantity", min_value=0)
            unit = st.selectbox("Unit", ["kg", "g", "L", "ml", "units"])
            
            if st.form_submit_button("Add Inventory Item"):
                new_item = pd.DataFrame([{
                    'item_id': f"INV{datetime.datetime.now().timestamp()}",
                    'item_name': item_name,
                    'quantity': quantity,
                    'unit': unit
                }])
                
                save_data(pd.concat([inventory, new_item], ignore_index=True), 'inventory')
                st.success("Inventory item added")
    
    with tabs[1]:
        st.subheader("Current Inventory")
        for _, item in inventory.iterrows():
            with st.expander(item['item_name']):
                with st.form(key=f"inv_{item['item_id']}"):
                    quantity = st.number_input("Quantity", value=item['quantity'])
                    unit = st.text_input("Unit", value=item['unit'])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Update"):
                            inventory.loc[inventory['item_id'] == item['item_id'], ['quantity', 'unit']] = [quantity, unit]
                            save_data(inventory, 'inventory')
                            st.success("Inventory updated")
                    with col2:
                        if st.button("Delete", key=f"del_inv_{item['item_id']}"):
                            inventory = inventory[inventory['item_id'] != item['item_id']]
                            save_data(inventory, 'inventory')
                            st.rerun()

def reports_page():
    st.title("📊 Sales Reports")
    orders = load_data('orders')
    
    if orders.empty:
        st.warning("No orders available")
        return
    
    # Convert date string to datetime
    orders['date'] = pd.to_datetime(orders['date'])
    
    # Time period selection
    period = st.selectbox("Report Period", ["Daily", "Weekly", "Monthly"])
    
    # Calculate date range based on selection
    end_date = datetime.datetime.now()
    if period == "Daily":
        start_date = end_date - datetime.timedelta(days=1)
    elif period == "Weekly":
        start_date = end_date - datetime.timedelta(weeks=1)
    else:  # Monthly
        start_date = end_date - datetime.timedelta(weeks=4)
    
    # Filter orders
    filtered_orders = orders[(orders['date'] >= start_date) & (orders['date'] <= end_date)]
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Orders", len(filtered_orders))
    col2.metric("Total Revenue", f"₹{filtered_orders['total'].sum():.2f}")
    col3.metric("Average Order Value", f"₹{filtered_orders['total'].mean():.2f}")
    
    # Time series chart
    st.subheader(f"Revenue Trend ({period})")
    if period == "Daily":
        time_group = filtered_orders['date'].dt.hour
    elif period == "Weekly":
        time_group = filtered_orders['date'].dt.day
    else:
        time_group = filtered_orders['date'].dt.week
    
    revenue_data = filtered_orders.groupby(time_group)['total'].sum().reset_index()
    st.bar_chart(revenue_data.set_index(revenue_data.columns[0]))
    
    # Top items
    st.subheader("Top Selling Items")
    all_items = []
    for items in filtered_orders['items']:
        for item in items.split(','):
            item_id, qty = item.split(':')
            all_items.append((item_id, int(qty)))
    
    if all_items:
        items_df = pd.DataFrame(all_items, columns=['item_id', 'quantity'])
        top_items = items_df.groupby('item_id')['quantity'].sum().nlargest(5).reset_index()
        menu = load_data('menu')
        top_items = top_items.merge(menu, on='item_id')
        st.dataframe(top_items[['name', 'quantity']].set_index('name'))

def feedback_page():
    st.title("⭐ Feedback")
    feedback = load_data('feedback')
    
    # Feedback submission
    with st.form("feedback_form"):
        name = st.text_input("Name (Optional)")
        rating = st.slider("Rating", 1, 5, 5)
        fb_type = st.selectbox("Feedback Type", ["General", "Complaint", "Suggestion"])
        comment = st.text_area("Your Feedback")
        
        if st.form_submit_button("Submit Feedback"):
            new_feedback = pd.DataFrame([{
                'feedback_id': f"FB{datetime.datetime.now().timestamp()}",
                'user_id': st.session_state.user_id,
                'name': name,
                'rating': rating,
                'type': fb_type,
                'comment': comment,
                'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }])
            
            save_data(pd.concat([feedback, new_feedback], ignore_index=True), 'feedback')
            st.success("Thank you for your feedback!")
    
    # Display feedback (for Admin/Staff)
    if st.session_state.user_role in ['Admin', 'Staff']:
        st.subheader("All Feedback")
        if feedback.empty:
            st.info("No feedback yet")
        else:
            for _, fb in feedback.iterrows():
                st.write(f"**{fb['name'] or 'Anonymous'}** ({fb['date'].split()[0]})")
                st.write(f"Rating: {'⭐' * int(fb['rating'])}")
                st.write(f"Type: {fb['type']}")
                st.write(fb['comment'])
                st.divider()

def credit_page():
    st.title("💰 Customer Credit Management")
    users = load_data('users')
    customers = users[users['role'] == 'Customer']
    
    if customers.empty:
        st.info("No customers found")
        return
    
    for _, customer in customers.iterrows():
        with st.expander(f"{customer['name']} - ₹{customer['current_balance']:.2f}/{customer['credit_limit']:.2f}"):
            with st.form(key=f"credit_{customer['user_id']}"):
                new_limit = st.number_input("Credit Limit", value=float(customer['credit_limit']))
                adjustment = st.number_input("Balance Adjustment", value=0.0)
                notes = st.text_area("Notes")
                
                if st.form_submit_button("Update"):
                    # Update credit limit
                    users.loc[users['user_id'] == customer['user_id'], 'credit_limit'] = new_limit
                    
                    # Apply balance adjustment
                    if adjustment != 0:
                        users.loc[users['user_id'] == customer['user_id'], 'current_balance'] += adjustment
                        # Record transaction
                        orders = load_data('orders')
                        new_order = pd.DataFrame([{
                            'order_id': f"ADJ{datetime.datetime.now().timestamp()}",
                            'user_id': customer['user_id'],
                            'mobile': customer['mobile'],
                            'items': "Balance Adjustment",
                            'total': abs(adjustment),
                            'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'payment_mode': "Credit" if adjustment > 0 else "Payment",
                            'status': "Adjusted"
                        }])
                        save_data(pd.concat([orders, new_order], ignore_index=True), 'orders')
                    
                    save_data(users, 'users')
                    st.success("Customer credit updated")

# Main app logic
def main():
    # Login page
    if not st.session_state.logged_in:
        st.title("🔐 Chai Chow Corner Login")
        role = st.radio("Select Role", ["Admin", "Staff", "Customer"], horizontal=True)
        
        if role in ["Admin", "Staff"]:
            admin_staff_login()
        else:
            customer_login()
        return
    
    # Main navigation
    pages = {
        "Order": order_page,
        "Feedback": feedback_page
    }
    
    if st.session_state.user_role == "Admin":
        admin_pages = {
            "User Management": user_management,
            "Menu Management": menu_management,
            "Inventory": inventory_page,
            "Reports": reports_page,
            "Customer Credit": credit_page
        }
        pages.update(admin_pages)
    elif st.session_state.user_role == "Staff":
        staff_pages = {
            "Menu Management": menu_management,
            "Inventory": inventory_page
        }
        pages.update(staff_pages)
    
    # Sidebar navigation
    with st.sidebar:
        st.title(f"Welcome, {st.session_state.user_role}")
        st.divider()
        page = option_menu(
            menu_title=None,
            options=list(pages.keys()),
            icons=["🧾", "⭐", "👤", "🍽", "📦", "📊", "💰"][:len(pages)],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"background-color": "#1a1a1a"},
                "nav-link": {"color": "white", "font-size": "14px"},
                "nav-link-selected": {"background-color": "#ff4b4b", "color": "black"}
            }
        )
        
        st.divider()
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user_role = None
            st.session_state.user_id = None
            st.rerun()
    
    # Display selected page
    pages[page]()

if __name__ == "__main__":
    main()
