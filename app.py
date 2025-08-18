# app.py — DailyShop Dairy (single-file, final)
# ------------------------------------------------------------
# Requirements:
#   pip install streamlit pandas fpdf openpyxl
# Run:
#   streamlit run app.py
# ------------------------------------------------------------

import os
import hashlib
from datetime import datetime, date
from io import BytesIO

import pandas as pd
import streamlit as st

# PDF support optional
try:
    from fpdf import FPDF
    FPDF_OK = True
except Exception:
    FPDF_OK = False

# -----------------------------
# Config & file paths
# -----------------------------
st.set_page_config(page_title="DailyShop Dairy", layout="wide", page_icon="🛒")
DATA_DIR = "data"
EXCEL_FILE = "DailyShop Dairy - Aug.xlsx"  # must be in repo root
USERS_FILE = os.path.join(DATA_DIR, "users.csv")
INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.csv")
EXPENSES_FILE = os.path.join(DATA_DIR, "expenses.csv")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.csv")
PAYMENTS_FILE = os.path.join(DATA_DIR, "payments.csv")

SCHEMA = {
    "users": ["user_id", "name", "role", "mobile", "password_hash"],
    "inventory": ["item_id", "item_name", "category", "unit", "stock_qty", "rate", "min_qty"],
    "expenses": ["date", "type", "category", "item", "item_id", "qty", "rate", "amount", "user_id", "remarks"],
    "orders": ["date", "customer_id", "item_id", "item_name", "qty", "rate", "total", "payment_mode", "balance", "user_id", "remarks"],
    "payments": ["date", "customer_id", "amount", "mode", "remarks", "user_id"],
}

# -----------------------------
# Helpers: filesystem & CSV
# -----------------------------
def safe_make_data_dir():
    # If data exists and is a file, remove it; then create folder
    if os.path.exists(DATA_DIR) and not os.path.isdir(DATA_DIR):
        try:
            os.remove(DATA_DIR)
        except Exception:
            pass
    os.makedirs(DATA_DIR, exist_ok=True)

def new_df(cols):
    return pd.DataFrame(columns=cols)

def load_csv(path, cols):
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
        except Exception:
            df = pd.read_csv(path, encoding="latin1")
        # ensure columns
        for c in cols:
            if c not in df.columns:
                df[c] = None
        return df[cols]
    return new_df(cols)

def save_csv(df, path):
    df.to_csv(path, index=False)

# -----------------------------
# Password hashing & auth
# -----------------------------
def hash_password(pw: str) -> str:
    return hashlib.sha256(str(pw).encode("utf-8")).hexdigest()

def check_password(raw_pw: str, pw_hash: str) -> bool:
    return hash_password(raw_pw) == pw_hash

# -----------------------------
# Bootstrap: files and optionally import from Excel
# -----------------------------
def import_from_excel_if_missing():
    """
    If inventory.csv or expenses.csv not present, attempt to read the Excel file
    in repo root and create them. Non-destructive: only runs when CSV missing.
    """
    # Inventory
    if not os.path.exists(INVENTORY_FILE):
        if os.path.exists(EXCEL_FILE):
            try:
                xls = pd.ExcelFile(EXCEL_FILE)
                if "Item List" in xls.sheet_names:
                    items = pd.read_excel(xls, "Item List")
                    # Map column names — tolerant to minor name differences
                    col_map = {}
                    for c in items.columns:
                        lc = str(c).strip().lower()
                        if "item#" in lc or c.lower().startswith("item#"):
                            col_map[c] = "item_id"
                        elif "item name" in lc or "itemname" in lc or "item name" in lc:
                            col_map[c] = "item_name"
                        elif "unit" in lc:
                            col_map[c] = "unit"
                        elif "category" in lc:
                            col_map[c] = "category"
                        elif "supplier" in lc and "rate" in lc:
                            col_map[c] = "rate"
                        elif "rate" in lc and "supplier" not in lc:
                            col_map[c] = "rate"
                    items = items.rename(columns=col_map)
                    # Keep required columns
                    inv = new_df(SCHEMA["inventory"])
                    # Try to fill
                    for idx, r in items.iterrows():
                        item_id = r.get("item_id", idx + 1)
                        name = r.get("item_name", r.get("Item Name", f"Item {item_id}"))
                        unit = r.get("unit", "")
                        category = r.get("category", "")
                        rate = r.get("rate", 0.0) if r.get("rate", 0) is not None else 0.0
                        inv.loc[len(inv)] = [item_id, name, category, unit, 0.0, float(rate or 0.0), 0.0]
                    save_csv(inv, INVENTORY_FILE)
            except Exception as e:
                st.warning("Inventory import from Excel failed (continuing with empty inventory).")
        else:
            save_csv(new_df(SCHEMA["inventory"]), INVENTORY_FILE)

    # Expenses
    if not os.path.exists(EXPENSES_FILE):
        if os.path.exists(EXCEL_FILE):
            try:
                xls = pd.ExcelFile(EXCEL_FILE)
                if "Daily Entry_Aug" in xls.sheet_names:
                    exp = pd.read_excel(xls, "Daily Entry_Aug")
                    # Map columns (tolerant)
                    colmap = {}
                    for c in exp.columns:
                        lc = str(c).strip().lower()
                        if "date" in lc:
                            colmap[c] = "date"
                        elif "item particular" in lc or "item" == lc or "item particular" in lc:
                            colmap[c] = "item"
                        elif "debit amount" in lc or "debit amount" in lc:
                            colmap[c] = "amount"
                        elif "category" in lc:
                            colmap[c] = "category"
                        elif "debit account" in lc:
                            colmap[c] = "user_id"
                    exp = exp.rename(columns=colmap)
                    exdf = new_df(SCHEMA["expenses"])
                    for _, r in exp.iterrows():
                        dt = r.get("date")
                        # Normalize date to ISO string
                        if pd.isna(dt):
                            dt_str = datetime.now().date().isoformat()
                        else:
                            try:
                                dt_parsed = pd.to_datetime(dt)
                                dt_str = dt_parsed.date().isoformat()
                            except Exception:
                                dt_str = str(dt)
                        category = r.get("category", "")
                        item = r.get("item", "")
                        amount = r.get("amount", r.get("Total", 0.0))
                        user_id = r.get("user_id", "")
                        exdf.loc[len(exdf)] = [dt_str, "Expense", category, item, "", 0.0, 0.0, float(amount or 0.0), user_id, ""]
                    save_csv(exdf, EXPENSES_FILE)
            except Exception as e:
                st.warning("Expenses import from Excel failed (continuing with empty expenses).")
        else:
            save_csv(new_df(SCHEMA["expenses"]), EXPENSES_FILE)

def ensure_data_files_and_import():
    # create folder safely
    safe_make_data_dir()
    # make placeholder CSVs if missing (so loads won't fail)
    if not os.path.exists(USERS_FILE):
        save_csv(new_df(SCHEMA["users"]), USERS_FILE)
    if not os.path.exists(ORDERS_FILE):
        save_csv(new_df(SCHEMA["orders"]), ORDERS_FILE)
    if not os.path.exists(PAYMENTS_FILE):
        save_csv(new_df(SCHEMA["payments"]), PAYMENTS_FILE)
    # import inventory & expenses from Excel if those CSVs don't exist or are empty
    import_from_excel_if_missing()

def ensure_default_admin():
    ensure_data_files_and_import()
    users = load_csv(USERS_FILE, SCHEMA["users"])
    # if admin absent, add default admin
    if users.empty or not (users["mobile"].astype(str) == "9999999999").any():
        admin = {
            "user_id": "admin",
            "name": "Master Admin",
            "role": "admin",
            "mobile": "9999999999",
            "password_hash": hash_password("admin123")
        }
        users = pd.concat([users, pd.DataFrame([admin])], ignore_index=True)
        save_csv(users, USERS_FILE)

# -----------------------------
# Business logic functions
# -----------------------------
def upsert_user(mobile, name, role, password):
    users = load_csv(USERS_FILE, SCHEMA["users"])
    exists = users[users["mobile"].astype(str) == str(mobile)]
    if exists.empty:
        users.loc[len(users)] = [mobile, name, role, mobile, hash_password(password)]
    else:
        idx = exists.index[0]
        users.loc[idx, ["name", "role", "password_hash"]] = [name, role, hash_password(password)]
    save_csv(users, USERS_FILE)

def list_items():
    return load_csv(INVENTORY_FILE, SCHEMA["inventory"])

def upsert_inventory(item_id, item_name, category, unit, stock_qty, rate, min_qty):
    inv = list_items()
    exists = inv[inv["item_id"].astype(str) == str(item_id)]
    if exists.empty:
        inv.loc[len(inv)] = [item_id, item_name, category, unit, float(stock_qty), float(rate), float(min_qty)]
    else:
        idx = exists.index[0]
        inv.loc[idx, ["item_name", "category", "unit", "stock_qty", "rate", "min_qty"]] = [item_name, category, unit, float(stock_qty), float(rate), float(min_qty)]
    save_csv(inv, INVENTORY_FILE)

def adjust_stock(item_id, delta):
    inv = list_items()
    row = inv[inv["item_id"].astype(str) == str(item_id)]
    if row.empty:
        return False, "Item not found"
    idx = row.index[0]
    current = float(inv.loc[idx, "stock_qty"] or 0)
    new = current + float(delta)
    if new < 0:
        return False, "Insufficient stock"
    inv.loc[idx, "stock_qty"] = new
    save_csv(inv, INVENTORY_FILE)
    return True, new

def add_expense_row(dt, category, item, amount, user_id="", remarks=""):
    df = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    df.loc[len(df)] = [dt.isoformat() if isinstance(dt, (date, datetime)) else str(dt), "Expense", category, item, "", 0.0, 0.0, float(amount or 0.0), user_id, remarks]
    save_csv(df, EXPENSES_FILE)

def add_purchase_row(dt, category, item, item_id, qty, rate, amount, user_id="", remarks=""):
    df = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    df.loc[len(df)] = [dt.isoformat() if isinstance(dt, (date, datetime)) else str(dt), "Purchase", category, item, item_id, qty, rate, amount, user_id, remarks]
    save_csv(df, EXPENSES_FILE)

def add_order_row(dt, customer_id, item_id, item_name, qty, rate, total, payment_mode, balance, user_id="", remarks=""):
    df = load_csv(ORDERS_FILE, SCHEMA["orders"])
    df.loc[len(df)] = [dt.isoformat() if isinstance(dt, (date, datetime)) else str(dt), customer_id, item_id, item_name, qty, rate, total, payment_mode, balance, user_id, remarks]
    save_csv(df, ORDERS_FILE)

def add_payment_row(dt, customer_id, amount, mode, remarks="", user_id=""):
    df = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
    df.loc[len(df)] = [dt.isoformat() if isinstance(dt, (date, datetime)) else str(dt), customer_id, amount, mode, remarks, user_id]
    save_csv(df, PAYMENTS_FILE)

def compute_customer_balances_df():
    orders = load_csv(ORDERS_FILE, SCHEMA["orders"])
    payments = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
    if orders.empty and payments.empty:
        return new_df(["customer_id", "credit_sales_total", "payments_total", "pending_balance"])
    credit = orders[orders["payment_mode"] == "Credit"].copy()
    credit["total"] = pd.to_numeric(credit["total"], errors="coerce").fillna(0.0)
    credits_sum = credit.groupby("customer_id")["total"].sum().rename("credit_sales_total")
    payments["amount"] = pd.to_numeric(payments["amount"], errors="coerce").fillna(0.0)
    pays_sum = payments.groupby("customer_id")["amount"].sum().rename("payments_total")
    joined = pd.concat([credits_sum, pays_sum], axis=1).fillna(0.0)
    joined["pending_balance"] = joined["credit_sales_total"] - joined["payments_total"]
    out = joined.reset_index().rename(columns={"index": "customer_id"})
    out = out.reset_index(drop=True)
    return out.sort_values("pending_balance", ascending=False)

# -----------------------------
# Exports & PDF
# -----------------------------
def csv_download_button(df, label):
    if df.empty:
        st.warning("No data to download.")
        return
    st.download_button(f"⬇️ Download {label} (CSV)", data=df.to_csv(index=False).encode("utf-8"), file_name=f"{label.replace(' ','_')}.csv", mime="text/csv")

def make_simple_pdf_bytes(title, intro_lines, tables):
    if not FPDF_OK:
        return None
    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, title, ln=True)
    pdf.set_font("Helvetica", size=10)
    for line in intro_lines:
        pdf.multi_cell(0, 6, line)
    pdf.ln(4)
    for name, df in tables:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, name, ln=True)
        pdf.set_font("Helvetica", size=9)
        if df.empty:
            pdf.cell(0, 6, "No data", ln=True)
            pdf.ln(2)
            continue
        # simple table print: show up to first 10 cols
        cols = list(df.columns)[:8]
        colw = pdf.w / max(len(cols), 1) - 2
        # header
        for c in cols:
            pdf.cell(colw, 7, str(c)[:15], border=1)
        pdf.ln()
        for _, row in df.head(40).iterrows():
            for c in cols:
                pdf.cell(colw, 6, str(row[c])[:15], border=1)
            pdf.ln()
        pdf.ln(3)
    return bytes(pdf.output(dest="S").encode("latin-1"))

# -----------------------------
# UI helpers
# -----------------------------
def kpi_card(label, value):
    st.markdown(f"""
        <div style="background:#fff;border-radius:12px;padding:14px;box-shadow:0 6px 18px rgba(0,0,0,0.06);">
            <div style="font-size:20px;font-weight:700;margin-bottom:4px;">{value}</div>
            <div style="color:#64748b;">{label}</div>
        </div>
    """, unsafe_allow_html=True)

# -----------------------------
# App initialization
# -----------------------------
ensure_default_admin()

if "user" not in st.session_state:
    st.session_state.user = None

# -----------------------------
# Login screen
# -----------------------------
if st.session_state.user is None:
    st.markdown("<h2 style='text-align:center;color:#2563EB;'>🛒 DailyShop Dairy</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#64748b;'>Manage inventory, purchases, sales, expenses & cash</p>", unsafe_allow_html=True)
    with st.form("login", clear_on_submit=False):
        mobile = st.text_input("📱 Mobile Number")
        password = st.text_input("🔑 Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            users = load_csv(USERS_FILE, SCHEMA["users"])
            user_row = users[users["mobile"].astype(str) == str(mobile)]
            if user_row.empty:
                st.error("Invalid mobile or password")
            else:
                user = user_row.iloc[0].to_dict()
                if check_password(password, user["password_hash"]):
                    st.session_state.user = user
                    st.success(f"Welcome {user['name']}!")
                    st.experimental_rerun()
                else:
                    st.error("Invalid mobile or password")
    st.caption("Tip: default admin → mobile: 9999999999 / password: admin123")
    st.stop()

# -----------------------------
# After login: top tabs
# -----------------------------
user = st.session_state.user
colL, colR = st.columns([0.75, 0.25])
with colL:
    st.markdown("<h3 style='margin:0;color:#0f172a;'>🛒 DailyShop Dairy</h3>", unsafe_allow_html=True)
with colR:
    st.markdown(f"**{user['name']}**  ·  {user['role']}", unsafe_allow_html=True)
    if st.button("Logout"):
        st.session_state.user = None
        st.experimental_rerun()

tabs = ["📊 Dashboard", "📦 Inventory", "💰 Expenses", "🛒 Sales", "💵 Payments", "🧾 Reports"]
if user["role"] == "admin":
    tabs.append("👥 Users")
tab_objs = st.tabs(tabs)

# -----------------------------
# Tab: Dashboard
# -----------------------------
with tab_objs[0]:
    inv = list_items()
    exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    orders = load_csv(ORDERS_FILE, SCHEMA["orders"])
    pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
    total_exp = float(exp["amount"].sum()) if not exp.empty else 0.0
    total_sales = float(orders["total"].sum()) if not orders.empty else 0.0
    inv["stock_qty"] = pd.to_numeric(inv["stock_qty"], errors="coerce").fillna(0.0)
    inv["rate"] = pd.to_numeric(inv["rate"], errors="coerce").fillna(0.0)
    stock_value = float((inv["stock_qty"] * inv["rate"]).sum()) if not inv.empty else 0.0
    balances = compute_customer_balances_df()
    pending_total = float(balances["pending_balance"].sum()) if not balances.empty else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Total Expenses", f"₹ {total_exp:,.2f}")
    with c2: kpi_card("Total Sales", f"₹ {total_sales:,.2f}")
    with c3: kpi_card("Stock Value (Est.)", f"₹ {stock_value:,.2f}")
    with c4: kpi_card("Pending Balances", f"₹ {pending_total:,.2f}")

    st.markdown("### ⚠️ Low stock alerts")
    low = inv[(inv["stock_qty"].astype(float) < inv["min_qty"].astype(float))]
    if low.empty:
        st.success("No low-stock items.")
    else:
        st.dataframe(low[["item_id", "item_name", "stock_qty", "min_qty", "rate"]])

# -----------------------------
# Tab: Inventory
# -----------------------------
with tab_objs[1]:
    st.header("Inventory Master")
    inv = list_items()
    with st.expander("➕ Add / Update Item", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            item_id = st.text_input("Item ID (unique)")
            item_name = st.text_input("Item Name")
            category = st.text_input("Category")
        with col2:
            unit = st.text_input("Unit (kg/pack/pcs)")
            rate = st.number_input("Rate (₹)", min_value=0.0, step=0.1, value=0.0)
            min_qty = st.number_input("Min Qty (alert below)", min_value=0.0, step=0.1, value=0.0)
        with col3:
            stock_qty = st.number_input("Stock Qty", min_value=0.0, step=0.1, value=0.0)
            if st.button("Save Item"):
                if not item_id or not item_name:
                    st.error("Provide item ID and name")
                else:
                    upsert_inventory(item_id, item_name, category, unit, stock_qty, rate, min_qty)
                    st.success("Item saved.")
                    st.experimental_rerun()
    st.markdown("#### Inventory List")
    st.dataframe(list_items(), use_container_width=True)
    csv_download_button(list_items(), "Inventory")

# -----------------------------
# Tab: Expenses (Purchases + Non-stock)
# -----------------------------
with tab_objs[2]:
    st.header("Purchases & Expenses")
    inv = list_items()
    item_labels = [f"{r['item_name']} ({r['item_id']})" for _, r in inv.iterrows()] if not inv.empty else []

    colA, colB = st.columns(2)
    with colA:
        st.subheader("Purchase (Stock-In)")
        with st.form("purchase_form", clear_on_submit=True):
            p_date = st.date_input("Date", datetime.now().date())
            p_item = st.selectbox("Item", options=["-- Select --"] + item_labels)
            p_qty = st.number_input("Qty", min_value=0.0, step=0.1, value=0.0)
            p_rate = st.number_input("Rate (₹)", min_value=0.0, step=0.1, value=0.0)
            p_category = st.text_input("Category", value="Purchase")
            p_remarks = st.text_input("Remarks")
            submit_p = st.form_submit_button("Add Purchase")
        if submit_p:
            if p_item == "-- Select --":
                st.error("Select item")
            else:
                pid = p_item.split("(")[-1].replace(")", "").strip()
                ok, msg = adjust_stock(pid, p_qty)
                if not ok:
                    st.error(msg)
                else:
                    amount = round(p_qty * p_rate, 2)
                    add_purchase_row(p_date, p_category, p_item.split("(")[0].strip(), pid, p_qty, p_rate, amount, user_id=user.get("user_id",""), remarks=p_remarks)
                    st.success("Purchase recorded & stock updated.")
                    st.experimental_rerun()

    with colB:
        st.subheader("Expense (Non-stock)")
        with st.form("expense_form", clear_on_submit=True):
            e_date = st.date_input("Date", datetime.now().date())
            e_cat = st.text_input("Category")
            e_item = st.text_input("Expense Title")
            e_amt = st.number_input("Amount (₹)", min_value=0.0, step=0.1)
            e_rem = st.text_input("Remarks")
            submit_e = st.form_submit_button("Record Expense")
        if submit_e:
            add_expense_row(e_date, e_cat, e_item, e_amt, user_id=user.get("user_id",""), remarks=e_rem)
            st.success("Expense recorded.")
            st.experimental_rerun()

    st.markdown("#### Recent Purchases & Expenses")
    st.dataframe(load_csv(EXPENSES_FILE, SCHEMA["expenses"]).sort_values("date", ascending=False), use_container_width=True)
    csv_download_button(load_csv(EXPENSES_FILE, SCHEMA["expenses"]), "Expenses")

# -----------------------------
# Tab: Sales / Orders
# -----------------------------
with tab_objs[3]:
    st.header("Sales / Orders")
    inv = list_items()
    if inv.empty:
        st.warning("Inventory empty — add items first.")
    else:
        item_options = {f"{r['item_name']} ({r['item_id']})": r["item_id"] for _, r in inv.iterrows()}
        with st.form("sale_form", clear_on_submit=True):
            s_date = st.date_input("Date", datetime.now().date())
            s_cust = st.text_input("Customer Mobile")
            s_item = st.selectbox("Item", options=["-- Select --"] + list(item_options.keys()))
            s_qty = st.number_input("Qty", min_value=0.0, step=0.1, value=1.0)
            use_item_rate = st.checkbox("Use Item Rate", value=True)
            s_rate_in = st.number_input("Rate (₹)", min_value=0.0, step=0.1, value=0.0, disabled=use_item_rate)
            s_mode = st.radio("Payment Mode", ["Cash", "Credit"], horizontal=True)
            s_rem = st.text_input("Remarks")
            submit_sale = st.form_submit_button("Record Sale")
        if submit_sale:
            if s_item == "-- Select --":
                st.error("Select item")
            elif not s_cust:
                st.error("Customer mobile required")
            else:
                pid = item_options[s_item]
                item = inv[inv["item_id"].astype(str) == str(pid)].iloc[0]
                rate = float(item["rate"]) if use_item_rate else float(s_rate_in)
                total = round(rate * float(s_qty), 2)
                balance = total if s_mode == "Credit" else 0.0
                ok, msg = adjust_stock(pid, -s_qty)
                if not ok:
                    st.error(msg)
                else:
                    add_order_row(s_date, s_cust, pid, item["item_name"], s_qty, rate, total, s_mode, balance, user_id=user.get("user_id",""), remarks=s_rem)
                    st.success("Sale recorded & stock updated.")
                    st.experimental_rerun()

    st.markdown("#### Recent Sales")
    st.dataframe(load_csv(ORDERS_FILE, SCHEMA["orders"]).sort_values("date", ascending=False), use_container_width=True)
    csv_download_button(load_csv(ORDERS_FILE, SCHEMA["orders"]), "Sales_Orders")

# -----------------------------
# Tab: Payments
# -----------------------------
with tab_objs[4]:
    st.header("Customer Payments")
    balances = compute_customer_balances_df()
    if not balances.empty:
        st.dataframe(balances, use_container_width=True)
    else:
        st.info("No credit sales / balances yet.")

    with st.form("pay_form", clear_on_submit=True):
        p_date = st.date_input("Date", datetime.now().date())
        p_customer = st.text_input("Customer mobile")
        p_amount = st.number_input("Amount (₹)", min_value=0.0, step=0.1)
        p_mode = st.selectbox("Mode", ["Cash", "UPI", "Card", "Other"])
        p_rem = st.text_input("Remarks")
        submit_pay = st.form_submit_button("Record Payment")
    if submit_pay:
        if not p_customer or p_amount <= 0:
            st.error("Customer and amount required.")
        else:
            add_payment_row(p_date, p_customer, p_amount, p_mode, p_rem, user_id=user.get("user_id",""))
            st.success("Payment recorded.")
            st.experimental_rerun()

    st.markdown("#### Payment History")
    st.dataframe(load_csv(PAYMENTS_FILE, SCHEMA["payments"]).sort_values("date", ascending=False), use_container_width=True)
    csv_download_button(load_csv(PAYMENTS_FILE, SCHEMA["payments"]), "Payments")

# -----------------------------
# Tab: Reports
# -----------------------------
with tab_objs[5]:
    st.header("Reports & Exports")
    today = datetime.now().date()
    default_start = today.replace(day=1)
    col1, col2, col3 = st.columns([1.2, 1.2, 1.6])
    with col1:
        start_date = st.date_input("Start date", default_start)
    with col2:
        end_date = st.date_input("End date", today)
    with col3:
        filter_customer = st.text_input("Filter by customer (mobile)")

    exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    ords = load_csv(ORDERS_FILE, SCHEMA["orders"])
    pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"])

    def drange(df, col="date"):
        if df.empty:
            return df
        df2 = df.copy()
        df2[col] = pd.to_datetime(df2[col], errors="coerce").dt.date
        return df2[(df2[col] >= start_date) & (df2[col] <= end_date)]

    exp_f = drange(exp, "date")
    ord_f = drange(ords, "date")
    pay_f = drange(pays, "date")
    if filter_customer:
        ord_f = ord_f[ord_f["customer_id"].astype(str) == str(filter_customer)]
        pay_f = pay_f[pay_f["customer_id"].astype(str) == str(filter_customer)]

    cash_sales = ord_f[ord_f["payment_mode"] == "Cash"]["total"].sum() if not ord_f.empty else 0.0
    total_sales = ord_f["total"].sum() if not ord_f.empty else 0.0
    total_exp = exp_f["amount"].sum() if not exp_f.empty else 0.0
    net_cash = cash_sales - total_exp

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Expenses (range)", f"₹ {total_exp:,.2f}")
    with c2: kpi_card("Sales (range)", f"₹ {total_sales:,.2f}")
    with c3: kpi_card("Cash Sales (range)", f"₹ {cash_sales:,.2f}")
    with c4: kpi_card("Net Cash (Cash Sales - Expenses)", f"₹ {net_cash:,.2f}")

    st.markdown("#### Expenses (filtered)")
    st.dataframe(exp_f, use_container_width=True)
    csv_download_button(exp_f, "Expenses_Filtered")

    st.markdown("#### Sales (filtered)")
    st.dataframe(ord_f, use_container_width=True)
    csv_download_button(ord_f, "Sales_Filtered")

    st.markdown("#### Payments (filtered)")
    st.dataframe(pay_f, use_container_width=True)
    csv_download_button(pay_f, "Payments_Filtered")

    st.markdown("#### Customer Balances")
    balances = compute_customer_balances_df()
    st.dataframe(balances, use_container_width=True)
    csv_download_button(balances, "Customer_Balances")

    st.markdown("### Export PDF (optional)")
    if FPDF_OK:
        intro = [f"Date range: {start_date} - {end_date}", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"]
        tables = [("Summary", pd.DataFrame({
            "Metric": ["Expenses (range)", "Sales (range)", "Cash Sales (range)", "Net Cash"],
            "Value": [f"₹ {total_exp:,.2f}", f"₹ {total_sales:,.2f}", f"₹ {cash_sales:,.2f}", f"₹ {net_cash:,.2f}"]
        })), ("Expenses", exp_f), ("Sales", ord_f), ("Payments", pay_f), ("Balances", balances)]
        pdf_bytes = make_simple_pdf_bytes("DailyShop Dairy Report", intro, tables)
        if pdf_bytes:
            st.download_button("🧾 Download PDF", data=pdf_bytes, file_name="dailyshop_report.pdf", mime="application/pdf")
    else:
        st.info("PDF export requires 'fpdf' package - add to requirements if you want PDFs.")

# -----------------------------
# Tab: Users (admin only)
# -----------------------------
if user["role"] == "admin":
    with tab_objs[-1]:
        st.header("User Management (Admin)")
        users = load_csv(USERS_FILE, SCHEMA["users"])
        st.markdown("#### Existing users")
        if users.empty:
            st.info("No users yet (apart from default admin).")
        else:
            st.dataframe(users[["user_id", "name", "role", "mobile"]], use_container_width=True)

        st.markdown("#### Add / Update User")
        with st.form("user_form"):
            u_mobile = st.text_input("Mobile (login id)")
            u_name = st.text_input("Full name")
            u_role = st.selectbox("Role", ["staff", "customer", "admin"])
            u_password = st.text_input("Password", type="password")
            submit_user = st.form_submit_button("Save User")
        if submit_user:
            if not u_mobile or not u_name or not u_password:
                st.error("All fields required.")
            else:
                upsert_user(u_mobile, u_name, u_role, u_password)
                st.success("User saved/updated.")
                st.experimental_rerun()

        st.markdown("#### Delete User")
        del_mobile = st.text_input("Mobile to delete")
        if st.button("Delete User"):
            df = load_csv(USERS_FILE, SCHEMA["users"])
            df2 = df[df["mobile"].astype(str) != str(del_mobile)]
            save_csv(df2, USERS_FILE)
            st.success("Deleted (if existed).")
            st.experimental_rerun()
