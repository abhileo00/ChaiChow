# app.py — DailyShop Dairy (single-file)
# Requirements:
#   pip install streamlit pandas fpdf
# Run:
#   streamlit run app.py

import os
import hashlib
import re
from datetime import datetime, date, timedelta
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
    # added selling_price (integer / multiples of 5)
    "inventory": ["item_id", "item_name", "category", "unit", "stock_qty", "rate", "selling_price", "min_qty"],
    # added selling_price to orders
    "orders": ["date", "customer_id", "item_id", "item_name", "qty", "rate", "selling_price", "total", "payment_mode", "balance", "user_id", "remarks"],
    "expenses": ["date", "type", "category", "item", "item_id", "qty", "rate", "amount", "user_id", "remarks"],
    "payments": ["date", "customer_id", "amount", "mode", "remarks", "user_id"],
}

st.set_page_config(page_title="DailyShop Dairy", layout="wide")

# -----------------------
# Utility functions
# -----------------------
def safe_make_data_dir():
    if os.path.exists(DATA_DIR) and not os.path.isdir(DATA_DIR):
        try:
            os.remove(DATA_DIR)
        except Exception:
            pass
    os.makedirs(DATA_DIR, exist_ok=True)

def new_df(cols): return pd.DataFrame(columns=cols)

def load_csv(path, cols):
    # returns DataFrame with all cols in cols list (creates missing columns)
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, dtype=str)
        except Exception:
            df = pd.read_csv(path, encoding="latin1", dtype=str)
        for c in cols:
            if c not in df.columns:
                df[c] = None
        # keep columns in order requested
        return df[cols]
    return new_df(cols)

def save_csv(df, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")

def hash_pw(pw: str) -> str:
    return hashlib.sha256(str(pw).encode("utf-8")).hexdigest()

def check_pw(raw: str, hashed: str) -> bool:
    return hash_pw(raw) == hashed

# -----------------------
# Bootstrap files & default admin
# -----------------------
def bootstrap_files():
    safe_make_data_dir()
    if not os.path.exists(USERS_FILE):
        admin = pd.DataFrame([{
            "user_id": "admin",
            "name": "Master Admin",
            "role": "admin",
            "mobile": "9999999999",
            "password_hash": hash_pw("admin123")
        }], columns=SCHEMA["users"])
        save_csv(admin, USERS_FILE)
    for f, cols in [(INVENTORY_FILE, SCHEMA["inventory"]),
                    (EXPENSES_FILE, SCHEMA["expenses"]),
                    (ORDERS_FILE, SCHEMA["orders"]),
                    (PAYMENTS_FILE, SCHEMA["payments"])]:
        if not os.path.exists(f):
            # create an empty csv with the required header
            save_csv(new_df(cols), f)

bootstrap_files()

# -----------------------
# Business functions
# -----------------------
def get_user_by_mobile(mobile):
    users = load_csv(USERS_FILE, SCHEMA["users"])
    row = users[users["mobile"].astype(str) == str(mobile)]
    return row.iloc[0].to_dict() if not row.empty else None

def create_or_update_user(user_id, name, role, mobile, password):
    users = load_csv(USERS_FILE, SCHEMA["users"])
    exists = users[users["mobile"].astype(str) == str(mobile)]
    pwdhash = hash_pw(password)
    if exists.empty:
        users.loc[len(users)] = [user_id, name, role, mobile, pwdhash]
    else:
        idx = exists.index[0]
        users.loc[idx, ["name", "role", "mobile", "password_hash"]] = [name, role, mobile, pwdhash]
    save_csv(users, USERS_FILE)

def list_inventory():
    inv = load_csv(INVENTORY_FILE, SCHEMA["inventory"])
    # coerce numeric cols
    inv["stock_qty"] = pd.to_numeric(inv.get("stock_qty", 0), errors="coerce").fillna(0.0)
    inv["rate"] = pd.to_numeric(inv.get("rate", 0), errors="coerce").fillna(0.0)
    # selling_price integers, multiples of 5 - store as int
    inv["selling_price"] = pd.to_numeric(inv.get("selling_price", 0), errors="coerce").fillna(0).astype(int)
    inv["min_qty"] = pd.to_numeric(inv.get("min_qty", 0), errors="coerce").fillna(0.0)
    # ensure types consistent as strings for display elsewhere
    for c in ["item_id", "item_name", "category", "unit"]:
        if c not in inv.columns:
            inv[c] = ""
    return inv

def upsert_inventory(item_id, item_name, category, unit, stock_qty, rate, selling_price, min_qty):
    inv = list_inventory()
    exists = inv[inv["item_id"].astype(str) == str(item_id)]
    # ensure numeric conversion
    stock_qty = float(stock_qty or 0)
    rate = float(rate or 0)
    selling_price = int(float(selling_price or 0))
    min_qty = float(min_qty or 0)
    if exists.empty:
        inv.loc[len(inv)] = [item_id, item_name, category, unit, stock_qty, rate, selling_price, min_qty]
    else:
        idx = exists.index[0]
        inv.loc[idx, ["item_name","category","unit","stock_qty","rate","selling_price","min_qty"]] = [item_name, category, unit, stock_qty, rate, selling_price, min_qty]
    save_csv(inv, INVENTORY_FILE)

def delete_inventory(item_id):
    inv = list_inventory()
    inv = inv[inv["item_id"].astype(str) != str(item_id)]
    save_csv(inv, INVENTORY_FILE)

def adjust_stock(item_id, delta):
    inv = list_inventory()
    row = inv[inv["item_id"].astype(str) == str(item_id)]
    if row.empty:
        return False, "Item not found"
    idx = row.index[0]
    current = float(inv.loc[idx,"stock_qty"] or 0)
    new = current + float(delta)
    if new < 0:
        return False, "Insufficient stock"
    inv.loc[idx, "stock_qty"] = new
    save_csv(inv, INVENTORY_FILE)
    return True, new

def record_expense(dt, category, item, amount, user_id="", remarks=""):
    df = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    df.loc[len(df)] = [dt.isoformat() if isinstance(dt, (date, datetime)) else str(dt), "Expense", category, item, "", 0.0, 0.0, float(amount or 0.0), user_id, remarks]
    save_csv(df, EXPENSES_FILE)

def record_purchase(dt, category, item_name, item_id, qty, rate, user_id="", remarks=""):
    amount = round(float(qty) * float(rate), 2)
    df = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    df.loc[len(df)] = [dt.isoformat() if isinstance(dt, (date, datetime)) else str(dt), "Purchase", category, item_name, item_id, qty, rate, amount, user_id, remarks]
    save_csv(df, EXPENSES_FILE)
    ok, val = adjust_stock(item_id, qty)
    return ok, val

def record_order(dt, customer_id, item_id, item_name, qty, rate, selling_price, payment_mode, user_id="", remarks=""):
    # ensure selling_price and rate are numeric ints
    qty = float(qty)
    selling_price = int(float(selling_price))
    rate = float(rate)
    total = round(qty * selling_price, 2)
    balance = total if str(payment_mode).strip().lower() == "credit" else 0.0
    df = load_csv(ORDERS_FILE, SCHEMA["orders"])
    df.loc[len(df)] = [dt.isoformat() if isinstance(dt, (date, datetime)) else str(dt), customer_id, item_id, item_name, qty, rate, selling_price, total, payment_mode, balance, user_id, remarks]
    save_csv(df, ORDERS_FILE)
    ok, new = adjust_stock(item_id, -qty)
    return ok, new

def record_payment(dt, customer_id, amount, mode, remarks="", user_id=""):
    df = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
    df.loc[len(df)] = [dt.isoformat() if isinstance(dt, (date, datetime)) else str(dt), customer_id, float(amount), mode, remarks, user_id]
    save_csv(df, PAYMENTS_FILE)

def compute_customer_balances():
    orders = load_csv(ORDERS_FILE, SCHEMA["orders"])
    payments = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
    if (orders.empty or "payment_mode" not in orders.columns) and payments.empty:
        return new_df(["customer_id","credit_sales_total","payments_total","pending_balance"])
    # consider only credit orders
    if "payment_mode" in orders.columns:
        credits = orders[orders["payment_mode"].astype(str).str.lower() == "credit"].copy()
    else:
        credits = orders.copy()
    credits["total"] = pd.to_numeric(credits.get("total", 0), errors="coerce").fillna(0.0)
    credit_sum = credits.groupby("customer_id")["total"].sum().rename("credit_sales_total")
    payments["amount"] = pd.to_numeric(payments.get("amount", 0), errors="coerce").fillna(0.0)
    pay_sum = payments.groupby("customer_id")["amount"].sum().rename("payments_total")
    df = pd.concat([credit_sum, pay_sum], axis=1).fillna(0.0)
    df["pending_balance"] = df["credit_sales_total"] - df["payments_total"]
    out = df.reset_index().rename(columns={"index":"customer_id"})
    return out.sort_values("pending_balance", ascending=False)

# -----------------------
# Exports (CSV/PDF)
# -----------------------
def csv_download(df, label):
    if df.empty:
        st.warning("No data to export.")
        return
    st.download_button(f"⬇ Download {label} (CSV)", data=df.to_csv(index=False).encode("utf-8"), file_name=f"{label.replace(' ','_')}.csv", mime="text/csv")

def make_pdf_bytes(title, df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 8, txt=title, ln=True)
    pdf.ln(2)
    if df.empty:
        pdf.cell(0,6,"No data",ln=True)
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

# -----------------------
# UI / Pages
# -----------------------
if "user" not in st.session_state:
    st.session_state.user = None

# session to hold editing state for inventory
if "editing_item" not in st.session_state:
    st.session_state.editing_item = None
if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = None

def login_page():
    st.markdown(f"<h2 style='text-align:center;color:#2563EB'>{APP_TITLE}</h2>", unsafe_allow_html=True)
    st.write("Login with mobile and password (first-time use: default Master Admin).")
    with st.form("login_form"):
        mobile = st.text_input("📱 Mobile", value="")
        password = st.text_input("🔒 Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            user = get_user_by_mobile(mobile)
            if user and check_pw(password, user["password_hash"]):
                st.session_state.user = user
                st.success(f"Welcome {user['name']}!")
                st.rerun()
            else:
                st.error("Invalid mobile or password")

def render_inventory_table(inv):
    st.markdown("#### Inventory List (Edit here)")
    # Build a display table but add Edit/Delete buttons per row
    # We'll show a header
    cols = ["item_id","item_name","category","unit","stock_qty","rate","selling_price","min_qty"]
    header_cols = st.columns([1.2,2,1.2,1,1,1,1,1,0.8])
    header_titles = ["Item ID","Item Name","Category","Unit","Stock","Rate (₹)","Sell Price (₹)","Min Qty","Actions"]
    for hc, t in zip(header_cols, header_titles):
        hc.markdown(f"**{t}**")
    # iterate rows
    for _, row in inv.iterrows():
        c0,c1,c2,c3,c4,c5,c6,c7,c8 = st.columns([1.2,2,1.2,1,1,1,1,1,0.8])
        c0.write(row.get("item_id",""))
        c1.write(row.get("item_name",""))
        c2.write(row.get("category",""))
        c3.write(row.get("unit",""))
        c4.write(f"{float(row.get('stock_qty',0)):.2f}")
        c5.write(f"₹ {float(row.get('rate',0)):.2f}")
        c6.write(f"₹ {int(row.get('selling_price',0))}")
        c7.write(f"{float(row.get('min_qty',0)):.2f}")
        # Action buttons
        if c8.button("Edit", key=f"edit_{row['item_id']}"):
            st.session_state.editing_item = row["item_id"]
            st.session_state.confirm_delete = None
            st.experimental_rerun()
        if c8.button("Delete", key=f"del_{row['item_id']}"):
            st.session_state.confirm_delete = row["item_id"]
            st.session_state.editing_item = None
            st.experimental_rerun()

def inventory_editor_block():
    inv = list_inventory()
    # top-level controls: upload, add, table (edit/delete)
    with st.expander("📤 Import Stock from CSV", expanded=False):
        st.info("Upload a CSV file to update/add inventory items. Required columns: 'Item Name','Category','Unit','Suppliers Rate','Selling Price'")
        sample_data = {
            'Item Name': ['Advance Compact','Airtight Containers','Ajwain (Carom Seeds)'],
            'Category': ['Smoking','Packaging & Storage','Spices and Masalas'],
            'Unit': ['pack','set','g/pack'],
            'Suppliers Rate': [75.0, 0.0, 0.0],
            'Selling Price': [80, 10, 10]
        }
        sample_df = pd.DataFrame(sample_data)
        st.download_button("📥 Download Sample CSV", data=sample_df.to_csv(index=False).encode('utf-8'), file_name="inventory_import_sample.csv", mime='text/csv')
        uploaded_file = st.file_uploader("Drag and drop file here (CSV)", type="csv", accept_multiple_files=False)
        if uploaded_file is not None:
            try:
                df_import = pd.read_csv(uploaded_file)
                df_import.columns = df_import.columns.str.strip()
                if 'Suppliers Rate' in df_import.columns:
                    df_import['Suppliers Rate'] = df_import['Suppliers Rate'].astype(str).str.replace(r'[^\d.]', '', regex=True).replace('', '0')
                    df_import['Suppliers Rate'] = pd.to_numeric(df_import['Suppliers Rate'], errors='coerce').fillna(0)
                if 'Selling Price' in df_import.columns:
                    df_import['Selling Price'] = df_import['Selling Price'].astype(str).str.replace(r'[^\d]', '', regex=True).replace('', '0')
                    df_import['Selling Price'] = pd.to_numeric(df_import['Selling Price'], errors='coerce').fillna(0).astype(int)
                st.markdown("### Preview")
                st.dataframe(df_import.head())
                if st.button("Process Import", key="process_import"):
                    current_inv = inv.copy()
                    processed = added = updated = 0
                    errors = []
                    for _, r in df_import.iterrows():
                        try:
                            name = str(r.get('Item Name','')).strip()
                            if not name:
                                continue
                            category = str(r.get('Category','')).strip()
                            unit = str(r.get('Unit','')).strip()
                            rate = float(r.get('Suppliers Rate',0) or 0)
                            selling_price = int(r.get('Selling Price',0) or 0)
                            item_id = hashlib.md5(name.encode()).hexdigest()[:8]
                            processed += 1
                            existing = current_inv[current_inv['item_id'] == item_id]
                            if existing.empty:
                                new_row = {
                                    "item_id": item_id,
                                    "item_name": name,
                                    "category": category,
                                    "unit": unit,
                                    "stock_qty": 0.0,
                                    "rate": rate,
                                    "selling_price": selling_price,
                                    "min_qty": 0.0
                                }
                                current_inv = pd.concat([current_inv, pd.DataFrame([new_row])], ignore_index=True)
                                added += 1
                            else:
                                idx = existing.index[0]
                                current_inv.loc[idx, 'rate'] = rate
                                current_inv.loc[idx, 'selling_price'] = selling_price
                                updated += 1
                        except Exception as e:
                            errors.append(str(e))
                    save_csv(current_inv, INVENTORY_FILE)
                    if errors:
                        st.error(f"Import completed with {len(errors)} errors")
                    else:
                        st.success(f"Import done. Processed {processed}, Added {added}, Updated {updated}")
                    st.experimental_rerun()
            except Exception as e:
                st.error(f"Error processing file: {e}")

    # Add new item quick form (but the user asked inventory editing only in table view — keep add optional)
    with st.expander("➕ Add New Inventory Item (optional)", expanded=False):
        with st.form("add_item_form", clear_on_submit=True):
            in_item_name = st.text_input("Item Name *")
            in_category = st.text_input("Category")
            in_unit = st.text_input("Unit (kg/pack/pcs)")
            in_stock = st.number_input("Stock Qty", value=0.0, step=0.1)
            in_rate = st.number_input("Suppliers Rate (₹)", min_value=0.0, step=0.1, value=0.0)
            in_selling_price = st.number_input("Selling Price (₹)", min_value=0, step=5, format="%d", value=0)
            in_min = st.number_input("Min Qty (alert)", min_value=0.0, step=0.1, value=0.0)
            submitted = st.form_submit_button("Add Item")
            if submitted:
                if not in_item_name:
                    st.error("Name required")
                else:
                    iid = hashlib.md5(in_item_name.encode()).hexdigest()[:8]
                    upsert_inventory(iid, in_item_name, in_category, in_unit, in_stock, in_rate, in_selling_price, in_min)
                    st.success("Item added")
                    st.experimental_rerun()

    # Show editable table with Edit/Delete actions
    inv = list_inventory()
    if inv.empty:
        st.info("No items in inventory.")
    else:
        # Render table with actions
        render_inventory_table(inv)

    # handle edit state
    if st.session_state.editing_item:
        item_id = st.session_state.editing_item
        inv = list_inventory()
        row = inv[inv["item_id"].astype(str) == str(item_id)]
        if not row.empty:
            r = row.iloc[0]
            st.markdown("---")
            st.markdown(f"### Edit Item: {r['item_name']} ({r['item_id']})")
            with st.form("edit_item_form"):
                e_name = st.text_input("Item Name", value=r["item_name"])
                e_cat = st.text_input("Category", value=r["category"])
                e_unit = st.text_input("Unit", value=r["unit"])
                e_stock = st.number_input("Stock Qty", value=float(r["stock_qty"]), step=0.1)
                e_rate = st.number_input("Suppliers Rate (₹)", min_value=0.0, value=float(r["rate"]), step=0.1)
                e_sell = st.number_input("Selling Price (₹)", min_value=0, step=5, format="%d", value=int(r["selling_price"]))
                e_min = st.number_input("Min Qty (alert)", min_value=0.0, step=0.1, value=float(r["min_qty"]))
                sub = st.form_submit_button("Save Changes")
            if sub:
                upsert_inventory(item_id, e_name, e_cat, e_unit, e_stock, e_rate, e_sell, e_min)
                st.success("Item updated.")
                st.session_state.editing_item = None
                st.experimental_rerun()
        else:
            st.warning("Item not found.")
            st.session_state.editing_item = None

    # handle delete confirmation
    if st.session_state.confirm_delete:
        did = st.session_state.confirm_delete
        with st.expander("Confirm Delete", expanded=True):
            st.warning(f"Delete inventory item: {did}? This will remove item and it cannot be undone.")
            col_yes, col_no = st.columns([1,1])
            if col_yes.button("Yes, Delete", key=f"confirm_del_{did}"):
                delete_inventory(did)
                st.success("Item deleted.")
                st.session_state.confirm_delete = None
                st.experimental_rerun()
            if col_no.button("Cancel", key=f"cancel_del_{did}"):
                st.session_state.confirm_delete = None
                st.experimental_rerun()

def app_ui():
    user = st.session_state.user
    colL, colR = st.columns([0.75, 0.25])
    with colL:
        st.markdown(f"<h3 style='margin:0;color:#0f172a'>{APP_TITLE}</h3>", unsafe_allow_html=True)
    with colR:
        st.markdown(f"**{user['name']}** · {user['role']}", unsafe_allow_html=True)
        if st.button("Logout"):
            st.session_state.user = None
            st.rerun()

    # Tabs — changed Sales -> Menu
    tabs = ["📊 Dashboard", "📦 Inventory", "💰 Expenses", "🍽️ Menu", "💵 Payments", "🧾 Reports"]
    if user["role"] == "admin":
        tabs.append("👥 Users")
    tab_objs = st.tabs(tabs)

    with tab_objs[0]:
        st.markdown("### 📊 Dashboard")
        inv = list_inventory()
        exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
        orders = load_csv(ORDERS_FILE, SCHEMA["orders"])
        pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"])

        total_exp = float(exp["amount"].astype(float).sum()) if not exp.empty else 0.0
        total_sales = float(orders["total"].astype(float).sum()) if not orders.empty else 0.0
        stock_value = float((inv["stock_qty"].astype(float) * inv["rate"].astype(float)).sum()) if not inv.empty else 0.0
        balances = compute_customer_balances()
        pending_total = float(balances["pending_balance"].sum()) if not balances.empty else 0.0

        c1, c2, c3, c4 = st.columns(4)
        with c1: kpi_card("Total Expenses", f"₹ {total_exp:,.2f}")
        with c2: kpi_card("Total Sales", f"₹ {total_sales:,.2f}")
        with c3: kpi_card("Stock Value (Est.)", f"₹ {stock_value:,.2f}")
        with c4: kpi_card("Pending Customer Balances", f"₹ {pending_total:,.2f}")

        st.markdown("#### Low stock alerts")
        low = inv[inv["stock_qty"].astype(float) < inv["min_qty"].astype(float)]
        if low.empty:
            st.info("No low-stock items.")
        else:
            st.dataframe(low[["item_id","item_name","stock_qty","min_qty","rate"]])

    with tab_objs[1]:
        st.header("Inventory Master")
        inventory_editor_block()
        # Offer CSV/PDF exports
        inv = list_inventory()
        csv_download(inv, "Inventory")
        if st.button("Export Inventory PDF", type="primary"):
            pdf_bytes = make_pdf_bytes("Inventory", inv)
            st.download_button("Download Inventory PDF", pdf_bytes, "inventory.pdf", "application/pdf")

    with tab_objs[2]:
        st.header("Purchases & Expenses")
        inv = list_inventory()
        labels = [f"{r['item_name']} ({r['item_id']})" for _, r in inv.iterrows()] if not inv.empty else []
        colA, colB = st.columns(2)
        with colA:
            st.subheader("Purchase (Stock-In)")
            with st.form("purchase_form", clear_on_submit=True):
                p_date = st.date_input("Date", datetime.now().date())
                p_item_label = st.selectbox("Item", options=["-- Select --"] + labels)
                p_qty = st.number_input("Quantity", min_value=0.0, step=0.1)
                p_rate = st.number_input("Rate (₹)", min_value=0.0, step=0.1)
                p_category = st.text_input("Category", value="Purchase")
                p_remarks = st.text_input("Remarks", "")
                s1 = st.form_submit_button("Add Purchase")
            if s1:
                if p_item_label == "-- Select --":
                    st.error("Select an item.")
                elif p_qty <= 0:
                    st.error("Quantity must be positive")
                else:
                    pid = p_item_label.split("(")[-1].replace(")","").strip()
                    ok, msg = record_purchase(p_date, p_category, p_item_label.split("(")[0].strip(), pid, p_qty, p_rate, user_id=user["user_id"], remarks=p_remarks)
                    if ok:
                        st.success(f"Purchase recorded. Stock increased by {p_qty}")
                        st.rerun()
                    else:
                        st.error(msg)
        with colB:
            st.subheader("Expense (Non-stock)")
            with st.form("expense_form", clear_on_submit=True):
                e_date = st.date_input("Date", datetime.now().date())
                e_cat = st.text_input("Category")
                e_item = st.text_input("Expense Item")
                e_amt = st.number_input("Amount (₹)", min_value=0.0, step=0.1)
                e_rem = st.text_input("Remarks")
                s2 = st.form_submit_button("Record Expense")
            if s2:
                if e_amt <= 0:
                    st.error("Amount must be positive")
                else:
                    record_expense(e_date, e_cat, e_item, e_amt, user_id=user["user_id"], remarks=e_rem)
                    st.success("Expense recorded.")
                    st.rerun()
        st.markdown("#### Recent Purchases & Expenses")
        st.dataframe(load_csv(EXPENSES_FILE, SCHEMA["expenses"]).sort_values("date", ascending=False), use_container_width=True)
        csv_download(load_csv(EXPENSES_FILE, SCHEMA["expenses"]), "Expenses")

    # -----------------------
    # Menu tab (replaces Sales)
    # -----------------------
    with tab_objs[3]:
        st.header("🍽️ Menu / Orders")
        inv = list_inventory()
        if inv.empty:
            st.info("No inventory items.")
        else:
            # category -> item dependent dropdown
            categories = sorted(inv["category"].astype(str).replace("", "Uncategorized").unique().tolist())
            chosen_cat = st.selectbox("Select Category", options=["-- All --"] + categories)
            if chosen_cat and chosen_cat != "-- All --":
                filtered = inv[inv["category"].astype(str) == chosen_cat]
            else:
                filtered = inv.copy()

            # Menu dropdown should show item_name only (no item code)
            menu_items = filtered[["item_name","item_id","selling_price","rate"]].copy()
            menu_items["label"] = menu_items["item_name"].astype(str)
            item_labels = menu_items["label"].tolist()
            selected_label = st.selectbox("Select Menu Item", options=["-- Select --"] + item_labels)
            # find selected row if chosen
            selected_row = None
            if selected_label and selected_label != "-- Select --":
                selected_row = menu_items[menu_items["label"] == selected_label].iloc[0]

            with st.form("menu_order_form", clear_on_submit=True):
                m_date = st.date_input("Date", datetime.now().date())
                m_customer = st.text_input("Customer mobile")
                m_qty = st.number_input("Qty", min_value=1, step=1, value=1, format="%d")
                # default selling price from inventory (int), use step 5
                default_sp = int(selected_row["selling_price"]) if selected_row is not None else 0
                sp_disabled = st.checkbox("Use item selling price", value=True)
                if sp_disabled:
                    m_selling_price = st.number_input("Selling Price (₹)", min_value=0, step=5, format="%d", value=default_sp, disabled=True)
                else:
                    m_selling_price = st.number_input("Selling Price (₹)", min_value=0, step=5, format="%d", value=default_sp)
                # store suppliers rate as rate (optional)
                default_rate = float(selected_row["rate"]) if selected_row is not None else 0.0
                use_rate = st.checkbox("Record supplier rate as well", value=False)
                if use_rate:
                    m_rate = st.number_input("Suppliers Rate (₹)", min_value=0.0, step=0.1, value=default_rate)
                else:
                    m_rate = default_rate
                m_payment = st.radio("Payment mode", ["Cash","Credit"], horizontal=True)
                m_rem = st.text_input("Remarks")
                m_submit = st.form_submit_button("Record Order")
            if m_submit:
                if not selected_row:
                    st.error("Select a menu item.")
                elif not m_customer:
                    st.error("Customer mobile required.")
                elif int(m_selling_price) <= 0:
                    st.error("Selling price must be positive.")
                else:
                    pid = selected_row["item_id"]
                    item_name = selected_row["item_name"]
                    ok, msg = record_order(m_date, m_customer, pid, item_name, m_qty, m_rate, m_selling_price, m_payment, user_id=user["user_id"], remarks=m_rem)
                    if ok:
                        st.success("Order recorded & stock updated.")
                        st.rerun()
                    else:
                        st.error(msg)

        st.markdown("#### Recent Orders")
        ords = load_csv(ORDERS_FILE, SCHEMA["orders"])
        # present selling_price column if present
        st.dataframe(ords.sort_values("date", ascending=False), use_container_width=True)
        csv_download(ords, "Orders")

    with tab_objs[4]:
        st.header("Customer Payments")
        balances = compute_customer_balances()
        st.dataframe(balances if not balances.empty else new_df(["customer_id","credit_sales_total","payments_total","pending_balance"]))
        with st.form("payment_form", clear_on_submit=True):
            p_date = st.date_input("Date", datetime.now().date())
            p_cust = st.text_input("Customer mobile")
            p_amt = st.number_input("Amount", min_value=0.0, step=0.1)
            p_mode = st.selectbox("Mode", ["Cash","UPI","Card","Other"])
            p_rem = st.text_input("Remarks")
            p_sub = st.form_submit_button("Record Payment")
        if p_sub:
            if not p_cust or p_amt <= 0:
                st.error("Customer and valid amount required.")
            else:
                record_payment(p_date, p_cust, p_amt, p_mode, remarks=p_rem, user_id=user["user_id"])
                st.success("Payment recorded.")
                st.rerun()
        st.markdown("#### Payment History")
        st.dataframe(load_csv(PAYMENTS_FILE, SCHEMA["payments"]).sort_values("date", ascending=False), use_container_width=True)
        csv_download(load_csv(PAYMENTS_FILE, SCHEMA["payments"]), "Payments")

    with tab_objs[5]:
        st.header("Reports & Exports")
        today = datetime.now().date()
        default_start = today.replace(day=1)
        c1,c2,c3 = st.columns([1.2,1.2,1.6])
        with c1: start_date = st.date_input("Start date", default_start)
        with c2: end_date = st.date_input("End date", today)
        with c3: filter_cust = st.text_input("Filter by Customer (mobile)")
        exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
        ords = load_csv(ORDERS_FILE, SCHEMA["orders"])
        pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
        def drange(df, col="date"):
            if df.empty: return df
            df2 = df.copy()
            df2[col] = pd.to_datetime(df2[col], errors='coerce').dt.date
            return df2[(df2[col] >= start_date) & (df2[col] <= end_date)]
        exp_f = drange(exp,"date")
        ord_f = drange(ords,"date")
        pay_f = drange(pays,"date")
        if filter_cust:
            ord_f = ord_f[ord_f["customer_id"].astype(str)==str(filter_cust)]
            pay_f = pay_f[pay_f["customer_id"].astype(str)==str(filter_cust)]
        cash_sales = ord_f[ord_f["payment_mode"].str.lower()=="cash"]["total"].astype(float).sum() if not ord_f.empty else 0.0
        total_sales = ord_f["total"].astype(float).sum() if not ord_f.empty else 0.0
        total_exp = exp_f["amount"].astype(float).sum() if not exp_f.empty else 0.0
        net_cash = cash_sales - total_exp
        kk1,kk2,kk3,kk4 = st.columns(4)
        with kk1: kpi_card("Expenses (range)", f"₹ {total_exp:,.2f}")
        with kk2: kpi_card("Sales (range)", f"₹ {total_sales:,.2f}")
        with kk3: kpi_card("Cash Sales (range)", f"₹ {cash_sales:,.2f}")
        with kk4: kpi_card("Net Cash (Cash Sales - Expenses)", f"₹ {net_cash:,.2f}")
        st.markdown("#### Expenses (filtered)"); st.dataframe(exp_f)
        csv_download(exp_f, "Expenses_Filtered")
        st.markdown("#### Sales (filtered)"); st.dataframe(ord_f)
        csv_download(ord_f, "Sales_Filtered")
        st.markdown("#### Payments (filtered)"); st.dataframe(pay_f)
        csv_download(pay_f, "Payments_Filtered")
        st.markdown("#### Customer Balances"); st.dataframe(compute_customer_balances())
        csv_download(compute_customer_balances(), "Customer_Balances")
        if st.button("Export Summary PDF", type="primary"):
            summary = pd.DataFrame({
                "Metric":["Expenses (range)","Sales (range)","Cash Sales","Net Cash"],
                "Value":[f"₹ {total_exp:,.2f}", f"₹ {total_sales:,.2f}", f"₹ {cash_sales:,.2f}", f"₹ {net_cash:,.2f}"]
            })
            pdfb = make_pdf_bytes("DailyShop Summary", summary)
            st.download_button("Download PDF", data=pdfb, file_name="summary.pdf", mime="application/pdf")

    if user['role']=="admin":
        with tab_objs[-1]:
            st.header("User Management (Admin)")
            users = load_csv(USERS_FILE, SCHEMA["users"])
            st.dataframe(users[["user_id","name","role","mobile"]], use_container_width=True)
            with st.form("add_user"):
                u_id = st.text_input("User ID (unique)")
                u_name = st.text_input("Full Name")
                u_role = st.selectbox("Role", ["admin","staff","customer"])
                u_mobile = st.text_input("Mobile (login)")
                u_password = st.text_input("Password", type="password")
                subu = st.form_submit_button("Save User")
            if subu:
                if not u_mobile or not u_name or not u_password or not u_id:
                    st.error("All fields required.")
                else:
                    create_or_update_user(u_id, u_name, u_role, u_mobile, u_password)
                    st.success("User saved.")
                    st.rerun()
            st.markdown("#### Reset Password")
            with st.form("reset_pw"):
                r_mobile = st.text_input("User mobile")
                r_pw = st.text_input("New password", type="password")
                r_sub = st.form_submit_button("Reset")
            if r_sub:
                usr = get_user_by_mobile(r_mobile)
                if not usr:
                    st.error("User not found.")
                else:
                    create_or_update_user(usr["user_id"], usr["name"], usr["role"], usr["mobile"], r_pw)
                    st.success("Password reset.")
                    st.rerun()

# -----------------------
# Run
# -----------------------
if st.session_state.user is None:
    login_page()
else:
    app_ui()
