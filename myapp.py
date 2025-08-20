import streamlit as st
import pandas as pd
import os

# ========================
# Utility functions
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
    st.write("Manage inventory here.")

def purchases():
    st.header("🛒 Purchases")
    st.write("Manage purchases here.")

def sales():
    st.header("🧾 Sales")
    st.write("Manage sales/orders here.")

def expenses():
    st.header("💰 Expenses")
    st.write("Track expenses here.")

def payments():
    st.header("💳 Payments")
    st.write("Track payments here.")

def reports():
    st.header("📑 Reports")
    st.write("Generate daily/weekly/monthly reports here.")

def user_mgmt():
    st.header("👥 User Management")
    st.write("Admin can manage users here.")

# ========================
# Main App
# ========================
def main():
    require_login()
    role = str(st.session_state.user.get("role", "")).strip().lower()

    # ✅ Admin gets all tabs
    if role == "admin":
        tabs = ["Dashboard", "Inventory", "Purchases", "Sales", "Expenses", "Payments", "Reports", "Users"]
    elif role == "staff":
        tabs = ["Dashboard", "Inventory", "Purchases", "Sales", "Expenses", "Payments", "Reports"]
    elif role == "customer":
        tabs = ["Dashboard", "Sales", "Payments"]
    else:
        tabs = ["Dashboard"]

    # ✅ Show top navigation tabs
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
