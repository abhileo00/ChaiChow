# app.py — DailyShop Dairy (single-file)
# Requirements:
#   pip install streamlit pandas fpdf
# Run:
#   streamlit run app.py

import os
import hashlib
from datetime import datetime, date
import pandas as pd
import streamlit as st
from fpdf import FPDF

# -----------------------
# Configuration
# -----------------------
APP_TITLE = "🛒 DailyShop Dairy"
DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.csv")
INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.csv")
EXPENSES_FILE = os.path.join(DATA_DIR, "expenses.csv")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.csv")
PAYMENTS_FILE = os.path.join(DATA_DIR, "payments.csv")

SCHEMA = {
    "users": ["user_id", "name", "role", "mobile", "password_hash"],
    "inventory": ["item_id", "item_name", "category", "unit", "stock_qty", "rate", "min_qty", "sell_price"],
    "expenses": ["date", "type", "category", "item", "item_id", "qty", "rate", "amount", "user_id", "remarks"],
    "orders": ["date", "customer_id", "item_id", "item_name", "qty", "rate", "total", "payment_mode", "balance", "user_id", "remarks"],
    "payments": ["date", "customer_id", "amount", "mode", "remarks", "user_id"],
}

st.set_page_config(page_title=APP_TITLE, layout="wide")

# -----------------------
# Utils (loading/saving, hashing, etc.)
# -----------------------
def safe_make_data_dir():
    if os.path.exists(DATA_DIR) and not os.path.isdir(DATA_DIR):
        try: os.remove(DATA_DIR)
        except: pass
    os.makedirs(DATA_DIR, exist_ok=True)

def new_df(cols): return pd.DataFrame(columns=cols)

def load_csv(path, cols):
    if os.path.exists(path):
        df = pd.read_csv(path, dtype=str, encoding="utf-8", errors="ignore")
        for c in cols:
            if c not in df.columns:
                df[c] = None
        return df[cols]
    return new_df(cols)

def save_csv(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")

def hash_pw(pw): return hashlib.sha256(str(pw).encode("utf-8")).hexdigest()
def check_pw(raw, hashed): return hash_pw(raw) == hashed

def round_to_5(n):
    try:
        return int(5 * round(float(n) / 5.0))
    except:
        return 0

# -----------------------
# Bootstrap default files
# -----------------------
def bootstrap_files():
    safe_make_data_dir()
    if not os.path.exists(USERS_FILE):
        admin = pd.DataFrame([{
            "user_id":"admin", "name":"Master Admin", "role":"admin", "mobile":"9999999999", "password_hash": hash_pw("admin123")
        }], columns=SCHEMA["users"])
        save_csv(admin, USERS_FILE)
    for path, cols in [(INVENTORY_FILE, SCHEMA["inventory"]), (EXPENSES_FILE, SCHEMA["expenses"]),
                       (ORDERS_FILE, SCHEMA["orders"]), (PAYMENTS_FILE, SCHEMA["payments"])]:
        if not os.path.exists(path):
            save_csv(new_df(cols), path)
        else:
            df = load_csv(path, cols)
            save_csv(df, path)

bootstrap_files()

# -----------------------
# Data Manip & Business Logic
# -----------------------
def get_user_by_mobile(mobile):
    users = load_csv(USERS_FILE, SCHEMA["users"])
    row = users[users["mobile"] == str(mobile)]
    return row.iloc[0].to_dict() if not row.empty else None

def create_or_update_user(user_id, name, role, mobile, password):
    users = load_csv(USERS_FILE, SCHEMA["users"])
    exists = users[users["mobile"] == str(mobile)]
    ph = hash_pw(password)
    if exists.empty:
        users.loc[len(users)] = [user_id, name, role, mobile, ph]
    else:
        idx = exists.index[0]
        users.loc[idx, ["name","role","mobile","password_hash"]] = [name, role, mobile, ph]
    save_csv(users, USERS_FILE)

def list_inventory():
    inv = load_csv(INVENTORY_FILE, SCHEMA["inventory"])
    for col in ["stock_qty","rate","min_qty","sell_price"]:
        inv[col] = pd.to_numeric(inv[col], errors="coerce").fillna(0)
    return inv

def adjust_stock(item_id, delta):
    inv = list_inventory()
    row = inv[inv["item_id"] == item_id]
    if row.empty:
        return False, "Item not found"
    idx = row.index[0]
    current = row.at[idx, "stock_qty"]
    new = current + float(delta)
    if new < 0:
        return False, {"current":current, "requested":abs(delta)}
    inv.at[idx, "stock_qty"] = new
    save_csv(inv, INVENTORY_FILE)
    return True, new

def record_order(dt, cust_id, item_id, item_name, qty, rate, payment_mode, user_id, remarks):
    total = round(qty * rate, 2)
    balance = total if payment_mode.lower() == "credit" else 0.0
    df = load_csv(ORDERS_FILE, SCHEMA["orders"])
    df.loc[len(df)] = [dt.isoformat(), cust_id, item_id, item_name, qty, rate, total, payment_mode, balance, user_id, remarks]
    save_csv(df, ORDERS_FILE)
    ok, _ = adjust_stock(item_id, -qty)
    return ok

# (Other functions like record_purchase, record_expense, balances, exports, etc. remain same)

# -----------------------
# Login & App UI
# -----------------------
if "user" not in st.session_state:
    st.session_state.user = None

def login_page():
    st.header(APP_TITLE)
    st.info("Login as admin/staff. Default: 9999999999 / admin123")
    with st.form("login"):
        mobile = st.text_input("Mobile")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            usr = get_user_by_mobile(mobile)
            if usr and check_pw(pw, usr["password_hash"]):
                st.session_state.user = usr
                st.experimental_rerun()
            else:
                st.error("Login failed")

def app_ui():
    user = st.session_state.user
    # Conditional tabs per role
    tabs = []
    if user["role"] == "admin":
        tabs = ["Dashboard","Inventory","Expenses","Menu","Payments","Reports","Users"]
    else:
        tabs = ["Dashboard","Menu"]
    tab_objs = st.tabs(tabs)

    # Dashboard
    with tab_objs[0]:
        st.write("Dashboard here...")

    # Inventory (admin only)
    if user["role"] == "admin":
        with tab_objs[1]:
            st.write("Inventory editor...")

        with tab_objs[-1]:
            st.header("User Management (Admin)")
            usr_df = load_csv(USERS_FILE, SCHEMA["users"])
            edited = st.data_editor(usr_df, use_container_width=True, num_rows="dynamic",
                                     column_config={
                                         "password_hash": st.column_config.TextColumn("Password Hash (encrypted)", disabled=True),
                                         "role": st.column_config.TextColumn("Role"),
                                     })
            if st.button("Save Users"):
                save_csv(edited, USERS_FILE)
                st.success("User table updated")
                st.experimental_rerun()

    # Menu / Booking
    idx = 2 if user["role"]=="admin" else 1
    with tab_objs[idx]:
        st.header("Menu / Booking")
        inv = list_inventory()
        if inv.empty:
            st.info("No items")
        else:
            cats = ["All"] + sorted(inv["category"].unique())
            sel_cat = st.selectbox("Category", cats)
            df = inv if sel_cat=="All" else inv[inv["category"]==sel_cat]
            names = ["Select"] + list(df["item_name"])
            with st.form("booking"):
                cust = st.text_input("Customer mobile (only for Credit)")
                item = st.selectbox("Item", names)
                qty = st.number_input("Qty", min_value=1, step=1, format="%d")
                pm = st.radio("Payment", ["Cash","Credit"])
                price = st.number_input("Price (₹)", min_value=0, step=5, format="%d", value=int(df[df["item_name"]==item]["sell_price"].iloc[0]) if item!="Select" else 0)
                rem = st.text_input("Remarks")
                if st.form_submit_button("Book"):
                    if item=="Select":
                        st.error("Select item")
                    else:
                        if pm=="Credit" and not cust.strip():
                            st.error("Mobile required for credit")
                        else:
                            cust_id = cust.strip() if pm=="Credit" else (cust.strip() or "Guest")
                            ok, det = adjust_stock(df[df["item_name"]==item]["item_id"].iloc[0], -qty)
                            if not ok:
                                st.error(f"Not enough stock. Available: {det['current']}")
                            else:
                                # reverse temp adjust & write
                                adjust_stock(df[df["item_name"]==item]["item_id"].iloc[0], qty)
                                record_order(date.today(), cust_id,
                                             df[df["item_name"]==item]["item_id"].iloc[0], item,
                                             qty, price, pm, user["user_id"], rem)
                                st.success("Booked!")

    # (Payments, Reports tabs implementation omitted for brevity)

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.experimental_rerun()

if st.session_state.user is None:
    login_page()
else:
    app_ui()
