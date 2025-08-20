# app.py — DailyShop Dairy (single-file)
# Requirements:
#   pip install streamlit pandas fpdf
# Run:
#   streamlit run app.py

import os
import hashlib
from datetime import datetime, date
import math
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

# add 'sell_price' to inventory schema
SCHEMA = {
    "users": ["user_id", "name", "role", "mobile", "password_hash"],
    "inventory": ["item_id", "item_name", "category", "unit", "stock_qty", "rate", "min_qty", "sell_price"],
    "expenses": ["date", "type", "category", "item", "item_id", "qty", "rate", "amount", "user_id", "remarks"],
    "orders": ["date", "customer_id", "item_id", "item_name", "qty", "rate", "total", "payment_mode", "balance", "user_id", "remarks"],
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
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, dtype=str)
        except Exception:
            df = pd.read_csv(path, encoding="latin1", dtype=str)
        # ensure all required columns exist
        for c in cols:
            if c not in df.columns:
                df[c] = None
        # drop unknown extra columns safely
        return df[cols]
    return new_df(cols)

def save_csv(df, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")

def hash_pw(pw: str) -> str:
    return hashlib.sha256(str(pw).encode("utf-8")).hexdigest()

def check_pw(raw: str, hashed: str) -> bool:
    return hash_pw(raw) == hashed

def round_to_5(n: float | int) -> int:
    """Round any number to the nearest 5 rupees (integer)."""
    try:
        return int(5 * round(float(n) / 5.0))
    except Exception:
        return 0

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
            save_csv(new_df(cols), f)
        else:
            # migrate/patch any missing columns
            df = load_csv(f, cols)
            save_csv(df, f)

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
    # Coerce numeric columns
    for col in ["stock_qty", "rate", "min_qty", "sell_price"]:
        inv[col] = pd.to_numeric(inv[col], errors="coerce").fillna(0)
    return inv

def upsert_inventory(item_id, item_name, category, unit, stock_qty, rate, min_qty, sell_price=0):
    inv = list_inventory()
    exists = inv[inv["item_id"].astype(str) == str(item_id)]
    sell_price = round_to_5(sell_price)
    if exists.empty:
        inv.loc[len(inv)] = [item_id, item_name, category, unit, float(stock_qty), float(rate), float(min_qty), int(sell_price)]
    else:
        idx = exists.index[0]
        inv.loc[idx, ["item_name","category","unit","stock_qty","rate","min_qty","sell_price"]] = [
            item_name, category, unit, float(stock_qty), float(rate), float(min_qty), int(sell_price)
        ]
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
        return False, {"current": current, "required": abs(delta), "missing": abs(new)}
    inv.loc[idx, "stock_qty"] = new
    save_csv(inv, INVENTORY_FILE)
    return True, new

def record_expense(dt, category, item, amount, user_id="", remarks=""):
    df = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    df.loc[len(df)] = [
        dt.isoformat() if isinstance(dt, (date, datetime)) else str(dt),
        "Expense", category, item, "", 0.0, 0.0, float(amount or 0.0), user_id, remarks
    ]
    save_csv(df, EXPENSES_FILE)

def record_purchase(dt, category, item_name, item_id, qty, rate, user_id="", remarks=""):
    amount = round(float(qty) * float(rate), 2)
    df = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    df.loc[len(df)] = [
        dt.isoformat() if isinstance(dt, (date, datetime)) else str(dt),
        "Purchase", category, item_name, item_id, qty, rate, amount, user_id, remarks
    ]
    save_csv(df, EXPENSES_FILE)
    ok, val = adjust_stock(item_id, qty)
    return ok, val

def record_order(dt, customer_id, item_id, item_name, qty, rate, payment_mode, user_id="", remarks=""):
    total = round(float(qty) * float(rate), 2)
    balance = total if payment_mode.lower() == "credit" else 0.0
    df = load_csv(ORDERS_FILE, SCHEMA["orders"])
    df.loc[len(df)] = [
        dt.isoformat() if isinstance(dt, (date, datetime)) else str(dt),
        customer_id, item_id, item_name, qty, rate, total, payment_mode, balance, user_id, remarks
    ]
    save_csv(df, ORDERS_FILE)
    ok, new = adjust_stock(item_id, -float(qty))
    return ok, new

def record_payment(dt, customer_id, amount, mode, remarks="", user_id=""):
    df = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
    df.loc[len(df)] = [
        dt.isoformat() if isinstance(dt, (date, datetime)) else str(dt),
        customer_id, float(amount), mode, remarks, user_id
    ]
    save_csv(df, PAYMENTS_FILE)

def compute_customer_balances():
    orders = load_csv(ORDERS_FILE, SCHEMA["orders"])
    payments = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
    if orders.empty and payments.empty:
        return new_df(["customer_id","credit_sales_total","payments_total","pending_balance"])
    credits = orders[orders["payment_mode"].str.lower() == "credit"].copy()
    credits["total"] = pd.to_numeric(credits["total"], errors="coerce").fillna(0.0)
    credit_sum = credits.groupby("customer_id")["total"].sum().rename("credit_sales_total")
    payments["amount"] = pd.to_numeric(payments["amount"], errors="coerce").fillna(0.0)
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
    st.download_button(
        f"⬇ Download {label} (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{label.replace(' ','_')}.csv",
        mime="text/csv"
    )

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
# Dialogs
# -----------------------
@st.dialog("Insufficient stock")
def insufficient_stock_dialog(item_name: str, have: float, want: float):
    st.error(f"Not enough **{item_name}** in stock.")
    st.write(f"Available: **{have}** • Requested: **{want}**")
    if st.button("OK", type="primary"):
        st.rerun()  # close dialog

# -----------------------
# UI / Pages
# -----------------------
if "user" not in st.session_state:
    st.session_state.user = None

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

def app_ui():
    user = st.session_state.user
    with st.sidebar:
        st.markdown("### ⚙️ Options")
        if st.checkbox("Run self-checks (quick)"):
            try:
                inv = list_inventory()
                assert set(SCHEMA["inventory"]).issubset(set(inv.columns))
                st.success("Inventory schema OK")
            except AssertionError:
                st.error("Inventory schema mismatch")
        if st.button("Logout"):
            st.session_state.user = None
            st.rerun()

    colL, colR = st.columns([0.75, 0.25])
    with colL:
        st.markdown(f"<h3 style='margin:0;color:#0f172a'>{APP_TITLE}</h3>", unsafe_allow_html=True)
    with colR:
        st.markdown(f"**{user['name']}** · {user['role']}", unsafe_allow_html=True)

    tabs = ["📊 Dashboard", "📦 Inventory", "💰 Expenses", "🍽️ Menu / Booking", "💵 Payments", "🧾 Reports"]
    if user["role"] == "admin":
        tabs.append("👥 Users")
    tab_objs = st.tabs(tabs)

    # ----- Dashboard -----
    with tab_objs[0]:
        st.markdown("### 📊 Dashboard")
        inv = list_inventory()
        exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
        orders = load_csv(ORDERS_FILE, SCHEMA["orders"])
        pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"])

        total_exp = float(exp["amount"].astype(float).sum()) if not exp.empty else 0.0
        total_sales = float(orders["total"].astype(float).sum()) if not orders.empty else 0.0
        # stock value by cost rate
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
            # show as small cards
            for _, r in low.iterrows():
                st.warning(f"{r['item_name']} — Stock: {r['stock_qty']} (Min: {r['min_qty']})")

    # ----- Inventory (st.data_editor) -----
    with tab_objs[1]:
        st.header("Inventory Master")
        inv = list_inventory().copy()

        with st.expander("📤 Import Stock from CSV", expanded=False):
            st.info("CSV columns: Item Name, Category, Unit, Suppliers Rate")
            sample_data = {
                'Item Name': ['Advance Compact','Airtight Containers','Ajwain (Carom Seeds)','Amchur Powder','Aprons'],
                'Category': ['Smoking','Packaging & Storage','Spices and Masalas','Spices and Masalas','Labor'],
                'Unit': ['pack','set','g/pack','g/pack','piece'],
                'Suppliers Rate': [75.0,0.0,0.0,0.0,0.0]
            }
            sample_df = pd.DataFrame(sample_data)
            st.download_button("📥 Download Sample CSV",
                               data=sample_df.to_csv(index=False).encode('utf-8'),
                               file_name="inventory_import_sample.csv",
                               mime='text/csv')
            uploaded_file = st.file_uploader("Drag-and-drop CSV", type="csv")
            if uploaded_file is not None:
                try:
                    df_import = pd.read_csv(uploaded_file)
                    df_import.columns = df_import.columns.str.strip()
                    if 'Suppliers Rate' in df_import.columns:
                        df_import['Suppliers Rate'] = (
                            df_import['Suppliers Rate']
                            .astype(str).str.replace(r'[^\d.]', '', regex=True)
                            .replace('', '0')
                        )
                        df_import['Suppliers Rate'] = pd.to_numeric(df_import['Suppliers Rate'], errors='coerce').fillna(0)
                    st.markdown("### Preview")
                    st.dataframe(df_import.head())
                    if st.button("Process Import", key="import_btn", type="primary"):
                        current_inv = inv.copy()
                        processed=added=updated=0
                        errors=[]
                        for _, row in df_import.iterrows():
                            try:
                                item_name = str(row.get('Item Name','')).strip()
                                category = str(row.get('Category','')).strip()
                                unit = str(row.get('Unit','')).strip()
                                rate = float(row.get('Suppliers Rate',0))
                                if not item_name:
                                    continue
                                item_id = hashlib.md5(item_name.encode()).hexdigest()[:8]
                                existing = current_inv[current_inv['item_id']==item_id]
                                processed += 1
                                if existing.empty:
                                    new_row = {
                                        "item_id": item_id, "item_name": item_name, "category": category, "unit": unit,
                                        "stock_qty": 0.0, "rate": rate, "min_qty": 0.0, "sell_price": round_to_5(rate)
                                    }
                                    current_inv = pd.concat([current_inv, pd.DataFrame([new_row])], ignore_index=True)
                                    added += 1
                                else:
                                    idx = existing.index[0]
                                    current_inv.loc[idx, 'rate'] = rate
                                    # do not override sell_price if already set
                                    updated += 1
                            except Exception as e:
                                errors.append(str(e))
                        save_csv(current_inv, INVENTORY_FILE)
                        if errors:
                            st.error(f"❌ Import completed with {len(errors)} errors")
                            for e in errors: st.error(f"- {e}")
                        else:
                            st.success(f"✅ Import completed! Processed:{processed}, Added:{added}, Updated:{updated}")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error processing file: {str(e)}")

        st.markdown("#### Inline Edit Inventory")
        edit_df = inv.copy()
        # Show a helper delete checkbox column
        edit_df.insert(0, "DELETE", False)
        edited = st.data_editor(
            edit_df,
            use_container_width=True,
            num_rows="dynamic",  # allow adding rows
            column_config={
                "DELETE": st.column_config.CheckboxColumn(help="Tick to delete this row on Save"),
                "item_id": st.column_config.TextColumn(help="Unique code (leave blank for new rows to auto-generate)"),
                "item_name": st.column_config.TextColumn(help="Display name on Menu"),
                "category": st.column_config.TextColumn(help="Grouping for menu filter"),
                "unit": st.column_config.TextColumn(help="kg/pack/pcs etc."),
                "stock_qty": st.column_config.NumberColumn(format="%.3f", step=0.1),
                "rate": st.column_config.NumberColumn(help="Purchase cost", format="%.2f", step=0.1),
                "min_qty": st.column_config.NumberColumn(format="%.3f", step=0.1),
                "sell_price": st.column_config.NumberColumn(help="Selling price (₹, rounded to 5)", format="%d", step=5),
            },
            key="inv_editor"
        )

        col_s1, col_s2 = st.columns([0.25, 0.75])
        with col_s1:
            if st.button("💾 Save Inventory Changes", type="primary"):
                # Apply deletes and saves
                df_save = edited.copy()
                df_save = df_save[~df_save["DELETE"]].drop(columns=["DELETE"])

                # Fill/Generate item_id for any new rows missing it
                for i, r in df_save[df_save["item_id"].isna() | (df_save["item_id"].astype(str).str.strip()=="")].iterrows():
                    gen_id = hashlib.md5(str(r.get("item_name","")).encode()).hexdigest()[:8]
                    df_save.at[i, "item_id"] = gen_id

                # Coerce numeric + round sell_price to nearest 5
                for c in ["stock_qty","rate","min_qty","sell_price"]:
                    df_save[c] = pd.to_numeric(df_save[c], errors="coerce").fillna(0)
                df_save["sell_price"] = df_save["sell_price"].map(round_to_5)

                # Reorder/ensure schema
                df_save = df_save[SCHEMA["inventory"]]
                save_csv(df_save, INVENTORY_FILE)
                st.success("Inventory saved.")
                st.rerun()
        with col_s2:
            csv_download(list_inventory(), "Inventory")
            if st.button("Export Inventory PDF"):
                pdf_bytes = make_pdf_bytes("Inventory", list_inventory())
                st.download_button("Download Inventory PDF", pdf_bytes, "inventory.pdf", "application/pdf")

    # ----- Purchases & Expenses -----
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
                    ok, msg = record_purchase(
                        p_date, p_category,
                        p_item_label.split("(")[0].strip(), pid, p_qty, p_rate,
                        user_id=user["user_id"], remarks=p_remarks
                    )
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

    # ----- Menu / Booking (Sales) -----
    with tab_objs[3]:
        st.header("🍽️ Menu / Booking")
        inv = list_inventory()
        if inv.empty:
            st.info("No inventory items.")
        else:
            # Dropdown 1: Category
            categories = ["-- All --"] + sorted([c for c in inv["category"].astype(str).fillna("").unique() if c != ""])
            sel_cat = st.selectbox("Item Category", options=categories, index=0)

            # Filter items by category
            inv_filtered = inv.copy()
            if sel_cat != "-- All --":
                inv_filtered = inv[inv["category"].astype(str) == sel_cat]

            # Dropdown 2: Item name only (no code)
            name_to_id = {r["item_name"]: r["item_id"] for _, r in inv_filtered.iterrows()}
            item_names = ["-- Select --"] + sorted(name_to_id.keys())
            with st.form("sales_form_menu", clear_on_submit=True):
                s_date = st.date_input("Date", datetime.now().date())
                s_customer = st.text_input("Customer mobile")
                s_item_name = st.selectbox("Item", options=item_names)
                s_qty = st.number_input("Qty", min_value=1, step=1, value=1, format="%d")  # integers only
                # Price: default from sell_price; 5-rupee increments; force integer
                default_price = 0
                if s_item_name != "-- Select --":
                    default_price = int(inv[inv["item_name"] == s_item_name]["sell_price"].iloc[0])
                use_item_price = st.checkbox("Use menu price", value=True)
                s_rate = st.number_input(
                    "Price (₹)",
                    min_value=0,
                    step=5,
                    value=int(default_price),
                    format="%d",
                    disabled=use_item_price
                )
                s_payment = st.radio("Payment mode", ["Cash","Credit"], horizontal=True)
                s_rem = st.text_input("Remarks")
                s_sub = st.form_submit_button("➕ Add Booking")

            if s_sub:
                if s_item_name == "-- Select --":
                    st.error("Select item")
                elif not s_customer:
                    st.error("Customer mobile is required")
                else:
                    pid = name_to_id[s_item_name]
                    item = inv[inv["item_id"].astype(str) == str(pid)].iloc[0]
                    rate = int(item["sell_price"]) if use_item_price else int(round_to_5(s_rate))
                    if rate <= 0:
                        st.error("Price must be positive")
                    else:
                        # check stock before recording
                        ok_stock, details = adjust_stock(pid, -float(s_qty))
                        if not ok_stock:
                            # revert attempted check (we already subtracted: adjust_stock was called; but since it failed, inventory unchanged)
                            # show modal dialog
                            have = float(inv[inv["item_id"]==pid]["stock_qty"].iloc[0])
                            insufficient_stock_dialog(item["item_name"], have, float(s_qty))
                        else:
                            # since we already reduced, now write order and avoid double-adjust: we'll record order and *not* adjust again
                            # So we record order but pass delta=0 for stock (we already adjusted manually)
                            # To keep logic consistent, we'll reverse the stock adjust we just made and use record_order which adjusts
                            adjust_stock(pid, float(s_qty))  # undo
                            ok, msg = record_order(
                                s_date, s_customer, pid, item["item_name"], s_qty, rate, s_payment,
                                user_id=user["user_id"], remarks=s_rem
                            )
                            if ok:
                                st.success("Booking recorded & stock updated.")
                                st.rerun()
                            else:
                                st.error(msg)

        st.markdown("#### Recent Bookings")
        st.dataframe(load_csv(ORDERS_FILE, SCHEMA["orders"]).sort_values("date", ascending=False), use_container_width=True)
        csv_download(load_csv(ORDERS_FILE, SCHEMA["orders"]), "Sales_Orders")

    # ----- Payments -----
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

    # ----- Reports -----
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
        st.markdown("#### Expenses (filtered)"); st.dataframe(exp_f, use_container_width=True)
        csv_download(exp_f, "Expenses_Filtered")
        st.markdown("#### Sales (filtered)"); st.dataframe(ord_f, use_container_width=True)
        csv_download(ord_f, "Sales_Filtered")
        st.markdown("#### Payments (filtered)"); st.dataframe(pay_f, use_container_width=True)
        csv_download(pay_f, "Payments_Filtered")
        st.markdown("#### Customer Balances"); st.dataframe(compute_customer_balances(), use_container_width=True)
        csv_download(compute_customer_balances(), "Customer_Balances")
        if st.button("Export Summary PDF", type="primary"):
            summary = pd.DataFrame({
                "Metric":["Expenses (range)","Sales (range)","Cash Sales","Net Cash"],
                "Value":[f"₹ {total_exp:,.2f}", f"₹ {total_sales:,.2f}", f"₹ {cash_sales:,.2f}", f"₹ {net_cash:,.2f}"]
            })
            pdfb = make_pdf_bytes("DailyShop Summary", summary)
            st.download_button("Download PDF", data=pdfb, file_name="summary.pdf", mime="application/pdf")

    # ----- Users (Admin) -----
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
