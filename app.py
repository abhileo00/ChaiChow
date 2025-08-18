# app.py — DailyShop Dairy (Single File)
# ------------------------------------------------------------
# Features:
# - Secure auth (admin/staff), mobile-based logins, hashed passwords
# - Top-tab navigation (Dashboard | Inventory | Expenses | Sales | Payments | Reports | Users[admin])
# - Inventory master with min stock & low-stock alerts
# - Purchases (stock-in) + Expenses (non-stock)
# - Sales (cash/credit), auto stock updates
# - Payments to settle customer balances
# - Reports: daily/weekly/monthly, filters, customer balances
# - Export CSV & PDF
# ------------------------------------------------------------
# Requirements:
#   pip install streamlit pandas fpdf
# Run:
#   streamlit run app.py

import os
import hashlib
from datetime import datetime, date, timedelta

import pandas as pd
import streamlit as st
from fpdf import FPDF

# -----------------------------
# App config & styles
# -----------------------------
st.set_page_config(page_title="DailyShop Dairy", layout="wide", page_icon="🛒")

PRIMARY = "#2563EB"
BG = "#f8fafc"

st.markdown(
    f"""
    <style>
    .main {{ background-color: {BG}; }}
    .app-title {{ text-align:center; font-size: 28px; font-weight: 700; color: {PRIMARY}; margin-bottom: 0.6rem; }}
    .card {{
        background: #fff; border-radius: 16px; padding: 18px 18px; 
        box-shadow: 0 6px 20px rgba(0,0,0,0.06); height: 100%;
    }}
    .kpi-value {{ font-size: 26px; font-weight: 700; }}
    .kpi-label {{ color: #475569; margin-top: -2px }}
    .low-stock {{ background: #fff7ed; border: 1px solid #fed7aa; }}
    .primary-btn button {{ background:{PRIMARY}!important; color:#fff!important; border-radius:10px!important; }}
    .pill {{ display:inline-block; padding:.2rem .6rem; background:#eef2ff; color:#3730a3; border-radius:999px; font-size:12px; }}
    .muted {{ color:#64748b }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Data paths & schema
# -----------------------------
DATA_DIR = "data"
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
# Helpers: files & auth
# -----------------------------
def ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def new_df(cols):
    return pd.DataFrame(columns=cols)

def load_csv(path, cols):
    if os.path.exists(path):
        df = pd.read_csv(path)
        # Ensure all columns exist (forward compatibility)
        for c in cols:
            if c not in df.columns:
                df[c] = None
        return df[cols]
    return new_df(cols)

def save_csv(df, path):
    df.to_csv(path, index=False)

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def check_password(raw_pw: str, pw_hash: str) -> bool:
    return hash_password(raw_pw) == pw_hash

def bootstrap_files():
    ensure_dir()

    # Users with default admin (mobile=9999999999 / password=admin123)
    if not os.path.exists(USERS_FILE):
        admin = pd.DataFrame([{
            "user_id": "admin",
            "name": "Master Admin",
            "role": "admin",
            "mobile": "9999999999",
            "password_hash": hash_password("admin123")
        }], columns=SCHEMA["users"])
        save_csv(admin, USERS_FILE)

    # Other data files
    if not os.path.exists(INVENTORY_FILE):
        save_csv(new_df(SCHEMA["inventory"]), INVENTORY_FILE)
    if not os.path.exists(EXPENSES_FILE):
        save_csv(new_df(SCHEMA["expenses"]), EXPENSES_FILE)
    if not os.path.exists(ORDERS_FILE):
        save_csv(new_df(SCHEMA["orders"]), ORDERS_FILE)
    if not os.path.exists(PAYMENTS_FILE):
        save_csv(new_df(SCHEMA["payments"]), PAYMENTS_FILE)

def get_user_by_mobile(mobile: str):
    users = load_csv(USERS_FILE, SCHEMA["users"])
    m = users[users["mobile"] == mobile]
    return m.iloc[0].to_dict() if not m.empty else None

def authenticate(mobile: str, password: str):
    user = get_user_by_mobile(mobile)
    if not user:
        return None
    return user if check_password(password, user["password_hash"]) else None

# -----------------------------
# Business logic
# -----------------------------
def upsert_inventory_item(item_id, item_name, category, unit, stock_qty, rate, min_qty):
    inv = load_csv(INVENTORY_FILE, SCHEMA["inventory"])
    row = inv[inv["item_id"] == item_id]
    if row.empty:
        inv.loc[len(inv)] = [item_id, item_name, category, unit, float(stock_qty), float(rate), float(min_qty)]
    else:
        idx = row.index[0]
        inv.loc[idx, ["item_name", "category", "unit", "rate", "min_qty"]] = [item_name, category, unit, float(rate), float(min_qty)]
        # stock_qty might be managed only via purchases/sales; allow override here if explicitly given
        inv.loc[idx, "stock_qty"] = float(stock_qty)
    save_csv(inv, INVENTORY_FILE)

def adjust_stock(item_id, delta_qty):
    inv = load_csv(INVENTORY_FILE, SCHEMA["inventory"])
    row = inv[inv["item_id"] == item_id]
    if row.empty:
        return False, "Item not found"
    idx = row.index[0]
    new_qty = float(inv.loc[idx, "stock_qty"] or 0) + float(delta_qty)
    if new_qty < 0:
        return False, "Insufficient stock"
    inv.loc[idx, "stock_qty"] = new_qty
    save_csv(inv, INVENTORY_FILE)
    return True, new_qty

def get_item(item_id):
    inv = load_csv(INVENTORY_FILE, SCHEMA["inventory"])
    row = inv[inv["item_id"] == item_id]
    return row.iloc[0].to_dict() if not row.empty else None

def list_items():
    return load_csv(INVENTORY_FILE, SCHEMA["inventory"])

def record_purchase_or_expense(
    when: date, type_: str, category: str, item_name: str, item_id: str, qty: float, rate: float,
    amount: float, user_id: str, remarks: str
):
    exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    exp.loc[len(exp)] = [
        when.isoformat(), type_, category, item_name, item_id, qty, rate, amount, user_id, remarks
    ]
    save_csv(exp, EXPENSES_FILE)

def record_order(
    when: date, customer_id: str, item_id: str, item_name: str, qty: float, rate: float,
    total: float, payment_mode: str, balance: float, user_id: str, remarks: str
):
    orders = load_csv(ORDERS_FILE, SCHEMA["orders"])
    orders.loc[len(orders)] = [
        when.isoformat(), customer_id, item_id, item_name, qty, rate, total, payment_mode, balance, user_id, remarks
    ]
    save_csv(orders, ORDERS_FILE)

def record_payment(when: date, customer_id: str, amount: float, mode: str, remarks: str, user_id: str):
    pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
    pays.loc[len(pays)] = [when.isoformat(), customer_id, amount, mode, remarks, user_id]
    save_csv(pays, PAYMENTS_FILE)

def compute_customer_balances():
    orders = load_csv(ORDERS_FILE, SCHEMA["orders"])
    pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"])

    credit_sales = orders[orders["payment_mode"] == "Credit"]
    credit_sum = credit_sales.groupby("customer_id")["total"].sum().rename("credit_sales_total") if not credit_sales.empty else pd.Series(dtype=float)

    pay_sum = pays.groupby("customer_id")["amount"].sum().rename("payments_total") if not pays.empty else pd.Series(dtype=float)

    out = pd.concat([credit_sum, pay_sum], axis=1).fillna(0.0)
    out["pending_balance"] = out["credit_sales_total"] - out["payments_total"]
    out = out.reset_index().rename(columns={"index": "customer_id"})
    return out.sort_values("pending_balance", ascending=False)

def date_range_filter(df, col="date", start=None, end=None):
    if df.empty:
        return df
    tmp = df.copy()
    tmp[col] = pd.to_datetime(tmp[col]).dt.date
    if start:
        tmp = tmp[tmp[col] >= start]
    if end:
        tmp = tmp[tmp[col] <= end]
    return tmp

# -----------------------------
# Exports
# -----------------------------
def make_downloadable_csv(df, label):
    if df.empty:
        st.warning(f"No data to export for {label}.")
        return
    st.download_button(
        label=f"⬇️ Download {label} (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{label.lower().replace(' ','_')}.csv",
        mime="text/csv",
        use_container_width=True
    )

def make_pdf(title: str, intro_lines: list[str], tables: list[tuple[str, pd.DataFrame]]):
    # Returns bytes for download
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=True)
    pdf.ln(2)
    pdf.set_font("Arial", "", 11)
    for line in intro_lines:
        pdf.multi_cell(0, 6, line)
    pdf.ln(4)

    for section_title, df in tables:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, section_title, ln=True)
        pdf.set_font("Arial", "", 9)
        if df.empty:
            pdf.cell(0, 6, "No data", ln=True)
            pdf.ln(2)
            continue
        # simple table (truncate wide text)
        col_width = pdf.epw / len(df.columns)
        # header
        for col in df.columns:
            pdf.cell(col_width, 7, str(col)[:20], border=1)
        pdf.ln()
        # rows
        for _, row in df.iterrows():
            for col in df.columns:
                pdf.cell(col_width, 7, str(row[col])[:20], border=1)
            pdf.ln()
        pdf.ln(3)

    return bytes(pdf.output(dest="S").encode("latin-1"))

def pdf_download_button(title, intro_lines, tables, filename):
    pdf_bytes = make_pdf(title, intro_lines, tables)
    st.download_button(
        "🧾 Download PDF",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
        use_container_width=True
    )

# -----------------------------
# UI Components
# -----------------------------
def kpi_card(label, value):
    st.markdown(
        f"""
        <div class="card">
            <div class="kpi-value">{value}</div>
            <div class="kpi-label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def low_stock_table():
    inv = list_items()
    if inv.empty:
        st.info("Inventory empty.")
        return
    inv["stock_qty"] = inv["stock_qty"].astype(float).fillna(0.0)
    inv["min_qty"] = inv["min_qty"].astype(float).fillna(0.0)
    low = inv[inv["stock_qty"] < inv["min_qty"]]
    if low.empty:
        st.success("✅ No low-stock alerts.")
        return
    st.markdown("#### ⚠️ Low Stock Alerts")
    st.dataframe(low[["item_id", "item_name", "category", "unit", "stock_qty", "min_qty"]], use_container_width=True)

# -----------------------------
# App start
# -----------------------------
bootstrap_files()

if "user" not in st.session_state:
    st.session_state.user = None

# -----------------------------
# Login screen
# -----------------------------
if st.session_state.user is None:
    st.markdown("<div class='app-title'>🛒 DailyShop Dairy</div>", unsafe_allow_html=True)
    st.markdown("<p class='muted' style='text-align:center;'>Manage inventory, sales, expenses & cash flow</p>", unsafe_allow_html=True)

    with st.form("login", clear_on_submit=False):
        mobile = st.text_input("📱 Mobile Number")
        password = st.text_input("🔑 Password", type="password")
        sub = st.form_submit_button("Login")
        if sub:
            user = authenticate(mobile.strip(), password)
            if user:
                st.session_state.user = user
                st.success(f"Welcome, {user['name']}!")
                st.rerun()
            else:
                st.error("Invalid mobile or password")
    st.caption("Tip: default admin → mobile: 9999999999 / password: admin123")
    st.stop()

# -----------------------------
# Top tabs (role-based)
# -----------------------------
user = st.session_state.user
colL, colR = st.columns([0.7, 0.3])
with colL:
    st.markdown("<div class='app-title'>🛒 DailyShop Dairy</div>", unsafe_allow_html=True)
with colR:
    st.write(f"**👤 {user['name']}**  ·  {user['role'].title()}")
    st.button("Logout", on_click=lambda: (st.session_state.update({"user": None}), st.rerun()))

tabs = ["📊 Dashboard", "📦 Inventory", "💰 Expenses", "🛒 Sales", "💵 Payments", "🧾 Reports"]
if user["role"] == "admin":
    tabs.append("👥 Users")

tab_objects = st.tabs(tabs)

# -----------------------------
# Tab: Dashboard
# -----------------------------
with tab_objects[0]:
    inv = list_items()
    exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    orders = load_csv(ORDERS_FILE, SCHEMA["orders"])
    pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"])

    # KPI metrics
    total_expenses = float(exp["amount"].sum()) if not exp.empty else 0.0
    total_sales = float(orders["total"].sum()) if not orders.empty else 0.0
    stock_value = float((inv["stock_qty"].astype(float) * inv["rate"].astype(float)).sum()) if not inv.empty else 0.0
    cust_balances = compute_customer_balances()
    pending_total = float(cust_balances["pending_balance"].sum()) if not cust_balances.empty else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Total Expenses", f"₹ {total_expenses:,.2f}")
    with c2: kpi_card("Total Sales", f"₹ {total_sales:,.2f}")
    with c3: kpi_card("Stock Value (Est.)", f"₹ {stock_value:,.2f}")
    with c4: kpi_card("Pending Customer Balances", f"₹ {pending_total:,.2f}")

    st.divider()
    low_stock_table()

# -----------------------------
# Tab: Inventory
# -----------------------------
with tab_objects[1]:
    st.subheader("Inventory Master")
    with st.expander("➕ Add / Update Item", expanded=True):
        inv = list_items()
        colA, colB, colC = st.columns([1.3, 1.2, 1.2])
        with colA:
            item_id = st.text_input("Item ID *")
            item_name = st.text_input("Item Name *")
            category = st.text_input("Category")
        with colB:
            unit = st.text_input("Unit (e.g., kg/pack)")
            rate = st.number_input("Rate (₹)", min_value=0.0, step=0.1, value=0.0)
            min_qty = st.number_input("Min Qty (alert below)", min_value=0.0, step=0.1, value=0.0)
        with colC:
            stock_qty = st.number_input("Current Stock Qty", min_value=0.0, step=0.1, value=0.0)
            st.caption("Note: Stock also changes via Purchases & Sales.")
            submit_item = st.button("💾 Save Item", use_container_width=True)
        if submit_item:
            if not item_id or not item_name:
                st.error("Item ID and Item Name are required.")
            else:
                upsert_inventory_item(item_id.strip(), item_name.strip(), category.strip(), unit.strip(), stock_qty, rate, min_qty)
                st.success("Item saved/updated.")
                st.experimental_rerun()

    st.markdown("#### Inventory List")
    st.dataframe(list_items(), use_container_width=True)

# -----------------------------
# Tab: Expenses (Purchases + Non-stock)
# -----------------------------
with tab_objects[2]:
    st.subheader("Expenses & Purchases")

    inv = list_items()
    items_options = {f"{r['item_name']} ({r['item_id']})": r["item_id"] for _, r in inv.iterrows()} if not inv.empty else {}

    col1, col2 = st.columns(2)

    # Purchases (Stock-In)
    with col1:
        st.markdown("**Purchase (Stock-In)**  <span class='pill'>Increases Stock</span>", unsafe_allow_html=True)
        with st.form("purchase_form", clear_on_submit=True):
            p_date = st.date_input("Date", datetime.now().date())
            p_item_label = st.selectbox("Item", options=["-- Select --"] + list(items_options.keys()))
            p_qty = st.number_input("Quantity", min_value=0.0, step=0.1)
            p_rate = st.number_input("Rate (₹)", min_value=0.0, step=0.1)
            p_category = st.text_input("Category", value="Purchase")
            p_remarks = st.text_input("Remarks", value="")
            s1 = st.form_submit_button("➕ Add Purchase")
        if s1:
            if p_item_label == "-- Select --":
                st.error("Select an item.")
            else:
                pid = items_options[p_item_label]
                item = get_item(pid)
                if not item:
                    st.error("Item not found.")
                else:
                    amount = round(p_qty * p_rate, 2)
                    ok, msg = adjust_stock(pid, p_qty)
                    if not ok:
                        st.error(msg)
                    else:
                        record_purchase_or_expense(
                            p_date, "Purchase", p_category, item["item_name"], pid, p_qty, p_rate, amount, user["user_id"], p_remarks
                        )
                        st.success(f"Purchase recorded. Stock increased by {p_qty}.")
                        st.experimental_rerun()

    # Non-stock Expenses
    with col2:
        st.markdown("**Expense (Non-Stock)**", unsafe_allow_html=True)
        with st.form("expense_form", clear_on_submit=True):
            e_date = st.date_input("Date ", datetime.now().date(), key="expense_date")
            e_category = st.text_input("Category (e.g., Rent, Utilities, Misc.)")
            e_item = st.text_input("Expense Title/Item")
            e_amount = st.number_input("Amount (₹)", min_value=0.0, step=0.1)
            e_remarks = st.text_input("Remarks", value="")
            s2 = st.form_submit_button("💾 Save Expense")
        if s2:
            record_purchase_or_expense(
                e_date, "Expense", e_category, e_item, "", 0.0, 0.0, e_amount, user["user_id"], e_remarks
            )
            st.success("Expense recorded.")

    st.divider()
    st.markdown("#### Recent Purchases & Expenses")
    exp_all = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    st.dataframe(exp_all.sort_values("date", ascending=False), use_container_width=True)
    make_downloadable_csv(exp_all, "Expenses")

# -----------------------------
# Tab: Sales
# -----------------------------
with tab_objects[3]:
    st.subheader("Sales / Orders")
    inv = list_items()
    items_options = {f"{r['item_name']} ({r['item_id']})": r["item_id"] for _, r in inv.iterrows()} if not inv.empty else {}

    # Build customer list from users (role=customer) + any customer_id ever used
    users_df = load_csv(USERS_FILE, SCHEMA["users"])
    cust_df = users_df[users_df["role"] == "customer"][["mobile", "name"]].rename(columns={"mobile": "customer_id"})
    known_custs = list(cust_df["customer_id"]) if not cust_df.empty else []
    orders_df = load_csv(ORDERS_FILE, SCHEMA["orders"])
    if not orders_df.empty:
        known_custs = sorted(list(set(known_custs + orders_df["customer_id"].dropna().astype(str).tolist())))
    cust_choice = st.selectbox("Customer (mobile)", options=["-- Enter manually --"] + known_custs)
    manual_cust = ""
    if cust_choice == "-- Enter manually --":
        manual_cust = st.text_input("Enter customer mobile *")

    with st.form("sales_form", clear_on_submit=True):
        s_date = st.date_input("Date", datetime.now().date())
        s_item_label = st.selectbox("Item *", options=["-- Select --"] + list(items_options.keys()))
        s_qty = st.number_input("Quantity *", min_value=0.0, step=0.1)
        s_rate_auto = st.checkbox("Use Item Rate", value=True)
        s_rate = st.number_input("Rate (₹)", min_value=0.0, step=0.1, disabled=s_rate_auto)
        s_payment = st.radio("Payment Mode", options=["Cash", "Credit"], horizontal=True)
        s_remarks = st.text_input("Remarks", value="")
        submit_sale = st.form_submit_button("🛒 Record Sale")

    if submit_sale:
        if s_item_label == "-- Select --":
            st.error("Select an item.")
        else:
            pid = items_options[s_item_label]
            item = get_item(pid)
            if not item:
                st.error("Item not found.")
            else:
                # rate
                rate = float(item["rate"]) if s_rate_auto else float(s_rate)
                total = round(s_qty * rate, 2)
                bal = total if s_payment == "Credit" else 0.0
                customer_id = manual_cust.strip() if cust_choice == "-- Enter manually --" else cust_choice
                if not customer_id:
                    st.error("Customer mobile is required (for both Cash and Credit).")
                else:
                    # reduce stock
                    ok, msg = adjust_stock(pid, -s_qty)
                    if not ok:
                        st.error(msg)
                    else:
                        record_order(
                            s_date, customer_id, pid, item["item_name"], s_qty, rate, total, s_payment, bal, user["user_id"], s_remarks
                        )
                        st.success(f"Sale recorded ({s_payment}). Stock decreased by {s_qty}.")
                        st.experimental_rerun()

    st.divider()
    st.markdown("#### Recent Sales")
    orders_all = load_csv(ORDERS_FILE, SCHEMA["orders"]).sort_values("date", ascending=False)
    st.dataframe(orders_all, use_container_width=True)
    make_downloadable_csv(orders_all, "Sales_Orders")

# -----------------------------
# Tab: Payments
# -----------------------------
with tab_objects[4]:
    st.subheader("Customer Payments / Settlements")
    balances = compute_customer_balances()
    if balances.empty:
        st.info("No credit sales yet.")
    else:
        st.dataframe(balances, use_container_width=True)

    customer_ids = balances["customer_id"].tolist() if not balances.empty else []
    with st.form("payment_form", clear_on_submit=True):
        p_date = st.date_input("Date", datetime.now().date())
        p_cust = st.selectbox("Customer (mobile)", options=["-- Select --"] + customer_ids)
        p_amount = st.number_input("Amount (₹)", min_value=0.0, step=0.1)
        p_mode = st.radio("Mode", options=["Cash", "UPI", "Card", "Other"], horizontal=True)
        p_remarks = st.text_input("Remarks", value="")
        submit_payment = st.form_submit_button("💵 Record Payment")
    if submit_payment:
        if p_cust == "-- Select --":
            st.error("Select a customer.")
        elif p_amount <= 0:
            st.error("Enter a valid amount.")
        else:
            record_payment(p_date, p_cust, p_amount, p_mode, p_remarks, user["user_id"])
            st.success("Payment recorded.")
            st.experimental_rerun()

    st.divider()
    st.markdown("#### Payment History")
    pays_all = load_csv(PAYMENTS_FILE, SCHEMA["payments"]).sort_values("date", ascending=False)
    st.dataframe(pays_all, use_container_width=True)
    make_downloadable_csv(pays_all, "Payments")

# -----------------------------
# Tab: Reports
# -----------------------------
with tab_objects[5]:
    st.subheader("Reports & Exports")

    # Filters
    today = datetime.now().date()
    default_start = today.replace(day=1)
    colf1, colf2, colf3 = st.columns([1.2, 1.2, 1.6])
    with colf1:
        start_date = st.date_input("Start date", default_start)
    with colf2:
        end_date = st.date_input("End date", today)
    with colf3:
        report_customer = st.text_input("Filter by Customer (mobile, optional)", value="")

    # Base data
    inv = list_items()
    exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    orders = load_csv(ORDERS_FILE, SCHEMA["orders"])
    pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
    balances = compute_customer_balances()

    exp_f = date_range_filter(exp, "date", start_date, end_date)
    ord_f = date_range_filter(orders, "date", start_date, end_date)
    pay_f = date_range_filter(pays, "date", start_date, end_date)

    if report_customer:
        ord_f = ord_f[ord_f["customer_id"].astype(str) == report_customer]
        pay_f = pay_f[pay_f["customer_id"].astype(str) == report_customer]

    # Summaries
    st.markdown("### 📈 Summary")
    colS1, colS2, colS3, colS4 = st.columns(4)
    with colS1: kpi_card("Expenses (range)", f"₹ {exp_f['amount'].sum():,.2f}" if not exp_f.empty else "₹ 0.00")
    with colS2: kpi_card("Sales (range)", f"₹ {ord_f['total'].sum():,.2f}" if not ord_f.empty else "₹ 0.00")
    with colS3:
        cash_sales = ord_f[ord_f["payment_mode"] == "Cash"]["total"].sum() if not ord_f.empty else 0.0
        kpi_card("Cash Sales (range)", f"₹ {cash_sales:,.2f}")
    with colS4:
        net_cash = cash_sales - (exp_f["amount"].sum() if not exp_f.empty else 0.0)
        kpi_card("Net Cash (Sales Cash - Expenses)", f"₹ {net_cash:,.2f}")

    st.markdown("### 🧮 Detailed Tables")
    st.markdown("**Expenses (filtered)**")
    st.dataframe(exp_f, use_container_width=True)
    make_downloadable_csv(exp_f, "Expenses_Filtered")

    st.markdown("**Sales (filtered)**")
    st.dataframe(ord_f, use_container_width=True)
    make_downloadable_csv(ord_f, "Sales_Filtered")

    st.markdown("**Payments (filtered)**")
    st.dataframe(pay_f, use_container_width=True)
    make_downloadable_csv(pay_f, "Payments_Filtered")

    st.markdown("**Customer Balances (overall)**")
    st.dataframe(balances, use_container_width=True)
    make_downloadable_csv(balances, "Customer_Balances")

    st.divider()
    st.markdown("### 📤 Export PDF")
    pdf_title = "DailyShop Dairy Report"
    intro = [
        f"Date Range: {start_date} to {end_date}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "All amounts in INR (₹)."
    ]
    tables = [
        ("Summary (Sales & Expenses)", pd.DataFrame({
            "Metric": ["Expenses (range)", "Sales (range)", "Cash Sales (range)", "Net Cash"],
            "Value": [
                f"₹ {exp_f['amount'].sum():,.2f}" if not exp_f.empty else "₹ 0.00",
                f"₹ {ord_f['total'].sum():,.2f}" if not ord_f.empty else "₹ 0.00",
                f"₹ {cash_sales:,.2f}",
                f"₹ {net_cash:,.2f}",
            ]
        })),
        ("Expenses (filtered)", exp_f),
        ("Sales (filtered)", ord_f),
        ("Payments (filtered)", pay_f),
        ("Customer Balances (overall)", balances),
    ]
    pdf_download_button(pdf_title, intro, tables, "dailyshop_report.pdf")

# -----------------------------
# Tab: Users (Admin only)
# -----------------------------
if user["role"] == "admin":
    with tab_objects[-1]:
        st.subheader("User Management (Admin)")
        users_df = load_csv(USERS_FILE, SCHEMA["users"])

        st.markdown("#### Existing Users")
        st.dataframe(users_df[["user_id", "name", "role", "mobile"]], use_container_width=True)

        st.divider()
        st.markdown("#### Add / Update User")
        colU1, colU2, colU3, colU4 = st.columns(4)
        with colU1:
            u_mobile = st.text_input("Mobile (login ID) *")
        with colU2:
            u_name = st.text_input("Full Name *")
        with colU3:
            u_role = st.selectbox("Role *", ["staff", "customer", "admin"])
        with colU4:
            u_password = st.text_input("Password *", type="password")

        c1, c2 = st.columns([0.2, 0.8])
        with c1:
            clicked = st.button("💾 Save User", use_container_width=True)
        if clicked:
            if not u_mobile or not u_name or not u_role or not u_password:
                st.error("All fields are required.")
            else:
                df = load_csv(USERS_FILE, SCHEMA["users"])
                exists = df[df["mobile"] == u_mobile]
                if exists.empty:
                    df.loc[len(df)] = [u_mobile, u_name, u_role, u_mobile, hash_password(u_password)]
                else:
                    idx = exists.index[0]
                    df.loc[idx, ["name", "role", "password_hash"]] = [u_name, u_role, hash_password(u_password)]
                save_csv(df, USERS_FILE)
                st.success("User saved/updated.")
                st.experimental_rerun()

        st.markdown("#### Reset Password")
        with st.form("reset_pw", clear_on_submit=True):
            r_mobile = st.text_input("User Mobile *")
            r_newpw = st.text_input("New Password *", type="password")
            r_submit = st.form_submit_button("Reset Password")
        if r_submit:
            df = load_csv(USERS_FILE, SCHEMA["users"])
            row = df[df["mobile"] == r_mobile]
            if row.empty:
                st.error("User not found.")
            else:
                idx = row.index[0]
                df.loc[idx, "password_hash"] = hash_password(r_newpw)
                save_csv(df, USERS_FILE)
                st.success("Password reset.")

        st.divider()
        st.markdown("#### Delete User")
        del_mobile = st.text_input("Mobile to delete")
        if st.button("🗑️ Delete", type="secondary"):
            if not del_mobile:
                st.error("Enter mobile to delete.")
            else:
                df = load_csv(USERS_FILE, SCHEMA["users"])
                df = df[df["mobile"] != del_mobile]
                save_csv(df, USERS_FILE)
                st.success("User deleted (if existed).")
                st.experimental_rerun()
