# app.py — DailyShop Dairy (single-file)
# Requirements:
#   pip install streamlit pandas fpdf
# Run:
#   streamlit run app.py

import os
import hashlib
import uuid
from datetime import datetime, date
import pandas as pd
import streamlit as st
from fpdf import FPDF

# -----------------------
# Config
# -----------------------
APP_TITLE = "🛒 DailyShop Dairy"
DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.csv")
INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.csv")
PURCHASES_FILE = os.path.join(DATA_DIR, "purchases.csv")
EXPENSES_FILE = os.path.join(DATA_DIR, "expenses.csv")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.csv")
PAYMENTS_FILE = os.path.join(DATA_DIR, "payments.csv")

# Schema definitions (column order)
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
# File & CSV helpers
# -----------------------
def ensure_data_dir():
    if os.path.exists(DATA_DIR) and not os.path.isdir(DATA_DIR):
        # if a file named 'data' exists, remove it and make directory
        try:
            os.remove(DATA_DIR)
        except Exception:
            pass
    os.makedirs(DATA_DIR, exist_ok=True)

def new_df(cols):
    return pd.DataFrame(columns=cols)

def load_csv(path, cols):
    """Load CSV (if missing create) and ensure columns exist (return DataFrame in given order)."""
    ensure_data_dir()
    if not os.path.exists(path):
        df = new_df(cols)
        df.to_csv(path, index=False)
        return df[cols]
    try:
        df = pd.read_csv(path, dtype=str)
    except Exception:
        df = pd.read_csv(path, encoding="latin1", dtype=str)
    # ensure columns present
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    # keep order
    return df[cols]

def save_csv(df, path):
    ensure_data_dir()
    # if df missing some expected cols but path has SCHEMA we try to reorder for neatness
    df.to_csv(path, index=False, encoding="utf-8")

def md5_id(text):
    return hashlib.md5(str(text).encode("utf-8")).hexdigest()[:12]

def uuid_id(prefix=""):
    return prefix + uuid.uuid4().hex[:10]

def round_to_5_int(x):
    try:
        x = float(x)
    except Exception:
        x = 0.0
    return int(round(x / 5.0) * 5)

# -----------------------
# Bootstrap default files and default admin user
# -----------------------
def bootstrap_files_and_default_admin():
    ensure_data_dir()
    # create CSVs if missing with headers
    for name, cols in SCHEMA.items():
        path = {
            "users": USERS_FILE,
            "inventory": INVENTORY_FILE,
            "purchases": PURCHASES_FILE,
            "expenses": EXPENSES_FILE,
            "orders": ORDERS_FILE,
            "payments": PAYMENTS_FILE
        }[name]
        if not os.path.exists(path):
            new_df(cols).to_csv(path, index=False)
    # ensure default admin exists
    users = load_csv(USERS_FILE, SCHEMA["users"])
    # check for any active admin
    has_admin = False
    if not users.empty:
        for _, r in users.iterrows():
            role = str(r.get("role","")).strip().lower()
            active = str(r.get("active","")).strip().lower()
            if role == "admin" and active in ("yes","true","1"):
                has_admin = True
                break
    if not has_admin:
        default = {
            "user_id": "UADMIN",
            "name": "Master Admin",
            "mobile": "9999999999",   # default login id requested
            "password": "admin123",   # default password requested
            "role": "admin",
            "tab": "Dashboard",
            "active": "Yes"
        }
        users = pd.concat([users, pd.DataFrame([default])], ignore_index=True)
        save_csv(users, USERS_FILE)

bootstrap_files_and_default_admin()

# -----------------------
# Authentication & user helpers
# -----------------------
def get_user_by_mobile(mobile):
    users = load_csv(USERS_FILE, SCHEMA["users"])
    if users.empty:
        return None
    users2 = users.fillna("")
    matched = users2[ users2["mobile"].astype(str) == str(mobile) ]
    if matched.empty:
        return None
    return matched.iloc[0].to_dict()

def authenticate(mobile, password):
    u = get_user_by_mobile(mobile)
    if not u:
        return None
    # simple plaintext match (as requested). Could be hashed later.
    if str(u.get("password","")) == str(password) and str(u.get("active","")).strip().lower() in ("yes","true","1"):
        return u
    return None

def upsert_user(user_id, name, mobile, password, role, tab="Dashboard", active="Yes"):
    users = load_csv(USERS_FILE, SCHEMA["users"])
    exists = users[ users["user_id"].astype(str) == str(user_id) ]
    if exists.empty:
        users.loc[len(users)] = [user_id, name, mobile, password, role, tab, active]
    else:
        idx = exists.index[0]
        users.loc[idx, ["name","mobile","password","role","tab","active"]] = [name, mobile, password, role, tab, active]
    save_csv(users, USERS_FILE)

def save_last_tab_for_user(mobile, tab_name):
    users = load_csv(USERS_FILE, SCHEMA["users"])
    if users.empty: return
    users2 = users.copy()
    mask = users2["mobile"].astype(str) == str(mobile)
    if mask.any():
        users2.loc[mask, "tab"] = tab_name
        save_csv(users2, USERS_FILE)

# -----------------------
# Business logic: inventory, purchases, orders, payments, expenses
# -----------------------
def list_inventory():
    inv = load_csv(INVENTORY_FILE, SCHEMA["inventory"]).copy()
    # coerce numeric fields
    for c in ["stock_qty","rate","min_qty","sell_price"]:
        if c in inv.columns:
            inv[c] = pd.to_numeric(inv[c], errors="coerce").fillna(0)
    return inv

def save_inventory_df(df):
    # ensure columns order
    df2 = df.copy()
    for c in ["stock_qty","rate","min_qty","sell_price"]:
        if c in df2.columns:
            df2[c] = pd.to_numeric(df2[c], errors="coerce").fillna(0)
    # Round sell_price to nearest 5 and ensure int
    if "sell_price" in df2.columns:
        df2["sell_price"] = df2["sell_price"].apply(round_to_5_int)
    # cast strings for others
    save_csv(df2[SCHEMA["inventory"]], INVENTORY_FILE)

def upsert_inventory_item(item_id, item_name, area, category, unit, stock_qty, rate, min_qty, sell_price):
    inv = list_inventory()
    if not item_id:
        item_id = md5_id(item_name + "|" + category)
    exists = inv[ inv["item_id"].astype(str) == str(item_id) ]
    sell_price = round_to_5_int(sell_price) if sell_price is not None else round_to_5_int(rate)
    row = {
        "item_id": item_id,
        "item_name": item_name,
        "Area": area or "",
        "category": category or "",
        "unit": unit or "",
        "stock_qty": float(stock_qty or 0),
        "rate": float(rate or 0),
        "min_qty": float(min_qty or 0),
        "sell_price": int(sell_price)
    }
    if exists.empty:
        inv = pd.concat([inv, pd.DataFrame([row])], ignore_index=True)
    else:
        idx = exists.index[0]
        for k,v in row.items():
            inv.loc[idx, k] = v
    save_inventory_df(inv)

def adjust_stock(item_id, delta):
    inv = list_inventory()
    row = inv[ inv["item_id"].astype(str) == str(item_id) ]
    if row.empty:
        return False, "Item not found"
    idx = row.index[0]
    current = float(inv.loc[idx, "stock_qty"])
    new = current + float(delta)
    if new < 0:
        return False, "Insufficient stock"
    inv.loc[idx, "stock_qty"] = new
    save_inventory_df(inv)
    return True, new

def record_purchase(date_, category, item_name, item_id, unit, qty, rate, remarks="", user_id=""):
    df = load_csv(PURCHASES_FILE, SCHEMA["purchases"])
    total = round(float(qty) * float(rate), 2)
    df.loc[len(df)] = [uuid_id("PUR_"), date_.isoformat() if isinstance(date_, date) else str(date_), item_id, item_name, category, unit, float(qty), float(rate), total, remarks]
    save_csv(df, PURCHASES_FILE)
    ok, new = adjust_stock(item_id, float(qty))
    return ok, new

def record_expense(date_, category, item, amount, remarks="", user_id=""):
    df = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    df.loc[len(df)] = [uuid_id("EXP_"), date_.isoformat() if isinstance(date_, date) else str(date_), category, item, float(amount), remarks]
    save_csv(df, EXPENSES_FILE)

def record_order(date_, customer_name, mobile, item_id, item_name, category, qty, price, payment_mode, status="Confirmed", user_id=""):
    df = load_csv(ORDERS_FILE, SCHEMA["orders"])
    total = round(float(qty) * float(price), 2)
    df.loc[len(df)] = [uuid_id("ORD_"), date_.isoformat() if isinstance(date_, date) else str(date_), customer_name, mobile, item_id, item_name, category, float(qty), float(price), total, payment_mode, status]
    save_csv(df, ORDERS_FILE)
    ok, new = adjust_stock(item_id, -float(qty))
    return ok, new

def record_payment(date_, customer_name, mobile, amount, remarks="", user_id=""):
    df = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
    df.loc[len(df)] = [uuid_id("PAY_"), date_.isoformat() if isinstance(date_, date) else str(date_), customer_name, mobile, float(amount), remarks]
    save_csv(df, PAYMENTS_FILE)

def compute_customer_balances():
    orders = load_csv(ORDERS_FILE, SCHEMA["orders"]).copy()
    payments = load_csv(PAYMENTS_FILE, SCHEMA["payments"]).copy()
    # Prepare empty DataFrame structure
    columns = ["mobile", "customer_name", "credit_sales_total", "payments_total", "pending_balance"]
    if orders.empty and payments.empty:
        return pd.DataFrame(columns=columns)
    # Only credit sales considered as outstanding
    if not orders.empty:
        orders["total"] = pd.to_numeric(orders["total"], errors="coerce").fillna(0.0)
        credits = orders[orders["payment_mode"].astype(str).str.lower() == "credit"].copy()
        if not credits.empty:
            credit_sum = credits.groupby(["mobile","customer_name"])["total"].sum().reset_index().rename(columns={"total":"credit_sales_total"})
        else:
            credit_sum = pd.DataFrame(columns=["mobile","customer_name","credit_sales_total"])
    else:
        credit_sum = pd.DataFrame(columns=["mobile","customer_name","credit_sales_total"])
    if not payments.empty:
        payments["amount"] = pd.to_numeric(payments["amount"], errors="coerce").fillna(0.0)
        pay_sum = payments.groupby(["mobile","customer_name"])["amount"].sum().reset_index().rename(columns={"amount":"payments_total"})
    else:
        pay_sum = pd.DataFrame(columns=["mobile","customer_name","payments_total"])
    if credit_sum.empty and pay_sum.empty:
        return pd.DataFrame(columns=columns)
    df = pd.merge(credit_sum, pay_sum, on=["mobile","customer_name"], how="outer").fillna(0.0)
    df["pending_balance"] = df["credit_sales_total"] - df["payments_total"]
    # order columns
    df = df[["mobile","customer_name","credit_sales_total","payments_total","pending_balance"]]
    return df.sort_values("pending_balance", ascending=False)

# -----------------------
# Exports: CSV & PDF helpers
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
    <div style="background:#ffffff;padding:10px;border-radius:8px;">
      <div style="font-weight:700;font-size:18px">{value}</div>
      <div style="color:#6b7280">{label}</div>
    </div>
    """, unsafe_allow_html=True)

def show_message_box(msg, kind="info"):
    if kind == "success":
        st.success(msg)
    elif kind == "error":
        st.error(msg)
    elif kind == "warning":
        st.warning(msg)
    else:
        st.info(msg)

# -----------------------
# Pages / Tab UIs
# -----------------------
if "user" not in st.session_state:
    st.session_state.user = None

def login_page():
    st.markdown(f"<h2 style='text-align:center'>{APP_TITLE}</h2>", unsafe_allow_html=True)
    st.write("Login with mobile and password (default admin: 9999999999 / admin123).")
    with st.form("login_form"):
        mobile = st.text_input("Mobile / ID", value="")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            user = authenticate(mobile, password)
            if user:
                st.session_state.user = user
                st.success(f"Welcome {user.get('name') or user.get('mobile')}!")
                # restore last tab if present in user record
                last_tab = str(user.get("tab","")).strip()
                if last_tab:
                    st.session_state.last_tab = last_tab
                else:
                    st.session_state.last_tab = "Dashboard"
                st.rerun()
            else:
                st.error("Invalid mobile or password or inactive user.")

def ui_app():
    user = st.session_state.user
    # header + user info + logout
    colL, colR = st.columns([0.8, 0.2])
    with colL:
        st.markdown(f"## {APP_TITLE}")
    with colR:
        st.markdown(f"**{user.get('name') or user.get('mobile')}**  ·  {user.get('role')}")
        if st.button("Logout"):
            st.session_state.user = None
            st.experimental_rerun()

    # Build tabs list by role
    role = str(user.get("role","")).strip().lower()
    tabs = ["Dashboard","Inventory","Purchases & Expenses","Sales / Orders","Payments","Reports"]
    if role == "admin":
        tabs.append("Users")

    # If we have last_tab in session_state and it exists in tabs, we will open that tab by selecting correct tab index.
    last_tab = st.session_state.get("last_tab", tabs[0] if tabs else "Dashboard")
    try:
        start_index = tabs.index(last_tab) if last_tab in tabs else 0
    except Exception:
        start_index = 0

    tab_objs = st.tabs(tabs)

    # iterate through tabs and render
    for idx, t in enumerate(tabs):
        with tab_objs[idx]:
            # Save last tab when user views this tab
            st.experimental_set_query_params(tab=t)  # lightweight param to reflect state
            # Update last-tab memory for user (persist to users.csv)
            save_last_tab_for_user(user.get("mobile"), t)
            st.session_state.last_tab = t

            if t == "Dashboard":
                ui_dashboard()
            elif t == "Inventory":
                ui_inventory()
            elif t == "Purchases & Expenses":
                ui_purchases_expenses()
            elif t == "Sales / Orders":
                ui_sales_orders()
            elif t == "Payments":
                ui_payments()
            elif t == "Reports":
                ui_reports()
            elif t == "Users":
                if role == "admin":
                    ui_users()
                else:
                    st.error("Access denied. Admin only.")

# Individual page implementations:
def ui_dashboard():
    st.markdown("### 📊 Dashboard")
    inv = list_inventory()
    exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    orders = load_csv(ORDERS_FILE, SCHEMA["orders"])
    pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"])

    total_exp = float(exp["amount"].astype(float).sum()) if (not exp.empty and "amount" in exp.columns) else 0.0
    total_sales = float(orders["total"].astype(float).sum()) if (not orders.empty and "total" in orders.columns) else 0.0
    stock_value = float((inv["stock_qty"] * inv["rate"]).sum()) if not inv.empty else 0.0
    balances = compute_customer_balances()
    pending_total = float(balances["pending_balance"].sum()) if (not balances.empty and "pending_balance" in balances.columns) else 0.0

    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi_card("Total Expenses", f"₹ {total_exp:,.2f}")
    with c2: kpi_card("Total Sales", f"₹ {total_sales:,.2f}")
    with c3: kpi_card("Stock Value (Est.)", f"₹ {stock_value:,.2f}")
    with c4: kpi_card("Pending Customer Balances", f"₹ {pending_total:,.2f}")

    st.markdown("#### Low stock alerts")
    low = inv[inv["stock_qty"] < inv["min_qty"]]
    if low.empty:
        st.info("No low-stock items.")
    else:
        st.dataframe(low[["item_id","item_name","stock_qty","min_qty","sell_price"]])

def ui_inventory():
    st.header("📦 Inventory Master")
    inv = list_inventory()
    # Ensure DELETE column exists for data_editor usage
    if "DELETE" not in inv.columns:
        inv["DELETE"] = False
    edited = st.data_editor(inv, key="inv_editor", use_container_width=True, num_rows="dynamic")
    colA, colB = st.columns([1,0.4])
    with colA:
        if st.button("Save Inventory"):
            # Convert DELETE to bool safely, remove rows marked True
            df = edited.copy()
            if "DELETE" in df.columns:
                df["DELETE"] = df["DELETE"].fillna(False).astype(bool)
                df = df[~df["DELETE"]].drop(columns=["DELETE"])
            # Ensure numeric conversions
            for c in ["stock_qty","rate","min_qty","sell_price"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
            save_inventory_df(df)
            st.success("Inventory saved.")
            st.experimental_rerun()
    with colB:
        st.download_button("Download Inventory CSV", data=df_to_csv_bytes(inv), file_name="inventory.csv", mime="text/csv")
        if st.button("Export Inventory PDF"):
            pdfb = df_to_pdf_bytes("Inventory", inv)
            st.download_button("Download Inventory PDF", data=pdfb, file_name="inventory.pdf", mime="application/pdf")

    st.markdown("### Import Inventory (CSV)")
    with st.expander("Upload CSV (columns: Item Name, Category, Unit, Suppliers Rate)", expanded=False):
        sample = pd.DataFrame({
            "Item Name": ["Milk (Full Cream)", "Paneer Block"],
            "Category": ["Menu","Menu"],
            "Unit": ["ltr","kg"],
            "Suppliers Rate": [40.0, 300.0]
        })
        st.download_button("Download sample CSV", data=sample.to_csv(index=False).encode("utf-8"), file_name="inventory_sample.csv", mime="text/csv")
        up = st.file_uploader("Drop CSV here", type="csv")
        if up is not None:
            try:
                df_up = pd.read_csv(up)
                st.dataframe(df_up.head())
                if st.button("Process import"):
                    processed = 0; added = 0; updated = 0; errs=[]
                    cur = list_inventory()
                    for _, r in df_up.iterrows():
                        processed += 1
                        try:
                            name = str(r.get("Item Name") or r.get("item_name") or "").strip()
                            cat = str(r.get("Category") or r.get("category") or "").strip()
                            unit = str(r.get("Unit") or r.get("unit") or "").strip()
                            rate = float(r.get("Suppliers Rate") or r.get("rate") or 0)
                            if not name:
                                continue
                            item_id = md5_id(name + "|" + cat)
                            exists = cur[cur["item_id"] == item_id]
                            if exists.empty:
                                upsert_inventory_item(item_id, name, "", cat, unit, 0.0, rate, 0.0, round_to_5_int(rate))
                                added += 1
                            else:
                                upsert_inventory_item(item_id, name, exists.iloc[0].get("Area",""), cat, unit, exists.iloc[0].get("stock_qty",0), rate, exists.iloc[0].get("min_qty",0), round_to_5_int(rate))
                                updated += 1
                        except Exception as e:
                            errs.append(str(e))
                    if errs:
                        st.error(f"Import completed with {len(errs)} errors.")
                        for e in errs: st.write(e)
                    else:
                        st.success(f"Import done. Processed {processed}, Added {added}, Updated {updated}.")
                    st.experimental_rerun()
            except Exception as e:
                st.error(f"Failed to read CSV: {e}")

    st.markdown("### Add / Update Item (Form)")
    with st.form("add_item", clear_on_submit=True):
        item_id = st.text_input("Item ID (leave blank to auto-generate)")
        item_name = st.text_input("Item Name *")
        area = st.text_input("Area (optional)")
        category = st.text_input("Category (Menu/Raw/Other)", value="Menu")
        unit = st.text_input("Unit (e.g., ltr, kg, pcs)")
        stock_qty = st.number_input("Stock Qty", min_value=0.0, step=0.1)
        rate = st.number_input("Purchase rate (₹)", min_value=0.0, step=0.1)
        min_qty = st.number_input("Min Qty (alert)", min_value=0.0, step=0.1)
        sell_price = st.number_input("Sell Price (₹) (rounds to nearest ₹5)", min_value=0, step=1, value=0)
        submitted = st.form_submit_button("Save Item")
        if submitted:
            if not item_name:
                st.error("Item name required.")
            else:
                upsert_inventory_item(item_id, item_name, area, category, unit, stock_qty, rate, min_qty, sell_price or round_to_5_int(rate))
                st.success("Item saved.")
                st.experimental_rerun()

def ui_purchases_expenses():
    st.header("🧾 Purchases & Expenses")
    inv = list_inventory()
    inv_labels = [f"{r['item_name']} ({r['item_id']})" for _, r in inv.iterrows()] if not inv.empty else []
    left, right = st.columns(2)
    with left:
        st.subheader("Record Purchase (Stock-In)")
        with st.form("purchase_form", clear_on_submit=True):
            p_date = st.date_input("Date", date.today())
            p_item = st.selectbox("Item", options=["-- Select --"] + inv_labels)
            p_qty = st.number_input("Quantity", min_value=0.0, step=0.1)
            p_rate = st.number_input("Rate per unit (₹)", min_value=0.0, step=0.1)
            p_remarks = st.text_input("Remarks")
            if st.form_submit_button("Add Purchase"):
                if p_item == "-- Select --":
                    st.error("Select an item.")
                elif p_qty <= 0:
                    st.error("Quantity must be positive.")
                else:
                    pid = p_item.split("(")[-1].replace(")","").strip()
                    ok, res = record_purchase(p_date, "Purchase", p_item.split("(")[0].strip(), pid, "", p_qty, p_rate, remarks=p_remarks)
                    if ok:
                        st.success(f"Purchase recorded; stock increased. New stock: {res}")
                    else:
                        st.error(res)
                    st.experimental_rerun()
    with right:
        st.subheader("Record Expense (Non-stock)")
        with st.form("expense_form", clear_on_submit=True):
            e_date = st.date_input("Date", date.today())
            e_cat = st.text_input("Category")
            e_item = st.text_input("Expense Item")
            e_amt = st.number_input("Amount (₹)", min_value=0.0, step=0.1)
            e_rem = st.text_input("Remarks")
            if st.form_submit_button("Record Expense"):
                if e_amt <= 0:
                    st.error("Amount must be positive.")
                else:
                    record_expense(e_date, e_cat, e_item, e_amt, remarks=e_rem)
                    st.success("Expense recorded.")
                    st.experimental_rerun()

    st.markdown("#### Recent Purchases")
    p_df = load_csv(PURCHASES_FILE, SCHEMA["purchases"]).sort_values("date", ascending=False)
    st.dataframe(p_df.head(50))
    csv_download = st.download_button if hasattr(st, "download_button") else None
    if not p_df.empty:
        st.download_button("⬇ Download Purchases CSV", data=df_to_csv_bytes(p_df), file_name="purchases.csv", mime="text/csv")

    st.markdown("#### Recent Expenses")
    e_df = load_csv(EXPENSES_FILE, SCHEMA["expenses"]).sort_values("date", ascending=False)
    st.dataframe(e_df.head(50))
    if not e_df.empty:
        st.download_button("⬇ Download Expenses CSV", data=df_to_csv_bytes(e_df), file_name="expenses.csv", mime="text/csv")

def ui_sales_orders():
    st.header("🛒 Sales / Orders (Menu)")
    inv = list_inventory()
    menu = inv[ inv["category"].astype(str).str.lower() == "menu" ] if not inv.empty else inv
    item_options = [f"{r['item_name']} ({r['item_id']})" for _, r in menu.iterrows()] if not menu.empty else []
    with st.form("sales_form", clear_on_submit=True):
        s_date = st.date_input("Date", date.today())
        s_payment = st.radio("Payment mode", ["Cash","Credit"], horizontal=True)
        if s_payment.lower() == "cash":
            s_customer = st.text_input("Customer Name", value="Guest")
            s_mobile = st.text_input("Customer Mobile (optional)", value="")
        else:
            # credit requires customer mobile present in users table
            users = load_csv(USERS_FILE, SCHEMA["users"])
            cust_mobiles = users[users["role"].astype(str).str.lower() == "customer"]["mobile"].tolist() if not users.empty else []
            s_mobile = st.selectbox("Select registered customer mobile (required for credit)", options=["-- Select --"] + cust_mobiles)
            s_customer = ""
        if item_options:
            s_item = st.selectbox("Item", options=["-- Select --"] + item_options)
        else:
            s_item = st.text_input("Item name")
        s_qty = st.number_input("Qty", min_value=0.0, step=0.1, value=1.0)
        s_price = st.number_input("Price per unit (₹)", min_value=0.0, step=1.0, value=0.0)
        s_rem = st.text_input("Remarks")
        if st.form_submit_button("Place Order"):
            if (s_item == "-- Select --" or not s_item) and not item_options:
                st.error("Select or enter item.")
            elif s_qty <= 0:
                st.error("Quantity must be positive.")
            elif s_payment.lower() == "credit" and (not s_mobile or s_mobile=="-- Select --"):
                st.error("Credit orders require selecting a registered customer's mobile.")
            else:
                if item_options and s_item != "-- Select --":
                    sel_id = s_item.split("(")[-1].replace(")","").strip()
                    sel_name = s_item.split("(")[0].strip()
                    # check stock
                    inv_row = inv[ inv["item_id"].astype(str) == sel_id ]
                    cur_stock = float(inv_row["stock_qty"].iloc[0]) if not inv_row.empty else 0.0
                    if cur_stock < float(s_qty):
                        st.error(f"Insufficient stock ({cur_stock}). Cannot place order.")
                    else:
                        ok, res = record_order(s_date, s_customer or "Guest", s_mobile or "", sel_id, sel_name, inv_row.iloc[0].get("category",""), s_qty, s_price or inv_row.iloc[0].get("sell_price",0), s_payment, user_id=user.get("user_id",""))
                        if ok:
                            st.success("Order recorded and stock updated.")
                        else:
                            st.error(res)
                else:
                    # item free text
                    ok, res = record_order(s_date, s_customer or "Guest", s_mobile or "", "", s_item, "", s_qty, s_price, s_payment, user_id=user.get("user_id",""))
                    if ok:
                        st.success("Order recorded.")
                    else:
                        st.error(res)
                st.experimental_rerun()

    st.markdown("#### Recent Orders")
    ord_df = load_csv(ORDERS_FILE, SCHEMA["orders"]).sort_values("date", ascending=False)
    st.dataframe(ord_df.head(50))
    if not ord_df.empty:
        st.download_button("⬇ Download Orders CSV", data=df_to_csv_bytes(ord_df), file_name="orders.csv", mime="text/csv")

def ui_payments():
    st.header("💵 Payments & Balances")
    balances = compute_customer_balances()
    st.subheader("Customer Balances")
    if balances.empty:
        st.info("No credit orders or payments recorded.")
    else:
        st.dataframe(balances)
        if st.button("Export Balances CSV"):
            st.download_button("⬇ Download Balances CSV", data=df_to_csv_bytes(balances), file_name="balances.csv", mime="text/csv")
    st.markdown("#### Record Payment")
    with st.form("payment_form", clear_on_submit=True):
        p_date = st.date_input("Date", date.today())
        p_mobile = st.text_input("Customer mobile")
        p_name = st.text_input("Customer name")
        p_amt = st.number_input("Amount", min_value=0.0, step=0.1)
        p_rem = st.text_input("Remarks")
        if st.form_submit_button("Record Payment"):
            if not p_mobile or p_amt <= 0:
                st.error("Customer mobile and positive amount required.")
            else:
                record_payment(p_date, p_name or p_mobile, p_mobile, p_amt, remarks=p_rem)
                st.success("Payment recorded.")
                st.experimental_rerun()
    st.markdown("#### Payment History")
    pay_df = load_csv(PAYMENTS_FILE, SCHEMA["payments"]).sort_values("date", ascending=False)
    st.dataframe(pay_df.head(50))
    if not pay_df.empty:
        st.download_button("⬇ Download Payments CSV", data=df_to_csv_bytes(pay_df), file_name="payments.csv", mime="text/csv")

def ui_reports():
    st.header("📈 Reports & Exports")
    today = date.today()
    default_start = today.replace(day=1)
    start_date = st.date_input("Start date", default_start)
    end_date = st.date_input("End date", today)
    filter_mobile = st.text_input("Filter by customer mobile (optional)")
    exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    ords = load_csv(ORDERS_FILE, SCHEMA["orders"])
    pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
    def filter_range(df, col="date"):
        if df.empty:
            return df
        tmp = df.copy()
        tmp[col] = pd.to_datetime(tmp[col], errors="coerce").dt.date
        return tmp[ (tmp[col] >= start_date) & (tmp[col] <= end_date) ]
    exp_f = filter_range(exp)
    ord_f = filter_range(ords)
    pay_f = filter_range(pays)
    if filter_mobile:
        ord_f = ord_f[ ord_f["mobile"].astype(str) == str(filter_mobile) ]
        pay_f = pay_f[ pay_f["mobile"].astype(str) == str(filter_mobile) ]
    cash_sales = ord_f[ ord_f["payment_mode"].astype(str).str.lower()=="cash"]["total"].astype(float).sum() if not ord_f.empty else 0.0
    total_sales = ord_f["total"].astype(float).sum() if not ord_f.empty else 0.0
    total_exp = exp_f["amount"].astype(float).sum() if not exp_f.empty else 0.0
    net_cash = cash_sales - total_exp
    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi_card("Expenses (range)", f"₹ {total_exp:,.2f}")
    with c2: kpi_card("Sales (range)", f"₹ {total_sales:,.2f}")
    with c3: kpi_card("Cash Sales (range)", f"₹ {cash_sales:,.2f}")
    with c4: kpi_card("Net Cash (Cash Sales - Expenses)", f"₹ {net_cash:,.2f}")
    st.markdown("#### Expenses (filtered)"); st.dataframe(exp_f)
    st.download_button("⬇ Download Filtered Expenses (CSV)", data=df_to_csv_bytes(exp_f), file_name="expenses_filtered.csv", mime="text/csv")
    st.markdown("#### Sales (filtered)"); st.dataframe(ord_f)
    st.download_button("⬇ Download Filtered Sales (CSV)", data=df_to_csv_bytes(ord_f), file_name="sales_filtered.csv", mime="text/csv")
    st.markdown("#### Payments (filtered)"); st.dataframe(pay_f)
    st.download_button("⬇ Download Filtered Payments (CSV)", data=df_to_csv_bytes(pay_f), file_name="payments_filtered.csv", mime="text/csv")
    st.markdown("#### Customer Balances"); st.dataframe(compute_customer_balances())
    st.download_button("⬇ Download Customer Balances (CSV)", data=df_to_csv_bytes(compute_customer_balances()), file_name="customer_balances.csv", mime="text/csv")
    if st.button("Export Summary PDF"):
        summary = pd.DataFrame({
            "Metric": ["Expenses (range)", "Sales (range)", "Cash Sales", "Net Cash"],
            "Value": [f"₹ {total_exp:,.2f}", f"₹ {total_sales:,.2f}", f"₹ {cash_sales:,.2f}", f"₹ {net_cash:,.2f}"]
        })
        pdfb = df_to_pdf_bytes("DailyShop Summary", summary)
        st.download_button("⬇ Download Summary (PDF)", data=pdfb, file_name="summary.pdf", mime="application/pdf")

def ui_users():
    st.header("👥 User Management (Admin)")
    users = load_csv(USERS_FILE, SCHEMA["users"])
    # show editable table (inline)
    if "DELETE" not in users.columns:
        users["DELETE"] = False
    edited = st.data_editor(users, key="users_editor", num_rows="dynamic", use_container_width=True)
    colA, colB = st.columns([1,0.6])
    with colA:
        if st.button("Save Users"):
            df = edited.copy()
            if "DELETE" in df.columns:
                df["DELETE"] = df["DELETE"].fillna(False).astype(bool)
                df = df[~df["DELETE"]].drop(columns=["DELETE"])
            # ensure required columns present, fill defaults
            for c in SCHEMA["users"]:
                if c not in df.columns:
                    df[c] = ""
            save_csv(df[SCHEMA["users"]], USERS_FILE)
            st.success("Users saved.")
            st.experimental_rerun()
    with colB:
        st.download_button("⬇ Download Users CSV", data=df_to_csv_bytes(users), file_name="users.csv", mime="text/csv")
        if st.button("Reset All App State (Admin only)"):
            # admin resets entire session memory (keeps CSV files)
            st.session_state.clear()
            st.experimental_rerun()
    st.markdown("### Add new user")
    with st.form("add_user_form", clear_on_submit=True):
        u_name = st.text_input("Full name")
        u_mobile = st.text_input("Mobile (login)")
        u_pass = st.text_input("Password")
        u_role = st.selectbox("Role", ["admin","staff","customer"], index=1)
        u_active = st.selectbox("Active", ["Yes","No"], index=0)
        if st.form_submit_button("Add User"):
            if not u_mobile or not u_pass or not u_name:
                st.error("Name, mobile and password required.")
            else:
                uid = "U"+uuid.uuid4().hex[:8]
                upsert_user(uid, u_name, u_mobile, u_pass, u_role, tab="Dashboard", active=u_active)
                st.success("User added.")
                st.experimental_rerun()

# -----------------------
# Entrypoint
# -----------------------
def main_app():
    if st.session_state.get("user") is None:
        login_page()
    else:
        # show top header + user info + logout
        u = st.session_state.user
        left, right = st.columns([0.78, 0.22])
        with left:
            st.markdown(f"### {APP_TITLE}")
        with right:
            st.markdown(f"**{u.get('name') or u.get('mobile')}** · {u.get('role')}")
            if st.button("Logout"):
                st.session_state.user = None
                st.experimental_rerun()
        ui_app()

if __name__ == "__main__":
    main_app()
