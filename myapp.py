# app.py — DailyShop Dairy (single-file)
# Requirements:
#   pip install streamlit pandas fpdf
# Run:
#   streamlit run app.py

import os
import uuid
from datetime import datetime, date
import pandas as pd
import streamlit as st
from fpdf import FPDF

# -----------------------
# Configuration
# -----------------------
APP_TITLE = "🛒 DailyShop Dairy"
DATA_DIR = "data"

USERS_CSV = os.path.join(DATA_DIR, "users.csv")
INVENTORY_CSV = os.path.join(DATA_DIR, "inventory.csv")
PURCHASES_CSV = os.path.join(DATA_DIR, "purchases.csv")
EXPENSES_CSV = os.path.join(DATA_DIR, "expenses.csv")
ORDERS_CSV = os.path.join(DATA_DIR, "orders.csv")
PAYMENTS_CSV = os.path.join(DATA_DIR, "payments.csv")

SCHEMA = {
    "users": ["user_id", "name", "mobile", "password", "role", "tab", "active"],
    "inventory": ["item_id", "item_name", "Area", "category", "unit", "stock_qty", "rate", "min_qty", "sell_price"],
    "purchases": ["purchase_id", "date", "item_id", "item_name", "category", "unit", "qty", "rate", "total", "remarks"],
    "expenses": ["expense_id", "date", "category", "item", "amount", "remarks"],
    "orders": ["order_id", "date", "customer_name", "mobile", "item_id", "item_name", "category", "qty", "price", "total", "payment_mode", "status"],
    "payments": ["payment_id", "date", "customer_name", "mobile", "amount", "remarks"]
}

st.set_page_config(page_title=APP_TITLE, layout="wide")

# -----------------------
# Helpers: file, csv
# -----------------------
def ensure_data_dir():
    if os.path.exists(DATA_DIR) and not os.path.isdir(DATA_DIR):
        try:
            os.remove(DATA_DIR)
        except Exception:
            pass
    os.makedirs(DATA_DIR, exist_ok=True)

def new_df(cols):
    return pd.DataFrame(columns=cols)

def load_csv(path, cols):
    """Load CSV and ensure required columns exist in returned DataFrame."""
    if not os.path.exists(path):
        df = new_df(cols)
        df.to_csv(path, index=False)
        return df[cols]
    try:
        df = pd.read_csv(path, dtype=str)
    except Exception:
        df = pd.read_csv(path, encoding="latin1", dtype=str)
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    # return in correct order and keep types as strings (coerce when needed)
    return df[cols]

def save_csv(df, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    # Ensure columns order if possible
    if isinstance(df, pd.DataFrame):
        df.to_csv(path, index=False, encoding="utf-8")
    else:
        raise ValueError("save_csv expects a DataFrame")

def make_id(prefix="ID"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

# -----------------------
# Bootstrap default files & default users.csv
# -----------------------
def bootstrap():
    ensure_data_dir()
    # create files if missing
    for key, cols in SCHEMA.items():
        path = {
            "users": USERS_CSV,
            "inventory": INVENTORY_CSV,
            "purchases": PURCHASES_CSV,
            "expenses": EXPENSES_CSV,
            "orders": ORDERS_CSV,
            "payments": PAYMENTS_CSV
        }[key]
        if not os.path.exists(path):
            save_csv(new_df(cols), path)
    # ensure default admin exists in users.csv
    users = load_csv(USERS_CSV, SCHEMA["users"])
    # if CSV empty or no active admin, add default admin
    has_admin = False
    if not users.empty:
        for _, r in users.iterrows():
            try:
                if str(r.get("role","")).strip().lower() == "admin" and str(r.get("active","")).strip().lower() in ("yes","true","1"):
                    has_admin = True
                    break
            except Exception:
                continue
    if not has_admin:
        # default admin credentials stored in CSV (change here if required)
        default_admin = {
            "user_id": "UADMIN",
            "name": "Administrator",
            "mobile": "admin",        # login id (string). Change to numeric like '9999999999' if you want.
            "password": "admin",      # plaintext password (as requested) — consider hashing for production
            "role": "admin",
            "tab": "all",
            "active": "yes"
        }
        users = pd.concat([users, pd.DataFrame([default_admin])], ignore_index=True)
        save_csv(users, USERS_CSV)
    # done

bootstrap()

# -----------------------
# Authentication & session
# -----------------------
def init_users_df():
    return load_csv(USERS_CSV, SCHEMA["users"])

def authenticate(mobile, password):
    users = init_users_df()
    if users.empty:
        return None
    users_local = users.fillna("")
    matched = users_local[
        (users_local["mobile"].astype(str) == str(mobile)) &
        (users_local["password"].astype(str) == str(password)) &
        (users_local["active"].astype(str).str.lower().isin(["yes", "true", "1"]))
    ]
    if not matched.empty:
        return matched.iloc[0].to_dict()
    return None

# -----------------------
# Business functions
# -----------------------
def list_inventory():
    inv = load_csv(INVENTORY_CSV, SCHEMA["inventory"]).copy()
    for c in ["stock_qty", "rate", "min_qty", "sell_price"]:
        if c in inv.columns:
            inv[c] = pd.to_numeric(inv[c], errors="coerce").fillna(0)
    return inv

def save_inventory(df):
    # ensure sell_price integer rounding to nearest 5
    df = df.copy()
    if "sell_price" in df.columns:
        df["sell_price"] = pd.to_numeric(df["sell_price"], errors="coerce").fillna(0).astype(float)
        df["sell_price"] = ( (df["sell_price"] / 5.0).round() * 5 ).astype(int)
    # ensure numeric columns saved as is
    save_csv(df[SCHEMA["inventory"]], INVENTORY_CSV)

def upsert_inventory(item_id, item_name, category, unit, stock_qty, rate, min_qty, sell_price=None):
    inv = list_inventory()
    if item_id == "" or item_id is None:
        item_id = make_id("IT")
    exists = inv[inv["item_id"].astype(str) == str(item_id)]
    if exists.empty:
        newrow = {
            "item_id": item_id,
            "item_name": item_name,
            "Area": "",
            "category": category,
            "unit": unit,
            "stock_qty": float(stock_qty or 0),
            "rate": float(rate or 0),
            "min_qty": float(min_qty or 0),
            "sell_price": int(sell_price) if sell_price is not None else int(round((float(rate or 0)/1.0)/5.0)*5)
        }
        inv = pd.concat([inv, pd.DataFrame([newrow])], ignore_index=True)
    else:
        idx = exists.index[0]
        inv.loc[idx, ["item_name","category","unit","stock_qty","rate","min_qty"]] = [
            item_name, category, unit, float(stock_qty or 0), float(rate or 0), float(min_qty or 0)
        ]
        if sell_price is not None:
            inv.loc[idx, "sell_price"] = int(sell_price)
    save_inventory(inv)

def adjust_stock(item_id, delta):
    inv = list_inventory()
    row = inv[inv["item_id"].astype(str) == str(item_id)]
    if row.empty:
        return False, "Item not found"
    idx = row.index[0]
    cur = float(inv.loc[idx, "stock_qty"])
    new = cur + float(delta)
    if new < 0:
        return False, "Insufficient stock"
    inv.loc[idx, "stock_qty"] = new
    save_inventory(inv)
    return True, new

def record_purchase(date_, category, item_name, item_id, qty, rate, remarks=""):
    df = load_csv(PURCHASES_CSV, SCHEMA["purchases"])
    total = round(float(qty)*float(rate),2)
    df.loc[len(df)] = [make_id("PUR"), date_.isoformat() if isinstance(date_,date) else str(date_), item_id, item_name, category, "", float(qty), float(rate), total, remarks]
    save_csv(df, PURCHASES_CSV)
    ok, new = adjust_stock(item_id, float(qty))
    return ok, new

def record_expense(date_, category, item, amount, remarks=""):
    df = load_csv(EXPENSES_CSV, SCHEMA["expenses"])
    df.loc[len(df)] = [make_id("EXP"), date_.isoformat() if isinstance(date_,date) else str(date_), category, item, float(amount), remarks]
    save_csv(df, EXPENSES_CSV)

def record_order(date_, customer_name, mobile, item_id, item_name, qty, price, payment_mode, status="Confirmed"):
    df = load_csv(ORDERS_CSV, SCHEMA["orders"])
    total = round(float(qty)*float(price),2)
    df.loc[len(df)] = [make_id("ORD"), date_.isoformat() if isinstance(date_,date) else str(date_), customer_name, mobile, item_id, item_name, "", float(qty), float(price), total, payment_mode, status]
    save_csv(df, ORDERS_CSV)
    ok, new = adjust_stock(item_id, -float(qty))
    return ok, new

def record_payment(date_, customer_name, mobile, amount, remarks=""):
    df = load_csv(PAYMENTS_CSV, SCHEMA["payments"])
    df.loc[len(df)] = [make_id("PAY"), date_.isoformat() if isinstance(date_,date) else str(date_), customer_name, mobile, float(amount), remarks]
    save_csv(df, PAYMENTS_CSV)

def compute_customer_balances():
    orders = load_csv(ORDERS_CSV, SCHEMA["orders"])
    pays = load_csv(PAYMENTS_CSV, SCHEMA["payments"])
    if orders.empty and pays.empty:
        return new_df := pd.DataFrame(columns=["mobile","customer_name","credit_sales_total","payments_total","pending_balance"])
    # credit orders only
    orders["total"] = pd.to_numeric(orders["total"], errors="coerce").fillna(0)
    cred = orders[orders["payment_mode"].astype(str).str.lower() == "credit"].copy()
    credit_sum = cred.groupby(["mobile","customer_name"])["total"].sum().reset_index().rename(columns={"total":"credit_sales_total"})
    pays["amount"] = pd.to_numeric(pays["amount"], errors="coerce").fillna(0)
    pay_sum = pays.groupby(["mobile","customer_name"])["amount"].sum().reset_index().rename(columns={"amount":"payments_total"})
    df = pd.merge(credit_sum, pay_sum, on=["mobile","customer_name"], how="outer").fillna(0)
    df["pending_balance"] = df["credit_sales_total"] - df["payments_total"]
    return df.sort_values("pending_balance", ascending=False)

# -----------------------
# Exports
# -----------------------
def df_to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")

def df_to_pdf_bytes(title, df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 8, txt=title, ln=True)
    pdf.ln(2)
    if df.empty:
        pdf.cell(0,6,"No data",ln=True)
        return pdf.output(dest="S").encode("latin1","ignore")
    cols = list(df.columns)[:8]
    colw = (pdf.w - 20) / max(len(cols), 1)
    for c in cols:
        pdf.cell(colw, 7, str(c)[:20], border=1)
    pdf.ln()
    for _, row in df.iterrows():
        for c in cols:
            text = str(row.get(c,""))
            safe = text.encode("latin1", "replace").decode("latin1")
            pdf.cell(colw, 6, safe[:22], border=1)
        pdf.ln()
    return pdf.output(dest="S").encode("latin1","ignore")

# -----------------------
# UI helpers
# -----------------------
def kpi_card(label, value):
    st.markdown(f"""
    <div style="background:#fff;padding:12px;border-radius:10px;box-shadow:0 6px 18px rgba(0,0,0,0.06);">
      <div style="font-weight:700;font-size:20px">{value}</div>
      <div style="color:#64748b">{label}</div>
    </div>
    """, unsafe_allow_html=True)

def csv_download(df, label):
    if df.empty:
        st.warning("No data to export.")
        return
    st.download_button(f"⬇ Download {label} (CSV)", data=df_to_csv_bytes(df), file_name=f"{label.replace(' ','_')}.csv", mime="text/csv")

# -----------------------
# UI: Login & main app
# -----------------------
if "user" not in st.session_state:
    st.session_state.user = None

def login_page():
    st.markdown(f"<h2 style='text-align:center;color:#111111'>{APP_TITLE}</h2>", unsafe_allow_html=True)
    st.write("Login (default admin created automatically on first run).")
    with st.form("login_form"):
        mobile = st.text_input("Mobile / ID", value="")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            user = authenticate(mobile, password)
            if user:
                st.session_state.user = user
                st.success(f"Welcome {user.get('name', user.get('mobile'))} ({user.get('role')})")
                st.experimental_rerun()
            else:
                st.error("Invalid credentials or inactive user.")

# Main UI functions for each tab (top tabs)
def ui_dashboard():
    st.markdown("### 📊 Dashboard")
    inv = list_inventory()
    exp = load_csv(EXPENSES_CSV, SCHEMA["expenses"])
    orders = load_csv(ORDERS_CSV, SCHEMA["orders"])
    pays = load_csv(PAYMENTS_CSV, SCHEMA["payments"])

    total_exp = exp["amount"].astype(float).sum() if not exp.empty else 0.0
    total_sales = orders["total"].astype(float).sum() if not orders.empty else 0.0
    stock_val = (inv["stock_qty"] * inv["rate"]).sum() if not inv.empty else 0.0
    balances = compute_customer_balances()
    pending_total = balances["pending_balance"].sum() if (not balances.empty) and ("pending_balance" in balances.columns) else 0.0

    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi_card("Total Expenses", f"₹ {total_exp:,.2f}")
    with c2: kpi_card("Total Sales", f"₹ {total_sales:,.2f}")
    with c3: kpi_card("Stock Value (Est.)", f"₹ {stock_val:,.2f}")
    with c4: kpi_card("Pending Balances", f"₹ {pending_total:,.2f}")

    st.markdown("#### Low stock items")
    low = inv[inv["stock_qty"] < inv["min_qty"]]
    if low.empty:
        st.info("No low-stock items.")
    else:
        st.dataframe(low[["item_id","item_name","stock_qty","min_qty","sell_price"]])

def ui_inventory():
    st.header("📦 Inventory")
    inv = list_inventory()
    if "DELETE" not in inv.columns:
        inv["DELETE"] = False
    edited = st.data_editor(inv, key="inv_editor", num_rows="dynamic", use_container_width=True)
    c1,c2 = st.columns([1,1])
    with c1:
        if st.button("Save Inventory"):
            try:
                # remove rows marked DELETE
                ed = edited.copy()
                if "DELETE" in ed.columns:
                    ed["DELETE"] = ed["DELETE"].fillna(False).astype(bool)
                    ed = ed[~ed["DELETE"]].drop(columns=["DELETE"])
                # ensure numeric
                for c in ["stock_qty","rate","min_qty","sell_price"]:
                    if c in ed.columns:
                        ed[c] = pd.to_numeric(ed[c], errors="coerce").fillna(0)
                save_inventory(ed)
                st.success("Inventory saved.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Failed saving inventory: {e}")
    with c2:
        st.download_button("Download Inventory CSV", data=df_to_csv_bytes(inv), file_name="inventory.csv", mime="text/csv")
        if st.button("Export Inventory PDF"):
            pdfb = df_to_pdf_bytes("Inventory", inv)
            st.download_button("Download PDF", data=pdfb, file_name="inventory.pdf", mime="application/pdf")

    st.markdown("### Add / Update Item")
    with st.form("add_item", clear_on_submit=True):
        item_id = st.text_input("Item ID (leave blank to auto-generate)")
        item_name = st.text_input("Item Name")
        category = st.text_input("Category", value="Menu")
        unit = st.text_input("Unit (kg/pcs)")
        stock_qty = st.number_input("Stock Qty", min_value=0.0, step=0.1)
        rate = st.number_input("Rate (purchase)", min_value=0.0, step=0.1)
        min_qty = st.number_input("Min Qty (alert)", min_value=0.0, step=0.1)
        sell_price = st.number_input("Sell Price (₹)", min_value=0, step=1, value=int(rate))
        if st.form_submit_button("Save Item"):
            if not item_name:
                st.error("Item name required")
            else:
                upsert_inventory(item_id, item_name, category, unit, stock_qty, rate, min_qty, sell_price)
                st.success("Item added/updated.")
                st.experimental_rerun()

def ui_purchases_expenses():
    st.header("🧾 Purchases & Expenses")
    inv = list_inventory()
    # Purchase form
    st.subheader("Purchase (Stock-in)")
    with st.form("purchase_form", clear_on_submit=True):
        p_date = st.date_input("Date", datetime.now().date())
        item = st.selectbox("Item", options=["-- Select --"] + [f"{r.item_name} ({r.item_id})" for _, r in inv.iterrows()]) if not inv.empty else st.text_input("Item name")
        qty = st.number_input("Quantity", min_value=0.0, step=0.1)
        rate = st.number_input("Rate (₹)", min_value=0.0, step=0.1)
        remarks = st.text_input("Remarks")
        if st.form_submit_button("Record Purchase"):
            if item == "-- Select --" and inv.empty:
                st.error("Please add the item first in inventory")
            else:
                if inv.empty:
                    # no inventory, just record as purchase (item id blank)
                    item_id = ""
                    item_name = item
                else:
                    item_id = item.split("(")[-1].replace(")","").strip()
                    item_name = item.split("(")[0].strip()
                ok, res = record_purchase(p_date, "Purchase", item_name, item_id, qty, rate, remarks=remarks)
                if ok:
                    st.success(f"Purchase recorded; stock updated (new stock: {res})")
                else:
                    st.error(res)
                st.experimental_rerun()

    st.subheader("Expense (non-stock)")
    with st.form("expense_form", clear_on_submit=True):
        e_date = st.date_input("Date", datetime.now().date())
        e_cat = st.text_input("Category")
        e_item = st.text_input("Expense Item")
        e_amt = st.number_input("Amount (₹)", min_value=0.0, step=0.1)
        e_rem = st.text_input("Remarks")
        if st.form_submit_button("Record Expense"):
            if e_amt <= 0:
                st.error("Amount must be > 0")
            else:
                record_expense(e_date, e_cat, e_item, e_amt, remarks=e_rem)
                st.success("Expense recorded.")
                st.experimental_rerun()

    st.markdown("#### Recent Purchases")
    purch = load_csv(PURCHASES_CSV, SCHEMA["purchases"]).sort_values("date", ascending=False)
    st.dataframe(purch.head(50))
    csv_download(purch, "purchases")

    st.markdown("#### Recent Expenses")
    ex = load_csv(EXPENSES_CSV, SCHEMA["expenses"]).sort_values("date", ascending=False)
    st.dataframe(ex.head(50))
    csv_download(ex, "expenses")

def ui_sales_orders():
    st.header("🛒 Sales / Orders (Menu)")
    inv = list_inventory()
    menu_items = inv.copy()
    if menu_items.empty:
        st.info("No inventory items available.")
    else:
        menu_items = menu_items[menu_items["category"].astype(str).str.lower() == "menu"] if "category" in menu_items.columns else menu_items
    all_items = menu_items if not menu_items.empty else inv
    item_options = [f"{r.item_name} ({r.item_id})" for _, r in all_items.iterrows()] if not all_items.empty else []
    with st.form("sales_form", clear_on_submit=True):
        s_date = st.date_input("Date", datetime.now().date())
        s_customer = st.text_input("Customer name (Guest for cash)")
        s_mobile = st.text_input("Customer mobile (required for credit)")
        s_item = st.selectbox("Item", options=["-- Select --"] + item_options) if item_options else st.text_input("Item name")
        s_qty = st.number_input("Qty", min_value=0.0, step=0.1, value=1.0)
        s_price = st.number_input("Price (₹)", min_value=0.0, step=1.0, value=0.0)
        s_payment = st.radio("Payment mode", ["Cash","Credit"], horizontal=True)
        s_rem = st.text_input("Remarks")
        if st.form_submit_button("Place Order"):
            if (s_item == "-- Select --" or s_item=="") and not item_options:
                st.error("Select or enter an item.")
            else:
                if s_payment.lower() == "credit" and (not s_mobile):
                    st.error("Credit requires customer mobile.")
                else:
                    if item_options:
                        sel_id = s_item.split("(")[-1].replace(")","").strip()
                        sel_name = s_item.split("(")[0].strip()
                    else:
                        sel_id = ""
                        sel_name = s_item
                    ok, res = record_order(s_date, s_customer or "Guest", s_mobile or "", sel_id, sel_name, s_qty, s_price, s_payment)
                    if ok:
                        st.success("Order recorded and stock updated.")
                    else:
                        st.error(res)
                    st.experimental_rerun()

    st.markdown("#### Recent Orders")
    ords = load_csv(ORDERS_CSV, SCHEMA["orders"]).sort_values("date", ascending=False)
    st.dataframe(ords.head(50))
    csv_download(ords, "orders")

def ui_payments():
    st.header("💵 Payments")
    balances = compute_customer_balances()
    st.markdown("#### Customer Balances")
    st.dataframe(balances if not balances.empty else pd.DataFrame(columns=["mobile","customer_name","credit_sales_total","payments_total","pending_balance"]))
    st.markdown("#### Record Payment")
    with st.form("payment_form", clear_on_submit=True):
        p_date = st.date_input("Date", datetime.now().date())
        p_name = st.text_input("Customer name")
        p_mobile = st.text_input("Customer mobile")
        p_amt = st.number_input("Amount", min_value=0.0, step=0.1)
        p_rem = st.text_input("Remarks")
        if st.form_submit_button("Record Payment"):
            if p_amt <= 0 or not p_mobile:
                st.error("Customer mobile and positive amount required.")
            else:
                record_payment(p_date, p_name or p_mobile, p_mobile, p_amt, remarks=p_rem)
                st.success("Payment recorded.")
                st.experimental_rerun()
    st.markdown("#### Payment History")
    ph = load_csv(PAYMENTS_CSV, SCHEMA["payments"]).sort_values("date", ascending=False)
    st.dataframe(ph.head(50))
    csv_download(ph, "payments")

def ui_reports():
    st.header("📈 Reports & Exports")
    today = date.today()
    start_date = st.date_input("Start date", today.replace(day=1))
    end_date = st.date_input("End date", today)
    exp = load_csv(EXPENSES_CSV, SCHEMA["expenses"])
    ords = load_csv(ORDERS_CSV, SCHEMA["orders"])
    pays = load_csv(PAYMENTS_CSV, SCHEMA["payments"])
    def filter_by_date(df, col="date"):
        if df.empty: return df
        df2 = df.copy()
        df2[col] = pd.to_datetime(df2[col], errors="coerce").dt.date
        return df2[(df2[col] >= start_date) & (df2[col] <= end_date)]
    exp_f = filter_by_date(exp)
    ord_f = filter_by_date(ords)
    pay_f = filter_by_date(pays)
    total_exp = exp_f["amount"].astype(float).sum() if not exp_f.empty else 0.0
    total_sales = ord_f["total"].astype(float).sum() if not ord_f.empty else 0.0
    cash_sales = ord_f[ord_f["payment_mode"].astype(str).str.lower()=="cash"]["total"].astype(float).sum() if not ord_f.empty else 0.0
    net_cash = cash_sales - total_exp
    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi_card("Expenses (range)", f"₹ {total_exp:,.2f}")
    with c2: kpi_card("Sales (range)", f"₹ {total_sales:,.2f}")
    with c3: kpi_card("Cash Sales (range)", f"₹ {cash_sales:,.2f}")
    with c4: kpi_card("Net Cash", f"₹ {net_cash:,.2f}")
    st.markdown("#### Filtered Expenses"); st.dataframe(exp_f)
    csv_download(exp_f, "expenses_filtered")
    st.markdown("#### Filtered Sales"); st.dataframe(ord_f)
    csv_download(ord_f, "sales_filtered")
    st.markdown("#### Filtered Payments"); st.dataframe(pay_f)
    csv_download(pay_f, "payments_filtered")
    st.markdown("#### Customer Balances (all)")
    csv_download(compute_customer_balances(), "customer_balances_all")
    if st.button("Export Summary PDF"):
        summary = pd.DataFrame({
            "Metric":["Expenses (range)","Sales (range)","Cash Sales","Net Cash"],
            "Value":[f"₹ {total_exp:,.2f}", f"₹ {total_sales:,.2f}", f"₹ {cash_sales:,.2f}", f"₹ {net_cash:,.2f}"]
        })
        pdfb = df_to_pdf_bytes("DailyShop Summary", summary)
        st.download_button("Download PDF", data=pdfb, file_name="summary.pdf", mime="application/pdf")

def ui_users():
    st.header("👥 User Management (Admin)")
    users = load_csv(USERS_CSV, SCHEMA["users"])
    st.markdown("#### Current Users")
    st.dataframe(users[["user_id","name","mobile","role","active"]].fillna(""))
    st.markdown("#### Add / Update User")
    with st.form("add_user", clear_on_submit=True):
        u_id = st.text_input("User ID (unique)")
        u_name = st.text_input("Full name")
        u_mobile = st.text_input("Mobile / login")
        u_pass = st.text_input("Password")
        u_role = st.selectbox("Role", ["admin","staff","customer"])
        u_active = st.selectbox("Active", ["yes","no"])
        if st.form_submit_button("Save User"):
            if not u_mobile or not u_pass or not u_name or not u_id:
                st.error("All fields required.")
            else:
                # upsert
                users = load_csv(USERS_CSV, SCHEMA["users"])
                exists = users[users["user_id"].astype(str) == str(u_id)]
                if exists.empty:
                    users.loc[len(users)] = [u_id, u_name, u_mobile, u_pass, u_role, "all", u_active]
                else:
                    idx = exists.index[0]
                    users.loc[idx, ["name","mobile","password","role","active"]] = [u_name, u_mobile, u_pass, u_role, u_active]
                save_csv(users, USERS_CSV)
                st.success("User saved.")
                st.experimental_rerun()
    st.markdown("#### Reset Page / Admin Reset")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("Reset Current Page (all users)"):
            st.experimental_rerun()
    with c2:
        if st.button("Admin: Clear last-tab memory & logout"):
            st.session_state.clear()
            st.experimental_rerun()

# -----------------------
# App entrypoint
# -----------------------
def main():
    if st.session_state.get("user") is None:
        login_page()
        return

    user = st.session_state.user
    role = str(user.get("role","")).strip().lower()

    # Build top tabs by role
    if role == "admin":
        tabs = ["Dashboard","Inventory","Purchases & Expenses","Sales/Orders","Payments","Reports","Users"]
    elif role == "staff":
        tabs = ["Dashboard","Inventory","Purchases & Expenses","Sales/Orders","Payments","Reports"]
    elif role == "customer":
        tabs = ["Dashboard","Sales/Orders","Payments"]
    else:
        tabs = ["Dashboard"]

    tab_objs = st.tabs(tabs)
    for i, key in enumerate(tabs):
        with tab_objs[i]:
            if key == "Dashboard":
                ui_dashboard()
            elif key == "Inventory":
                ui_inventory()
            elif key == "Purchases & Expenses":
                ui_purchases_expenses()
            elif key == "Sales/Orders":
                ui_sales_orders()
            elif key == "Payments":
                ui_payments()
            elif key == "Reports":
                ui_reports()
            elif key == "Users":
                ui_users()

# show header + run
if st.session_state.get("user") is None:
    login_page()
else:
    # show header with logout
    left, right = st.columns([0.8, 0.2])
    with left:
        st.markdown(f"## {APP_TITLE}")
    with right:
        u = st.session_state.user
        st.markdown(f"**{u.get('name',u.get('mobile'))}**  ·  {u.get('role')}")
        if st.button("Logout"):
            st.session_state.user = None
            st.experimental_rerun()
    main()
