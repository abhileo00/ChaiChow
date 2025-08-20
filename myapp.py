# app.py — DailyShop Dairy (single file)
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

ALLOW_ALL_TABS_FOR_NON_ADMIN = True

SCHEMA = {
    "users": ["user_id", "name", "role", "mobile", "password_hash"],
    "inventory": ["item_id", "item_name", "category", "unit", "stock_qty", "rate", "min_qty", "sell_price"],
    "expenses": ["date", "type", "category", "item", "item_id", "qty", "rate", "amount", "user_id", "remarks"],
    "orders": ["date", "customer_id", "item_id", "item_name", "qty", "rate", "total", "payment_mode", "balance", "user_id", "remarks"],
    "payments": ["date", "customer_id", "amount", "mode", "remarks", "user_id"],
}

st.set_page_config(page_title=APP_TITLE, layout="wide")

# -----------------------
# Utilities
# -----------------------
def safe_make_data_dir():
    if os.path.exists(DATA_DIR) and not os.path.isdir(DATA_DIR):
        try: os.remove(DATA_DIR)
        except: pass
    os.makedirs(DATA_DIR, exist_ok=True)

def new_df(cols): return pd.DataFrame(columns=cols)

def load_csv(path, cols):
    if os.path.exists(path):
        try: df = pd.read_csv(path, dtype=str, encoding="utf-8")
        except: df = pd.read_csv(path, dtype=str, encoding="latin1")
        for c in cols:
            if c not in df.columns: df[c] = None
        return df[cols]
    return new_df(cols)

def save_csv(df, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")

def hash_pw(pw): return hashlib.sha256(pw.encode("utf-8")).hexdigest()
def check_pw(raw, hashed): return hash_pw(raw) == hashed

def round_to_5(n):
    try: return int(5 * round(float(n) / 5.0))
    except: return 0

# -----------------------
# Bootstrap files & admin
# -----------------------
def bootstrap_files():
    safe_make_data_dir()
    if not os.path.exists(USERS_FILE):
        admin = pd.DataFrame([{
            "user_id": "admin", "name": "Master Admin",
            "role": "admin", "mobile": "9999999999",
            "password_hash": hash_pw("admin123")
        }], columns=SCHEMA["users"])
        save_csv(admin, USERS_FILE)
    else:
        save_csv(load_csv(USERS_FILE, SCHEMA["users"]), USERS_FILE)

    for path, cols in [
        (INVENTORY_FILE, SCHEMA["inventory"]),
        (EXPENSES_FILE, SCHEMA["expenses"]),
        (ORDERS_FILE, SCHEMA["orders"]),
        (PAYMENTS_FILE, SCHEMA["payments"]),
    ]:
        if not os.path.exists(path):
            save_csv(new_df(cols), path)
        else:
            save_csv(load_csv(path, cols), path)

bootstrap_files()

# -----------------------
# Business logic
# -----------------------
def get_user_by_mobile(m): ...
def create_or_update_user(...): ...
def list_inventory(): ...
def upsert_inventory(...): ...
def adjust_stock(...): ...
def record_expense(...): ...
def record_purchase(...): ...
def record_order(...): ...
def record_payment(...): ...
def compute_customer_balances(): ...

# -----------------------
# Exports (CSV/PDF)
# -----------------------
def csv_download(...): ...
def make_pdf_bytes(...): ...

# -----------------------
# UI / Pages
# -----------------------
if "user" not in st.session_state:
    st.session_state.user = None

def login_page():
    st.markdown(f"<h2 style='text-align:center;color:#2563EB'>{APP_TITLE}</h2>", unsafe_allow_html=True)
    st.write("Login (default admin: mobile=9999999999, pw=admin123).")
    with st.form("login_form"):
        mobile = st.text_input("Mobile")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            u = get_user_by_mobile(mobile)
            if u and check_pw(pw, u["password_hash"]):
                st.session_state.user = u
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials.")

def app_ui():
    user = st.session_state.user
    colL, colR = st.columns([0.75, 0.25])
    with colL: st.markdown(f"<h3>{APP_TITLE}</h3>", unsafe_allow_html=True)
    with colR:
        st.markdown(f"**{user['name']}** · {user['role']}", unsafe_allow_html=True)
        if st.button("Logout"):
            st.session_state.user = None
            st.rerun()

    tabs = ["Dashboard", "Inventory", "Expenses", "Menu/Booking", "Payments", "Reports"]
    if user["role"] == "admin" or ALLOW_ALL_TABS_FOR_NON_ADMIN:
        tabs.append("Users")
    tab_objs = st.tabs(tabs)

    # Dashboard Tab
    with tab_objs[0]:
        st.header("Dashboard")
        inv = list_inventory()
        exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
        orders = load_csv(ORDERS_FILE, SCHEMA["orders"])
        payments = load_csv(PAYMENTS_FILE, SCHEMA["payments"])

        total_exp = exp["amount"].astype(float).sum() if not exp.empty else 0.0
        total_sales = orders["total"].astype(float).sum() if not orders.empty else 0.0
        stock_val = (inv["stock_qty"] * inv["rate"]).sum() if not inv.empty else 0.0
        balances = compute_customer_balances()
        pending_total = balances["pending_balance"].sum() if not balances.empty else 0.0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Expenses", f"₹{total_exp:,.2f}")
        c2.metric("Total Sales", f"₹{total_sales:,.2f}")
        c3.metric("Stock Value", f"₹{stock_val:,.2f}")
        c4.metric("Pending Balance", f"₹{pending_total:,.2f}")

        low = inv[inv["stock_qty"] < inv["min_qty"]]
        st.subheader("Low Stock Alerts")
        if low.empty:
            st.info("All items are sufficiently stocked.")
        else:
            for _, r in low.iterrows():
                st.warning(f"{r['item_name']} – Stock: {r['stock_qty']} (Min: {r['min_qty']})")

    # Inventory Tab with fixed bug in DELETE handling
    with tab_objs[1]:
        st.header("Inventory Management")
        inv = list_inventory().copy()
        inv.insert(0, "DELETE", False)
        edited = st.data_editor(
            inv, use_container_width=True, num_rows="dynamic",
            key="inv_edit"
        )

        c1, c2 = st.columns([0.3,0.7])
        with c1:
            if st.button("Save Changes"):
                df = edited.copy()
                # FIX: Proper boolean conversion for DELETE
                df["DELETE"] = df["DELETE"].astype(bool)
                df = df.loc[~df["DELETE"]].drop(columns=["DELETE"])
                # Generate missing IDs
                for i, r in df[df["item_id"].astype(str).str.strip()==""].iterrows():
                    df.at[i, "item_id"] = hashlib.md5(r["item_name"].encode()).hexdigest()[:8]
                for col in ["stock_qty", "rate", "min_qty", "sell_price"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                df["sell_price"] = df["sell_price"].map(round_to_5)
                df = df[SCHEMA["inventory"]]
                save_csv(df, INVENTORY_FILE)
                st.success("Inventory saved.")
                st.rerun()
        with c2:
            csv_download(list_inventory(), "Inventory")
            if st.button("Export PDF"):
                pdf = make_pdf_bytes("Inventory", list_inventory())
                st.download_button("Download PDF", pdf, "inventory.pdf", "application/pdf")

    # ... Similarly implement other tabs: Expenses, Menu/Booking, Payments, Reports, Users ...

if st.session_state.user is None:
    login_page()
else:
    app_ui()
