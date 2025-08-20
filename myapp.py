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

# -------------------------------
# Configuration
# -------------------------------
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

# -------------------------------
# Utilities (Load, Save, Hash, Round)
# -------------------------------
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
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")

def hash_pw(pw): return hashlib.sha256(str(pw).encode("utf-8")).hexdigest()
def check_pw(raw, hashed): return hash_pw(raw) == hashed

def round_to_5(n):
    try: return int(round(float(n) / 5.0) * 5)
    except: return 0

# -------------------------------
# Bootstrap Default Files
# -------------------------------
def bootstrap_files():
    safe_make_data_dir()
    if not os.path.exists(USERS_FILE):
        admin = pd.DataFrame([{"user_id":"admin","name":"Master Admin",
                               "role":"admin","mobile":"9999999999",
                               "password_hash":hash_pw("admin123")}],
                             columns=SCHEMA["users"])
        save_csv(admin, USERS_FILE)
    for path, cols in [(INVENTORY_FILE, SCHEMA["inventory"]),
                       (EXPENSES_FILE, SCHEMA["expenses"]),
                       (ORDERS_FILE, SCHEMA["orders"]),
                       (PAYMENTS_FILE, SCHEMA["payments"])]:
        if not os.path.exists(path):
            save_csv(new_df(cols), path)
        else:
            df = load_csv(path, cols)
            save_csv(df, path)

bootstrap_files()

# -------------------------------
# Business Logic
# -------------------------------
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
    if row.empty: return False, "Item not found"
    idx = row.index[0]
    curr = row.at[idx, "stock_qty"]
    new = curr + float(delta)
    if new < 0:
        return False, {"current": curr, "requested": abs(delta)}
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

def list_users():
    return load_csv(USERS_FILE, SCHEMA["users"])

def record_expense(dt, category, item, amount, user_id, remarks):
    df = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    df.loc[len(df)] = [dt.isoformat(), "Expense", category, item, "", 0.0, 0.0, amount, user_id, remarks]
    save_csv(df, EXPENSES_FILE)

def record_payment(dt, cust_id, amount, mode, user_id, remarks):
    df = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
    df.loc[len(df)] = [dt.isoformat(), cust_id, amount, mode, remarks, user_id]
    save_csv(df, PAYMENTS_FILE)

def compute_customer_balances():
    orders = load_csv(ORDERS_FILE, SCHEMA["orders"])
    payments = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
    if orders.empty and payments.empty:
        return new_df(["customer_id","credit_sales_total","payments_total","pending_balance"])
    credits = orders[orders["payment_mode"].str.lower() == "credit"].copy()
    credits["total"] = pd.to_numeric(credits["total"], errors="coerce").fillna(0)
    cs = credits.groupby("customer_id")["total"].sum().rename("credit_sales_total")
    payments["amount"] = pd.to_numeric(payments["amount"], errors="coerce").fillna(0)
    ps = payments.groupby("customer_id")["amount"].sum().rename("payments_total")
    df = pd.concat([cs, ps], axis=1).fillna(0)
    df["pending_balance"] = df["credit_sales_total"] - df["payments_total"]
    out = df.reset_index().rename(columns={"index":"customer_id"})
    return out.sort_values("pending_balance", ascending=False)

# -------------------------------
# Exports
# -------------------------------
def csv_download(df, label):
    if df.empty:
        st.warning("No data to export.")
        return
    st.download_button(f"⬇ Download {label} (CSV)", df.to_csv(index=False).encode('utf-8'),
                       f"{label.replace(' ','_')}.csv", "text/csv")

def make_pdf_bytes(title, df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 8, txt=title, ln=True)
    pdf.ln(2)
    if df.empty:
        pdf.cell(0,6,"No data", ln=True)
        return pdf.output(dest="S").encode("latin1","ignore")
    cols = list(df.columns)[:8]
    colw = pdf.w / max(len(cols),1) - 2
    for c in cols:
        pdf.cell(colw, 7, str(c)[:20], border=1)
    pdf.ln()
    for _, row in df.iterrows():
        for c in cols:
            text = str(row.get(c,""))
            safe = text.encode("latin1", "replace").decode("latin1")
            pdf.cell(colw, 6, safe[:20], border=1)
        pdf.ln()
    return pdf.output(dest="S").encode("latin1","ignore")

# -------------------------------
# Auth & Layout
# -------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

def login_page():
    st.title(APP_TITLE)
    st.info("Login (Admin by default: 9999999999 / admin123)")
    with st.form("login"):
        mobile = st.text_input("Mobile")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user = get_user_by_mobile(mobile)
            if user and check_pw(pw, user["password_hash"]):
                st.session_state.user = user
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")

def app_ui():
    usr = st.session_state.user
    menu = ["Dashboard", "Menu / Booking"]
    if usr["role"] == "admin":
        menu = ["Dashboard", "Inventory", "Expenses", "Menu / Booking", "Payments", "Reports", "Users"]
    tabs = st.tabs(menu)

    # Dashboard
    with tabs[0]:
        st.header("Dashboard")
        inv = list_inventory()
        exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
        ords = load_csv(ORDERS_FILE, SCHEMA["orders"])
        pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
        total_exp = exp["amount"].astype(float).sum() if not exp.empty else 0.0
        total_sales = ords["total"].astype(float).sum() if not ords.empty else 0.0
        stock_value = (inv["stock_qty"].astype(float) * inv["rate"].astype(float)).sum() if not inv.empty else 0.0
        balances = compute_customer_balances()
        pending = balances["pending_balance"].sum() if not balances.empty else 0.0
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total Expenses", f"₹ {total_exp:,.2f}")
        c2.metric("Total Sales", f"₹ {total_sales:,.2f}")
        c3.metric("Stock Value", f"₹ {stock_value:,.2f}")
        c4.metric("Pending Balances", f"₹ {pending:,.2f}")
        st.subheader("Low-stock alerts")
        low = inv[inv["stock_qty"] < inv["min_qty"]]
        if low.empty:
            st.info("All good!")
        else:
            for _, r in low.iterrows():
                st.warning(f"{r['item_name']}: {r['stock_qty']} (min {r['min_qty']})")
    # Inventory
    if usr["role"] == "admin":
        with tabs[1]:
            st.header("Inventory Master")
            inv = list_inventory().copy()
            inv.insert(0, "DELETE", False)
            edited = st.data_editor(inv, use_container_width=True, num_rows="dynamic", 
                                    column_config={
                                        "DELETE": st.column_config.CheckboxColumn(),
                                        "item_id": st.column_config.TextColumn(),
                                        "item_name": st.column_config.TextColumn(),
                                        "category": st.column_config.TextColumn(),
                                        "unit": st.column_config.TextColumn(),
                                        "stock_qty": st.column_config.NumberColumn(),
                                        "rate": st.column_config.NumberColumn(),
                                        "min_qty": st.column_config.NumberColumn(),
                                        "sell_price": st.column_config.NumberColumn()
                                    })
            if st.button("Save Inventory"):
                df = edited[~edited["DELETE"]].drop(columns="DELETE")
                for i, r in df[df["item_id"].isna() | (df["item_id"]=="")].iterrows():
                    df.at[i, "item_id"] = hashlib.md5(str(r["item_name"]).encode()).hexdigest()[:8]
                for c in ["stock_qty","rate","min_qty","sell_price"]:
                    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
                df["sell_price"] = df["sell_price"].map(round_to_5)
                save_csv(df[SCHEMA["inventory"]], INVENTORY_FILE)
                st.success("Saved!")
                st.experimental_rerun()
    # Expenses
    if usr["role"] == "admin":
        with tabs[2]:
            st.header("Purchases & Expenses")
            inv = list_inventory()
            labels = [f"{r['item_name']} ({r['item_id']})" for _,r in inv.iterrows()]
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Record Purchase")
                with st.form("purchase"):
                    d = st.date_input("Date", date.today())
                    itm = st.selectbox("Item", ["--"]+labels)
                    qty = st.number_input("Qty", min_value=0.0, step=0.1)
                    rate = st.number_input("Rate", min_value=0.0, step=0.1)
                    rem = st.text_input("Remarks")
                    if st.form_submit_button("Add"):
                        if itm=="--" or qty<=0:
                            st.error("Select item and qty >0")
                        else:
                            pid = itm.split("(")[-1][:-1]
                            record_expense(d, "Purchase", itm.split("(")[0].strip(), qty*rate, usr["user_id"], rem)
                            adjust_stock(pid, qty)
                            st.success("OK")
            with col2:
                st.subheader("Record Expense")
                with st.form("expense"):
                    d2 = st.date_input("Date", date.today())
                    cat = st.text_input("Category")
                    item = st.text_input("Expense Item")
                    amt = st.number_input("Amount", min_value=0.0, step=0.1)
                    rem2 = st.text_input("Remarks")
                    if st.form_submit_button("Add"):
                        record_expense(d2, cat, item, amt, usr["user_id"], rem2)
                        st.success("OK")
            df = load_csv(EXPENSES_FILE, SCHEMA["expenses"]).sort_values("date", ascending=False)
            st.dataframe(df)
            csv_download(df, "Expenses")
    # Menu / Booking
    mi = 3 if usr["role"]=="admin" else 1
    with tabs[mi]:
        st.header("Menu / Booking")
        inv = list_inventory()
        if inv.empty:
            st.info("No items")
        else:
            cats = ["All"]+sorted(inv["category"].unique())
            sel = st.selectbox("Category", cats)
            df = inv if sel=="All" else inv[inv["category"]==sel]
            names = ["Select"] + df["item_name"].tolist()
            with st.form("order"):
                cust = st.text_input("Customer mobile (for Credit)")
                item = st.selectbox("Item", names)
                qty = st.number_input("Qty", min_value=1, step=1, format="%d")
                pm = st.radio("Payment mode", ["Cash","Credit"])
                default_price = int(df[df["item_name"]==item]["sell_price"].iloc[0]) if item!="Select" else 0
                price = st.number_input("Price (₹)", min_value=0, step=5, format="%d", value=default_price)
                rem = st.text_input("Remarks")
                if st.form_submit_button("Book"):
                    if item=="Select": st.error("Choose item")
                    elif pm=="Credit" and not cust.strip():
                        st.error("Mobile required for Credit")
                    else:
                        cid = cust.strip() if pm=="Credit" else (cust.strip() or "Guest")
                        pid = df[df["item_name"]==item]["item_id"].iloc[0]
                        ok, det = adjust_stock(pid, -qty)
                        if not ok:
                            st.error(f"Insufficient stock ({det['current']} available)")
                        else:
                            adjust_stock(pid, qty)  # rollback
                            record_order(date.today(), cid, pid, item, qty, price, pm, usr["user_id"], rem)
                            st.success("Booked!")
    # Payments & Reports (admin only)
    if usr["role"]=="admin":
        with tabs[4]:
            st.header("Payment / Balances")
            bal = compute_customer_balances()
            st.dataframe(bal)
            csv_download(bal, "Balances")
        with tabs[5]:
            st.header("Reports")
            st.info("Use exports in each tab")
        with tabs[6]:
            st.header("User Management")
            udf = list_users()
            edited = st.data_editor(udf, use_container_width=True, num_rows="dynamic")
            if st.button("Save Users"):
                save_csv(edited, USERS_FILE)
                st.success("Users saved.")
                st.experimental_rerun()

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.experimental_rerun()

# -------------------------------
# Main Execution
# -------------------------------
if st.session_state.user is None:
    login_page()
else:
    app_ui()
