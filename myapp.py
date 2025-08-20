import os
import hashlib
import uuid
import pandas as pd
import streamlit as st
from datetime import datetime

# ------------------------
# File & Folder Setup
# ------------------------
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

TABLES = {
    "users.csv": ["user_id","name","mobile","password","role","tab","active"],
    "inventory.csv": ["item_id","item_name","Area","category","unit","stock_qty","rate","min_qty","sell_price"],
    "purchases.csv": ["purchase_id","date","item_id","item_name","category","unit","qty","rate","total","remarks"],
    "expenses.csv": ["expense_id","date","category","item","amount","remarks"],
    "orders.csv": ["order_id","date","customer_name","mobile","item_id","item_name","category","qty","price","total","payment_mode","status"],
    "payments.csv": ["payment_id","date","customer_name","mobile","amount","remarks"]
}

for fname, cols in TABLES.items():
    path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(path):
        df = pd.DataFrame(columns=cols)
        # add default admin user
        if fname == "users.csv":
            df = pd.DataFrame([{
                "user_id": "U001",
                "name": "Admin",
                "mobile": "9999",
                "password": "admin",
                "role": "admin",
                "tab": "all",
                "active": "Yes"
            }], columns=cols)
        df.to_csv(path, index=False)

# ------------------------
# Utility Functions
# ------------------------
def load_csv(name):
    path = os.path.join(DATA_DIR, name)
    df = pd.read_csv(path)
    expected = TABLES[name]
    for c in expected:
        if c not in df.columns:
            df[c] = ""
    return df[expected]

def save_csv(name, df):
    df.to_csv(os.path.join(DATA_DIR, name), index=False)

def gen_id(prefix=""):
    return prefix + str(uuid.uuid4())[:8]

def hash_id(text):
    return hashlib.md5(text.encode()).hexdigest()[:10]

# ------------------------
# Authentication
# ------------------------
def authenticate(mobile, password):
    users = load_csv("users.csv")
    row = users[(users["mobile"].astype(str) == str(mobile)) &
                (users["password"] == password) &
                (users["active"].str.lower() == "yes")]
    if not row.empty:
        return row.iloc[0].to_dict()
    return None

def require_login():
    if "user" not in st.session_state:
        st.title("DailyShop Dairy - Login")
        mobile = st.text_input("Mobile")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user = authenticate(mobile, password)
            if user:
                st.session_state.user = user
                st.session_state.last_tab = "Dashboard"
                st.rerun()
            else:
                st.error("Invalid credentials or inactive user.")
        st.stop()

# ------------------------
# Tabs
# ------------------------
def dashboard():
    st.header("📊 Dashboard")
    st.success(f"Welcome {st.session_state.user['name']} ({st.session_state.user['role']})")

def inventory():
    st.header("📦 Inventory")
    df = load_csv("inventory.csv")
    edited = st.data_editor(df, num_rows="dynamic")
    if st.button("Save Inventory"):
        save_csv("inventory.csv", edited)
        st.success("Inventory saved.")
        st.rerun()

def purchases():
    st.header("🛒 Purchases")
    df = load_csv("purchases.csv")
    edited = st.data_editor(df, num_rows="dynamic")
    if st.button("Save Purchases"):
        save_csv("purchases.csv", edited)
        st.success("Purchases saved.")
        st.rerun()

def sales():
    st.header("🧾 Sales / Orders")
    df = load_csv("orders.csv")
    edited = st.data_editor(df, num_rows="dynamic")
    if st.button("Save Orders"):
        save_csv("orders.csv", edited)
        st.success("Orders saved.")
        st.rerun()

def expenses():
    st.header("💰 Expenses")
    df = load_csv("expenses.csv")
    edited = st.data_editor(df, num_rows="dynamic")
    if st.button("Save Expenses"):
        save_csv("expenses.csv", edited)
        st.success("Expenses saved.")
        st.rerun()

def payments():
    st.header("💵 Payments")
    df = load_csv("payments.csv")
    edited = st.data_editor(df, num_rows="dynamic")
    if st.button("Save Payments"):
        save_csv("payments.csv", edited)
        st.success("Payments saved.")
        st.rerun()

def reports():
    st.header("📑 Reports")
    sales_df = load_csv("orders.csv")
    expenses_df = load_csv("expenses.csv")
    payments_df = load_csv("payments.csv")
    st.subheader("Summary")
    st.write("Total Sales:", sales_df["total"].astype(float).sum() if not sales_df.empty else 0)
    st.write("Total Expenses:", expenses_df["amount"].astype(float).sum() if not expenses_df.empty else 0)
    st.write("Total Payments:", payments_df["amount"].astype(float).sum() if not payments_df.empty else 0)

def user_mgmt():
    st.header("👥 User Management (Admin Only)")
    if st.session_state.user["role"].lower() != "admin":
        st.error("Access denied.")
        return
    df = load_csv("users.csv")
    edited = st.data_editor(df, num_rows="dynamic")
    if st.button("Save Users"):
        save_csv("users.csv", edited)
        st.success("Users updated.")
        st.rerun()

# ------------------------
# Main
# ------------------------
def main():
    require_login()

    role = str(st.session_state.user.get("role", "")).strip().lower()

    if role == "admin":
        tabs = ["Dashboard","Inventory","Purchases","Sales","Expenses","Payments","Reports","Users"]
    elif role == "staff":
        tabs = ["Dashboard","Inventory","Purchases","Sales","Expenses","Payments","Reports"]
    elif role == "customer":
        tabs = ["Dashboard","Sales","Payments"]
    else:
        tabs = ["Dashboard"]  # fallback safe tab

    if "last_tab" not in st.session_state or st.session_state.last_tab not in tabs:
        st.session_state.last_tab = tabs[0]

    tab = st.sidebar.radio("Navigation", tabs, index=tabs.index(st.session_state.last_tab))
    st.session_state.last_tab = tab

    if tab == "Dashboard": dashboard()
    elif tab == "Inventory": inventory()
    elif tab == "Purchases": purchases()
    elif tab == "Sales": sales()
    elif tab == "Expenses": expenses()
    elif tab == "Payments": payments()
    elif tab == "Reports": reports()
    elif tab == "Users": user_mgmt()

    if role == "admin" and st.sidebar.button("Reset App"):
        st.session_state.clear()
        st.rerun()

if __name__ == "__main__":
    main()
