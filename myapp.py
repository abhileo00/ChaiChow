import streamlit as st
import pandas as pd
import os

# ========================
# Utility Functions
# ========================
def load_csv(file, columns, default_data=None):
    """Load CSV or create with default data"""
    if not os.path.exists(file):
        df = pd.DataFrame(default_data if default_data else [], columns=columns)
        df.to_csv(file, index=False)
    df = pd.read_csv(file)
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[columns]

def save_csv(file, df):
    df.to_csv(file, index=False)

# ========================
# Authentication
# ========================
def init_users():
    """Ensure at least one admin user exists"""
    default_admin = [{
        "mobile": "9999999999",
        "password": "admin",
        "role": "admin",
        "active": "yes",
        "tabs": "all"
    }]
    users = load_csv("users.csv", ["mobile", "password", "role", "active", "tabs"], default_admin)
    if users.empty:
        users = pd.DataFrame(default_admin)
        save_csv("users.csv", users)
    return users

def authenticate(mobile, password):
    users = init_users()
    row = users[
        (users["mobile"].astype(str) == str(mobile)) &
        (users["password"] == password) &
        (users["active"].astype(str).str.lower() == "yes")
    ]
    if not row.empty:
        return row.iloc[0].to_dict()
    return None

def require_login():
    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        st.title("DailyShop Dairy - Login")
        mobile = st.text_input("Mobile")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user = authenticate(mobile, password)
            if user:
                st.session_state.user = user
                st.success("Login successful ✅")
                st.rerun()
            else:
                st.error("Invalid credentials or inactive user.")
        st.stop()

# ========================
# Pages
# ========================
def dashboard():
    st.header("📊 Dashboard")
    st.info("Welcome to DailyShop Dairy")

def inventory():
    st.header("📦 Inventory")
    df = load_csv("inventory.csv", ["item", "quantity", "price"])
    st.dataframe(df)
    with st.form("add_inventory"):
        item = st.text_input("Item Name")
        qty = st.number_input("Quantity", min_value=0, step=1)
        price = st.number_input("Price", min_value=0.0, step=0.1)
        if st.form_submit_button("Add Item"):
            df.loc[len(df)] = [item, qty, price]
            save_csv("inventory.csv", df)
            st.success("Item added!")
            st.rerun()

def purchases():
    st.header("🛒 Purchases")
    df = load_csv("purchases.csv", ["date", "item", "quantity", "amount"])
    st.dataframe(df)
    with st.form("add_purchase"):
        date = st.date_input("Date")
        item = st.text_input("Item")
        qty = st.number_input("Quantity", min_value=0, step=1)
        amt = st.number_input("Amount", min_value=0.0, step=0.1)
        if st.form_submit_button("Add Purchase"):
            df.loc[len(df)] = [str(date), item, qty, amt]
            save_csv("purchases.csv", df)
            st.success("Purchase added!")
            st.rerun()

def sales():
    st.header("🧾 Sales")
    df = load_csv("sales.csv", ["date", "item", "quantity", "amount", "customer"])
    st.dataframe(df)
    with st.form("add_sale"):
        date = st.date_input("Date")
        item = st.text_input("Item")
        qty = st.number_input("Quantity", min_value=0, step=1)
        amt = st.number_input("Amount", min_value=0.0, step=0.1)
        customer = st.text_input("Customer")
        if st.form_submit_button("Add Sale"):
            df.loc[len(df)] = [str(date), item, qty, amt, customer]
            save_csv("sales.csv", df)
            st.success("Sale added!")
            st.rerun()

def expenses():
    st.header("💰 Expenses")
    df = load_csv("expenses.csv", ["date", "category", "amount", "note"])
    st.dataframe(df)
    with st.form("add_expense"):
        date = st.date_input("Date")
        cat = st.text_input("Category")
        amt = st.number_input("Amount", min_value=0.0, step=0.1)
        note = st.text_input("Note")
        if st.form_submit_button("Add Expense"):
            df.loc[len(df)] = [str(date), cat, amt, note]
            save_csv("expenses.csv", df)
            st.success("Expense added!")
            st.rerun()

def payments():
    st.header("💳 Payments")
    df = load_csv("payments.csv", ["date", "customer", "amount", "mode"])
    st.dataframe(df)
    with st.form("add_payment"):
        date = st.date_input("Date")
        cust = st.text_input("Customer")
        amt = st.number_input("Amount", min_value=0.0, step=0.1)
        mode = st.selectbox("Mode", ["Cash", "Card", "UPI"])
        if st.form_submit_button("Add Payment"):
            df.loc[len(df)] = [str(date), cust, amt, mode]
            save_csv("payments.csv", df)
            st.success("Payment recorded!")
            st.rerun()

def reports():
    st.header("📑 Reports")
    sales = load_csv("sales.csv", ["date", "item", "quantity", "amount", "customer"])
    st.subheader("Total Sales")
    st.write(f"₹ {sales['amount'].sum():,.2f}")
    st.subheader("Sales Records")
    st.dataframe(sales)

def user_mgmt():
    st.header("👥 User Management (Admin Only)")
    df = init_users()
    st.dataframe(df)
    with st.form("add_user"):
        mobile = st.text_input("Mobile")
        pwd = st.text_input("Password")
        role = st.selectbox("Role", ["admin", "staff", "customer"])
        active = st.selectbox("Active", ["yes", "no"])
        if st.form_submit_button("Add User"):
            df.loc[len(df)] = [mobile, pwd, role, active, "all"]
            save_csv("users.csv", df)
            st.success("User added!")
            st.rerun()

# ========================
# Main App
# ========================
def main():
    require_login()
    role = str(st.session_state.user.get("role", "")).strip().lower()

    # ✅ Role-based tabs
    if role == "admin":
        tabs = ["Dashboard", "Inventory", "Purchases", "Sales", "Expenses", "Payments", "Reports", "Users"]
    elif role == "staff":
        tabs = ["Dashboard", "Inventory", "Purchases", "Sales", "Expenses", "Payments", "Reports"]
    elif role == "customer":
        tabs = ["Dashboard", "Sales", "Payments"]
    else:
        tabs = ["Dashboard"]

    # ✅ Top tabs navigation
    tab_objects = st.tabs(tabs)

    for i, t in enumerate(tabs):
        with tab_objects[i]:
            if t == "Dashboard":
                dashboard()
            elif t == "Inventory":
                inventory()
            elif t == "Purchases":
                purchases()
            elif t == "Sales":
                sales()
            elif t == "Expenses":
                expenses()
            elif t == "Payments":
                payments()
            elif t == "Reports":
                reports()
            elif t == "Users":
                user_mgmt()

if __name__ == "__main__":
    main()
