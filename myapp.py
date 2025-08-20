import streamlit as st
import pandas as pd
import os
import uuid
from datetime import datetime

# ========================
# Config
# ========================
st.set_page_config(page_title="DailyShop Dairy", layout="wide")
DATA_DIR = "data"

# ========================
# Table structures
# ========================
TABLES = {
    "users.csv": ["user_id", "name", "mobile", "password", "role", "tab", "active"],
    "inventory.csv": ["item_id", "item_name", "unit", "quantity", "price"],
    "purchases.csv": ["purchase_id", "date", "vendor", "item_id", "qty", "rate", "total"],
    "sales.csv": ["order_id", "date", "customer", "item_id", "qty", "rate", "total", "payment_mode"],
    "expenses.csv": ["expense_id", "date", "description", "amount"],
    "payments.csv": ["payment_id", "date", "customer", "amount", "mode"],
}

os.makedirs(DATA_DIR, exist_ok=True)

# ========================
# Helpers
# ========================
def gen_id(prefix="id"):
    return f"{prefix}_{uuid.uuid4().hex[:6]}"

def load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        pd.DataFrame(columns=TABLES[filename]).to_csv(path, index=False)
    df = pd.read_csv(path)
    return df

def save_csv(filename, df):
    path = os.path.join(DATA_DIR, filename)
    df.to_csv(path, index=False)

# ========================
# Ensure CSVs + default admin
# ========================
for fname in TABLES:
    load_csv(fname)

users_df = load_csv("users.csv")
if users_df.empty:
    default_admin = pd.DataFrame([{
        "user_id": gen_id("u"),
        "name": "Admin",
        "mobile": "9999999999",
        "password": "admin123",
        "role": "admin",
        "tab": "all",
        "active": "Yes"
    }])
    save_csv("users.csv", pd.concat([users_df, default_admin], ignore_index=True))

# ========================
# Authentication
# ========================
def authenticate(mobile, password):
    users = load_csv("users.csv")
    row = users[
        (users["mobile"].astype(str) == str(mobile)) &
        (users["password"].astype(str) == str(password)) &
        (users["active"].astype(str).str.lower() == "yes")
    ]
    return row.iloc[0].to_dict() if not row.empty else None

def require_login():
    if "user" not in st.session_state:
        st.title("DailyShop Dairy - Login")
        mobile = st.text_input("Mobile")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user = authenticate(mobile, password)
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid credentials or inactive user.")
        st.stop()

# ========================
# Modules
# ========================
def dashboard():
    st.subheader("📊 Dashboard")
    st.info("Welcome to DailyShop Dairy")

def inventory():
    st.subheader("📦 Inventory")
    df = load_csv("inventory.csv")
    edited = st.data_editor(df, num_rows="dynamic", key="inv_edit")
    if st.button("Save Inventory"):
        save_csv("inventory.csv", edited)
        st.success("Inventory saved")

def purchases():
    st.subheader("🛒 Purchases")
    df = load_csv("purchases.csv")
    edited = st.data_editor(df, num_rows="dynamic", key="pur_edit")
    if st.button("Save Purchases"):
        save_csv("purchases.csv", edited)
        st.success("Purchases saved")

def sales():
    st.subheader("🧾 Sales / Orders")
    df = load_csv("sales.csv")
    edited = st.data_editor(df, num_rows="dynamic", key="sales_edit")
    if st.button("Save Sales"):
        save_csv("sales.csv", edited)
        st.success("Sales saved")

def expenses():
    st.subheader("💸 Expenses")
    df = load_csv("expenses.csv")
    edited = st.data_editor(df, num_rows="dynamic", key="exp_edit")
    if st.button("Save Expenses"):
        save_csv("expenses.csv", edited)
        st.success("Expenses saved")

def payments():
    st.subheader("💰 Payments")
    df = load_csv("payments.csv")
    edited = st.data_editor(df, num_rows="dynamic", key="pay_edit")
    if st.button("Save Payments"):
        save_csv("payments.csv", edited)
        st.success("Payments saved")

def reports():
    st.subheader("📑 Reports")
    sales = load_csv("sales.csv")
    if sales.empty:
        st.warning("No sales records.")
    else:
        sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
        daily = sales.groupby(sales["date"].dt.date)["total"].sum().reset_index()
        st.write("### Daily Sales")
        st.dataframe(daily)

def user_mgmt():
    st.subheader("👥 User Management")
    df = load_csv("users.csv")
    edited = st.data_editor(df, num_rows="dynamic", key="users_edit")
    if st.button("Save Users"):
        save_csv("users.csv", edited)
        st.success("Users saved")

# ========================
# Main App
# ========================
def main():
    require_login()
    role = str(st.session_state.user.get("role", "")).strip().lower()

    # ✅ Admin has all tabs
    if role == "admin":
        tabs = ["Dashboard", "Inventory", "Purchases", "Sales", "Expenses", "Payments", "Reports", "Users"]
    elif role == "staff":
        tabs = ["Dashboard", "Inventory", "Purchases", "Sales", "Expenses", "Payments", "Reports"]
    elif role == "customer":
        tabs = ["Dashboard", "Sales", "Payments"]
    else:
        tabs = ["Dashboard"]

    # ✅ Top navigation tabs
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
