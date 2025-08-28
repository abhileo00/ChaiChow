import streamlit as st
import pandas as pd
import hashlib
import os
import uuid
from datetime import datetime
from fpdf import FPDF

# =============================
# CONFIGURATION
# =============================
MASTER_ADMIN_ID = "root@admin"
MASTER_ADMIN_PASS = "root123"  # (will be hashed on first run)

# File paths
USERS_FILE = "users.csv"
MENU_FILE = "menu.csv"
ORDERS_FILE = "orders.csv"
CUSTOMERS_FILE = "customers.csv"
EXPENSES_FILE = "expenses.csv"

# =============================
# UTILS
# =============================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def init_files():
    if not os.path.exists(USERS_FILE):
        df = pd.DataFrame(columns=["username", "password", "role"])
        df.loc[len(df)] = [MASTER_ADMIN_ID, hash_password(MASTER_ADMIN_PASS), "MasterAdmin"]
        df.to_csv(USERS_FILE, index=False)
    if not os.path.exists(MENU_FILE):
        pd.DataFrame(columns=["ItemID", "Name", "Category", "Unit", "Stock", "CostPrice", "SellingPrice", "MinQty"]).to_csv(MENU_FILE, index=False)
    if not os.path.exists(ORDERS_FILE):
        pd.DataFrame(columns=["OrderID", "Customer", "Mobile", "Items", "Total", "PaymentMode", "Timestamp"]).to_csv(ORDERS_FILE, index=False)
    if not os.path.exists(CUSTOMERS_FILE):
        pd.DataFrame(columns=["Name", "Mobile", "Email", "CreditBalance"]).to_csv(CUSTOMERS_FILE, index=False)
    if not os.path.exists(EXPENSES_FILE):
        pd.DataFrame(columns=["Date", "Category", "Amount", "Notes"]).to_csv(EXPENSES_FILE, index=False)

init_files()

# =============================
# AUTHENTICATION
# =============================
def login(username, password):
    users = pd.read_csv(USERS_FILE)
    user = users[users["username"] == username]
    if not user.empty:
        if check_password(password, user.iloc[0]["password"]):
            return user.iloc[0]["role"]
    return None

# =============================
# APP
# =============================
st.set_page_config(page_title="Restaurant & Café Management", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None

if not st.session_state.logged_in:
    st.title("🍽️ Restaurant & Café Management App")
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        role = login(username, password)
        if role:
            st.session_state.logged_in = True
            st.session_state.role = role
            st.session_state.username = username
            st.success(f"Welcome {username} ({role})")
        else:
            st.error("Invalid credentials")
else:
    st.sidebar.title("Navigation")
    role = st.session_state.role

    tabs = []
    if role in ["MasterAdmin", "Admin"]:
        tabs = ["Dashboard", "Menu & Inventory", "Orders", "Customers", "Expenses", "Reports", "User Management"]
    elif role == "Manager":
        tabs = ["Dashboard", "Orders", "Reports"]
    elif role == "Cashier":
        tabs = ["Orders", "Customers"]
    elif role == "Waiter":
        tabs = ["Orders"]
    else:
        tabs = ["Orders"]

    choice = st.sidebar.radio("Go to", tabs)

    # DASHBOARD
    if choice == "Dashboard":
        st.title("📊 Dashboard")
        orders = pd.read_csv(ORDERS_FILE)
        customers = pd.read_csv(CUSTOMERS_FILE)
        if not orders.empty:
            st.metric("Total Sales", orders["Total"].astype(float).sum())
            st.metric("Orders Today", len(orders[orders["Timestamp"].str.startswith(datetime.now().strftime("%Y-%m-%d"))]))
        st.metric("Customers", len(customers))

    # MENU & INVENTORY
    elif choice == "Menu & Inventory":
        st.title("📋 Menu & Inventory")
        df = pd.read_csv(MENU_FILE)
        st.dataframe(df)
        with st.expander("Add New Item"):
            name = st.text_input("Name")
            cat = st.selectbox("Category", ["Drinks", "Snacks", "Meals", "Desserts", "Menu"])
            unit = st.text_input("Unit")
            stock = st.number_input("Stock", min_value=0)
            cp = st.number_input("Cost Price", min_value=0.0)
            sp = st.number_input("Selling Price", min_value=0.0)
            minq = st.number_input("Min Qty Alert", min_value=0)
            if st.button("Save Item"):
                item_id = str(uuid.uuid4())[:8]
                new_row = pd.DataFrame([[item_id, name, cat, unit, stock, cp, sp, minq]],
                                       columns=df.columns)
                df = pd.concat([df, new_row], ignore_index=True)
                df.to_csv(MENU_FILE, index=False)
                st.success("Item Added!")
                st.experimental_rerun()

    # ORDERS
    elif choice == "Orders":
        st.title("🛒 Place Order")
        menu = pd.read_csv(MENU_FILE)
        customers = pd.read_csv(CUSTOMERS_FILE)
        if menu.empty:
            st.warning("Menu is empty")
        else:
            cart = []
            category = st.selectbox("Category", menu["Category"].unique())
            items = menu[menu["Category"] == category]
            item = st.selectbox("Item", items["Name"].tolist())
            qty = st.number_input("Quantity", 1, 50)
            if st.button("Add to Cart"):
                cart.append((item, qty))
            if cart:
                st.write(cart)

    # CUSTOMERS
    elif choice == "Customers":
        st.title("👥 Customers")
        df = pd.read_csv(CUSTOMERS_FILE)
        st.dataframe(df)

    # EXPENSES
    elif choice == "Expenses":
        st.title("💰 Expenses")
        df = pd.read_csv(EXPENSES_FILE)
        st.dataframe(df)

    # REPORTS
    elif choice == "Reports":
        st.title("📑 Reports")
        orders = pd.read_csv(ORDERS_FILE)
        if not orders.empty:
            st.dataframe(orders)

    # USER MANAGEMENT
    elif choice == "User Management":
        st.title("👤 User Management")
        users = pd.read_csv(USERS_FILE)
        st.dataframe(users)
        if st.session_state.role == "MasterAdmin":
            with st.expander("Add User"):
                uname = st.text_input("Username")
                pwd = st.text_input("Password", type="password")
                role = st.selectbox("Role", ["Admin", "Manager", "Cashier", "Waiter"])
                if st.button("Create User"):
                    new_row = pd.DataFrame([[uname, hash_password(pwd), role]], columns=users.columns)
                    users = pd.concat([users, new_row], ignore_index=True)
                    users.to_csv(USERS_FILE, index=False)
                    st.success("User Created!")

    st.sidebar.button("Logout", on_click=lambda: st.session_state.update({"logged_in": False}))
