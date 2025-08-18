import streamlit as st
import pandas as pd
import hashlib
import os
from datetime import datetime

# ------------------------
# File paths
# ------------------------
DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.csv")
INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.csv")
EXPENSES_FILE = os.path.join(DATA_DIR, "expenses.csv")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.csv")
PAYMENTS_FILE = os.path.join(DATA_DIR, "payments.csv")

# ------------------------
# Utility functions
# ------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def ensure_data_files():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(USERS_FILE):
        df = pd.DataFrame(columns=["user_id", "name", "role", "mobile", "password_hash"])
        df.to_csv(USERS_FILE, index=False)

    if not os.path.exists(INVENTORY_FILE):
        df = pd.DataFrame(columns=["item_id", "item_name", "category", "unit", "stock_qty", "rate", "min_qty"])
        df.to_csv(INVENTORY_FILE, index=False)

    if not os.path.exists(EXPENSES_FILE):
        df = pd.DataFrame(columns=["date", "category", "item", "amount", "user_id"])
        df.to_csv(EXPENSES_FILE, index=False)

    if not os.path.exists(ORDERS_FILE):
        df = pd.DataFrame(columns=["date", "customer_id", "item_id", "qty", "rate", "total", "payment_mode", "balance"])
        df.to_csv(ORDERS_FILE, index=False)

    if not os.path.exists(PAYMENTS_FILE):
        df = pd.DataFrame(columns=["date", "customer_id", "amount", "mode", "remarks"])
        df.to_csv(PAYMENTS_FILE, index=False)

def ensure_default_admin():
    ensure_data_files()
    df = pd.read_csv(USERS_FILE)
    if df.empty or "9999999999" not in df["mobile"].astype(str).values:
        admin_user = {
            "user_id": len(df) + 1,
            "name": "Admin",
            "role": "admin",
            "mobile": "9999999999",
            "password_hash": hash_password("admin123")
        }
        df = pd.concat([df, pd.DataFrame([admin_user])], ignore_index=True)
        df.to_csv(USERS_FILE, index=False)

# ------------------------
# Authentication
# ------------------------
def login_user(mobile, password):
    df = pd.read_csv(USERS_FILE)
    user = df[df["mobile"].astype(str) == str(mobile)]
    if not user.empty:
        if user.iloc[0]["password_hash"] == hash_password(password):
            return user.iloc[0].to_dict()
    return None

# ------------------------
# Pages
# ------------------------
def page_inventory(user):
    st.header("📦 Manage Inventory")
    df = pd.read_csv(INVENTORY_FILE)

    with st.form("add_item"):
        item_name = st.text_input("Item Name")
        category = st.text_input("Category")
        unit = st.text_input("Unit (e.g. kg, pcs)")
        stock_qty = st.number_input("Stock Quantity", min_value=0, value=0)
        rate = st.number_input("Rate", min_value=0.0, value=0.0)
        min_qty = st.number_input("Minimum Qty Alert", min_value=0, value=0)
        submitted = st.form_submit_button("Add Item")
        if submitted and item_name:
            new_item = {
                "item_id": len(df) + 1,
                "item_name": item_name,
                "category": category,
                "unit": unit,
                "stock_qty": stock_qty,
                "rate": rate,
                "min_qty": min_qty
            }
            df = pd.concat([df, pd.DataFrame([new_item])], ignore_index=True)
            df.to_csv(INVENTORY_FILE, index=False)
            st.success("✅ Item added!")

    st.subheader("Current Inventory")
    st.dataframe(df)

def page_expenses(user):
    st.header("💰 Track Expenses")
    df = pd.read_csv(EXPENSES_FILE)

    with st.form("add_expense"):
        category = st.text_input("Category")
        item = st.text_input("Expense Item")
        amount = st.number_input("Amount", min_value=0.0, value=0.0)
        submitted = st.form_submit_button("Add Expense")
        if submitted and item:
            new_expense = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "category": category,
                "item": item,
                "amount": amount,
                "user_id": user["user_id"]
            }
            df = pd.concat([df, pd.DataFrame([new_expense])], ignore_index=True)
            df.to_csv(EXPENSES_FILE, index=False)
            st.success("✅ Expense recorded!")

    st.subheader("Expense Records")
    st.dataframe(df)

def page_orders(user):
    st.header("🛒 Manage Orders")
    df_orders = pd.read_csv(ORDERS_FILE)
    df_inventory = pd.read_csv(INVENTORY_FILE)

    if df_inventory.empty:
        st.warning("⚠️ No items in inventory. Please add items first.")
        return

    with st.form("add_order"):
        customer_id = st.text_input("Customer Mobile")
        item = st.selectbox("Item", df_inventory["item_name"].tolist())
        qty = st.number_input("Quantity", min_value=1, value=1)
        payment_mode = st.selectbox("Payment Mode", ["Cash", "Credit", "UPI", "Card"])
        submitted = st.form_submit_button("Add Order")
        if submitted and customer_id:
            item_row = df_inventory[df_inventory["item_name"] == item].iloc[0]
            rate = float(item_row["rate"])
            total = qty * rate
            balance = 0 if payment_mode != "Credit" else total

            new_order = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "customer_id": customer_id,
                "item_id": item_row["item_id"],
                "qty": qty,
                "rate": rate,
                "total": total,
                "payment_mode": payment_mode,
                "balance": balance
            }
            df_orders = pd.concat([df_orders, pd.DataFrame([new_order])], ignore_index=True)
            df_orders.to_csv(ORDERS_FILE, index=False)
            st.success("✅ Order added!")

    st.subheader("Order Records")
    st.dataframe(df_orders)

def page_reports(user):
    st.header("📊 Reports")

    orders = pd.read_csv(ORDERS_FILE)
    expenses = pd.read_csv(EXPENSES_FILE)

    if not orders.empty:
        st.subheader("Sales Summary")
        st.write("💵 Total Sales:", orders["total"].sum())
        st.write("🧾 Pending Credit:", orders["balance"].sum())

    if not expenses.empty:
        st.subheader("Expense Summary")
        st.write("💸 Total Expenses:", expenses["amount"].sum())

# ------------------------
# Main App
# ------------------------
def main():
    st.set_page_config(page_title="Smart Shop Manager", layout="wide")
    st.markdown("<h2 style='text-align:center;'>🛍️ Smart Shop Manager</h2>", unsafe_allow_html=True)

    ensure_default_admin()

    if "user" not in st.session_state:
        # Login page
        st.subheader("🔑 Login")
        mobile = st.text_input("📱 Mobile Number")
        password = st.text_input("🔒 Password", type="password")
        if st.button("Login"):
            user = login_user(mobile, password)
            if user:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error("❌ Invalid mobile or password")
        st.info("Tip: default admin → mobile: **9999999999** / password: **admin123**")
    else:
        user = st.session_state["user"]
        st.sidebar.success(f"👋 Welcome {user['name']} ({user['role']})")
        tab = st.tabs(["📦 Inventory", "💰 Expenses", "🛒 Orders", "📊 Reports"])
        
        with tab[0]:
            page_inventory(user)
        with tab[1]:
            page_expenses(user)
        with tab[2]:
            page_orders(user)
        with tab[3]:
            page_reports(user)

        if st.sidebar.button("🚪 Logout"):
            st.session_state.pop("user")
            st.rerun()

if __name__ == "__main__":
    main()
