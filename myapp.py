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

# Basic schema sanity check (helps catch earlier TypeError)
for k, cols in SCHEMA.items():
    assert isinstance(cols, list) and all(isinstance(c, str) for c in cols), f"SCHEMA['{k}'] invalid"

st.set_page_config(page_title=APP_TITLE, layout="wide")

# -----------------------
# Utilities
# -----------------------
def safe_make_data_dir():
    if os.path.exists(DATA_DIR) and not os.path.isdir(DATA_DIR):
        try:
            os.remove(DATA_DIR)
        except Exception:
            pass
    os.makedirs(DATA_DIR, exist_ok=True)

def new_df(cols):
    return pd.DataFrame(columns=cols)

def load_csv(path, cols):
    # ensure caller passed a valid list of string column names
    assert isinstance(cols, list) and all(isinstance(c, str) for c in cols), f"Invalid cols: {cols}"
    if os.path.exists(path):
        # robust read: try utf-8, fallback to latin1
        try:
            df = pd.read_csv(path, dtype=str)
        except Exception:
            try:
                df = pd.read_csv(path, dtype=str, encoding="latin1")
            except Exception:
                # last resort: read rows with python engine
                df = pd.read_csv(path, dtype=str, encoding="latin1", engine="python", on_bad_lines="skip")
        # ensure required columns exist
        for c in cols:
            if c not in df.columns:
                df[c] = None
        # return only the schema columns (ensures consistent column order)
        return df[cols]
    return new_df(cols)

def save_csv(df, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")

def hash_pw(pw: str) -> str:
    return hashlib.sha256(str(pw).encode("utf-8")).hexdigest()

def check_pw(raw: str, hashed: str) -> bool:
    return hash_pw(raw) == hashed

def round_to_5(n) -> int:
    try:
        return int(5 * round(float(n) / 5.0))
    except Exception:
        return 0

# -----------------------
# Bootstrap files & defaults
# -----------------------
def bootstrap_files():
    safe_make_data_dir()
    # default admin
    if not os.path.exists(USERS_FILE):
        admin = pd.DataFrame([{
            "user_id": "admin",
            "name": "Master Admin",
            "role": "admin",
            "mobile": "9999999999",
            "password_hash": hash_pw("admin123")
        }], columns=SCHEMA["users"])
        save_csv(admin, USERS_FILE)
    # ensure all data files exist and have required columns
    for path, cols in [
        (INVENTORY_FILE, SCHEMA["inventory"]),
        (EXPENSES_FILE, SCHEMA["expenses"]),
        (ORDERS_FILE, SCHEMA["orders"]),
        (PAYMENTS_FILE, SCHEMA["payments"]),
    ]:
        if not os.path.exists(path):
            save_csv(new_df(cols), path)
        else:
            df = load_csv(path, cols)
            save_csv(df, path)

bootstrap_files()

# -----------------------
# Business logic
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
    # coerce numeric columns
    for c in ["stock_qty", "rate", "min_qty", "sell_price"]:
        inv[c] = pd.to_numeric(inv[c], errors="coerce").fillna(0)
    return inv

def upsert_inventory(item_id, item_name, category, unit, stock_qty, rate, min_qty, sell_price=0):
    inv = list_inventory()
    sell_price = round_to_5(sell_price)
    exists = inv[inv["item_id"].astype(str) == str(item_id)]
    if exists.empty:
        inv.loc[len(inv)] = [item_id, item_name, category, unit, float(stock_qty), float(rate), float(min_qty), int(sell_price)]
    else:
        idx = exists.index[0]
        inv.loc[idx, ["item_name", "category", "unit", "stock_qty", "rate", "min_qty", "sell_price"]] = [
            item_name, category, unit, float(stock_qty), float(rate), float(min_qty), int(sell_price)
        ]
    save_csv(inv, INVENTORY_FILE)

def adjust_stock(item_id, delta):
    inv = list_inventory()
    row = inv[inv["item_id"].astype(str) == str(item_id)]
    if row.empty:
        return False, "Item not found"
    idx = row.index[0]
    current = float(inv.loc[idx, "stock_qty"] or 0)
    new = current + float(delta)
    if new < 0:
        return False, {"current": current, "required": abs(delta)}
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
        return new_df(["customer_id", "credit_sales_total", "payments_total", "pending_balance"])
    credits = orders[orders["payment_mode"].str.lower() == "credit"].copy()
    credits["total"] = pd.to_numeric(credits["total"], errors="coerce").fillna(0.0)
    credit_sum = credits.groupby("customer_id")["total"].sum().rename("credit_sales_total")
    payments["amount"] = pd.to_numeric(payments["amount"], errors="coerce").fillna(0.0)
    pay_sum = payments.groupby("customer_id")["amount"].sum().rename("payments_total")
    df = pd.concat([credit_sum, pay_sum], axis=1).fillna(0.0)
    df["pending_balance"] = df["credit_sales_total"] - df["payments_total"]
    out = df.reset_index().rename(columns={"index": "customer_id"})
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
        pdf.cell(0, 6, "No data", ln=True)
        return pdf.output(dest="S").encode("latin1","ignore")
    cols = list(df.columns)[:8]
    colw = pdf.w / max(len(cols), 1) - 2
    for c in cols:
        pdf.cell(colw, 7, str(c)[:20], border=1)
    pdf.ln()
    for _, row in df.iterrows():
        for c in cols:
            text = str(row.get(c, ""))
            safe = text.encode("latin1", "replace").decode("latin1")
            pdf.cell(colw, 6, safe[:20], border=1)
        pdf.ln()
    return pdf.output(dest="S").encode("latin1","ignore")

# -----------------------
# Dialog (modal) for low stock
# -----------------------
@st.dialog("Insufficient stock")
def insufficient_stock_dialog(item_name: str, have: float, want: float):
    st.error(f"Not enough **{item_name}** in stock.")
    st.write(f"Available: **{have}** • Requested: **{want}**")
    if st.button("OK", type="primary"):
        st.experimental_rerun()  # close dialog by rerunning

# -----------------------
# UI / App
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
                st.experimental_rerun()
            else:
                st.error("Invalid mobile or password")

def app_ui():
    user = st.session_state.user

    with st.sidebar:
        st.markdown("### ⚙️ Options")
        if st.button("Logout"):
            st.session_state.user = None
            st.experimental_rerun()

    colL, colR = st.columns([0.75, 0.25])
    with colL:
        st.markdown(f"<h3 style='margin:0;color:#0f172a'>{APP_TITLE}</h3>", unsafe_allow_html=True)
    with colR:
        st.markdown(f"**{user['name']}** · {user['role']}", unsafe_allow_html=True)

    # Users of any role should be able to access primary tabs; admin additionally gets Users management
    tabs = ["📊 Dashboard", "📦 Inventory", "💰 Expenses", "🍽️ Menu / Booking", "💵 Payments", "🧾 Reports"]
    if user["role"] == "admin":
        tabs.append("👥 Users")
    tab_objs = st.tabs(tabs)

    # --- Dashboard ---
    with tab_objs[0]:
        st.markdown("### 📊 Dashboard")
        inv = list_inventory()
        exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
        ords = load_csv(ORDERS_FILE, SCHEMA["orders"])
        pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"])

        total_exp = float(exp["amount"].astype(float).sum()) if not exp.empty else 0.0
        total_sales = float(ords["total"].astype(float).sum()) if not ords.empty else 0.0
        stock_value = float((inv["stock_qty"].astype(float) * inv["rate"].astype(float)).sum()) if not inv.empty else 0.0
        balances = compute_customer_balances()
        pending_total = float(balances["pending_balance"].sum()) if not balances.empty else 0.0

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Total Expenses", f"₹ {total_exp:,.2f}")
        with c2: st.metric("Total Sales", f"₹ {total_sales:,.2f}")
        with c3: st.metric("Stock Value (Est.)", f"₹ {stock_value:,.2f}")
        with c4: st.metric("Pending Customer Balances", f"₹ {pending_total:,.2f}")

        st.markdown("#### Low stock alerts")
        low = inv[inv["stock_qty"].astype(float) < inv["min_qty"].astype(float)]
        if low.empty:
            st.info("No low-stock items.")
        else:
            for _, r in low.iterrows():
                st.warning(f"{r['item_name']} — Stock: {r['stock_qty']} (Min: {r['min_qty']})")

    # --- Inventory ---
    with tab_objs[1]:
        st.header("Inventory Master")
        inv = list_inventory().copy()

        # CSV Upload for inventory
        with st.expander("📥 Upload Inventory CSV (Item Name, Category, Unit, Suppliers Rate)", expanded=False):
            uploaded_file = st.file_uploader("Upload CSV", type="csv", key="inv_upload")
            if uploaded_file is not None:
                try:
                    try:
                        df_imp = pd.read_csv(uploaded_file)
                    except Exception:
                        uploaded_file.seek(0)
                        df_imp = pd.read_csv(uploaded_file, encoding="latin1")
                    df_imp.columns = df_imp.columns.str.strip()
                    required = {"Item Name", "Category", "Unit", "Suppliers Rate"}
                    missing = required - set(df_imp.columns)
                    if missing:
                        st.error(f"Missing columns: {', '.join(missing)}")
                    else:
                        st.markdown("Preview of uploaded CSV")
                        st.dataframe(df_imp.head())
                        if st.button("Process Inventory CSV"):
                            current = inv.copy()
                            processed = added = updated = 0
                            errors = []
                            for _, row in df_imp.iterrows():
                                try:
                                    name = str(row.get("Item Name","")).strip()
                                    if not name:
                                        continue
                                    category = str(row.get("Category","")).strip()
                                    unit = str(row.get("Unit","")).strip()
                                    rate = float(row.get("Suppliers Rate", 0) or 0)
                                    item_id = hashlib.md5(name.encode()).hexdigest()[:8]
                                    existing = current[current["item_id"] == item_id]
                                    processed += 1
                                    if existing.empty:
                                        upsert_inventory(item_id, name, category, unit, 0.0, rate, 0.0, rate)
                                        added += 1
                                    else:
                                        # update cost rate; preserve stock and sell_price
                                        cur_stock = float(existing.iloc[0]["stock_qty"] or 0)
                                        cur_min = float(existing.iloc[0]["min_qty"] or 0)
                                        cur_sell = int(existing.iloc[0]["sell_price"] or round_to_5(rate))
                                        upsert_inventory(item_id, name, category, unit, cur_stock, rate, cur_min, cur_sell)
                                        updated += 1
                                except Exception as e:
                                    errors.append(str(e))
                            if errors:
                                st.error(f"Import completed with {len(errors)} errors")
                                for e in errors:
                                    st.error(e)
                            else:
                                st.success(f"Import done — processed:{processed} added:{added} updated:{updated}")
                            st.experimental_rerun()
                except Exception as e:
                    st.error(f"Failed reading CSV: {e}")

        # Inline editable inventory via data_editor
        st.markdown("#### Inline Edit Inventory")
        df_editor = inv.copy()
        df_editor.insert(0, "DELETE", False)
        edited = st.data_editor(
            df_editor,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "DELETE": st.column_config.CheckboxColumn(help="Tick to delete this row on Save"),
                "item_id": st.column_config.TextColumn(help="Unique code (leave blank to auto-generate)"),
                "item_name": st.column_config.TextColumn(help="Name shown on Menu"),
                "category": st.column_config.TextColumn(help="Category grouping"),
                "unit": st.column_config.TextColumn(),
                "stock_qty": st.column_config.NumberColumn(format="%.3f", step=0.1),
                "rate": st.column_config.NumberColumn(format="%.2f", step=0.1),
                "min_qty": st.column_config.NumberColumn(format="%.3f", step=0.1),
                "sell_price": st.column_config.NumberColumn(help="Selling price (₹, nearest 5)", format="%d", step=5),
            },
            key="inv_editor_v1"
        )

        c1, c2 = st.columns([0.25, 0.75])
        with c1:
            if st.button("💾 Save Inventory Changes"):
                df_save = edited.copy()
                df_save = df_save[~df_save["DELETE"]].drop(columns=["DELETE"])
                # generate ids for new rows that lack item_id
                missing_mask = df_save["item_id"].isna() | (df_save["item_id"].astype(str).str.strip() == "")
                for i, r in df_save[missing_mask].iterrows():
                    gen = hashlib.md5(str(r.get("item_name","")).encode()).hexdigest()[:8]
                    df_save.at[i, "item_id"] = gen
                # coerce numeric and round sell_price
                for c in ["stock_qty", "rate", "min_qty", "sell_price"]:
                    df_save[c] = pd.to_numeric(df_save[c], errors="coerce").fillna(0)
                df_save["sell_price"] = df_save["sell_price"].map(round_to_5)
                # ensure schema ordering
                df_save = df_save[SCHEMA["inventory"]]
                save_csv(df_save, INVENTORY_FILE)
                st.success("Inventory saved.")
                st.experimental_rerun()
        with c2:
            csv_download(list_inventory(), "Inventory")
            if st.button("Export Inventory PDF"):
                pdfb = make_pdf_bytes("Inventory", list_inventory())
                st.download_button("Download Inventory PDF", data=pdfb, file_name="inventory.pdf", mime="application/pdf")

    # --- Purchases & Expenses ---
    with tab_objs[2]:
        st.header("Purchases & Expenses")
        inv = list_inventory()
        labels = [f"{r['item_name']} ({r['item_id']})" for _, r in inv.iterrows()] if not inv.empty else []
        left, right = st.columns(2)
        with left:
            st.subheader("Purchase (Stock-In)")
            with st.form("purchase_form", clear_on_submit=True):
                p_date = st.date_input("Date", date.today())
                p_item_label = st.selectbox("Item", options=["-- Select --"] + labels)
                p_qty = st.number_input("Quantity", min_value=0.0, step=0.1)
                p_rate = st.number_input("Rate (₹)", min_value=0.0, step=0.1)
                p_rem = st.text_input("Remarks")
                if st.form_submit_button("Add Purchase"):
                    if p_item_label == "-- Select --":
                        st.error("Select an item.")
                    elif p_qty <= 0:
                        st.error("Quantity must be positive")
                    else:
                        pid = p_item_label.split("(")[-1].replace(")","").strip()
                        ok, _ = record_purchase(p_date, "Purchase", p_item_label.split("(")[0].strip(), pid, p_qty, p_rate, user_id=user["user_id"], remarks=p_rem)
                        if ok:
                            st.success(f"Purchase recorded. Stock increased by {p_qty}")
                            st.experimental_rerun()
                        else:
                            st.error("Failed to record purchase")
        with right:
            st.subheader("Expense (Non-stock) & CSV Upload")
            with st.form("expense_form", clear_on_submit=True):
                e_date = st.date_input("Date", date.today())
                e_cat = st.text_input("Category")
                e_item = st.text_input("Expense Item")
                e_amt = st.number_input("Amount (₹)", min_value=0.0, step=0.1)
                e_rem = st.text_input("Remarks")
                if st.form_submit_button("Record Expense"):
                    if e_amt <= 0:
                        st.error("Amount must be positive")
                    else:
                        record_expense(e_date, e_cat, e_item, e_amt, user_id=user["user_id"], remarks=e_rem)
                        st.success("Expense recorded.")
                        st.experimental_rerun()

            # CSV uploader for expenses (flexible columns)
            with st.expander("📥 Upload Expenses CSV (Date, Category, Item, Amount, Remarks, User_id)"):
                up = st.file_uploader("Upload CSV for expenses", type="csv", key="exp_upload")
                if up is not None:
                    try:
                        try:
                            df_exp_imp = pd.read_csv(up)
                        except Exception:
                            up.seek(0)
                            df_exp_imp = pd.read_csv(up, encoding="latin1")
                        df_exp_imp.columns = df_exp_imp.columns.str.strip()
                        required = {"Category", "Item", "Amount"}
                        missing = required - set(df_exp_imp.columns)
                        if missing:
                            st.error(f"Missing columns: {', '.join(missing)}")
                        else:
                            st.dataframe(df_exp_imp.head())
                            if st.button("Process Expenses CSV"):
                                added = 0
                                for _, r in df_exp_imp.iterrows():
                                    try:
                                        d = r.get("Date", date.today())
                                        if pd.isna(d) or str(d).strip()=="":
                                            d = date.today()
                                        else:
                                            d = pd.to_datetime(d).date()
                                        cat = r.get("Category")
                                        item = r.get("Item")
                                        amt = float(r.get("Amount", 0) or 0)
                                        uid = r.get("User_id", user["user_id"])
                                        rem = r.get("Remarks", "")
                                        record_expense(d, cat, item, amt, user_id=uid, remarks=rem)
                                        added += 1
                                    except Exception:
                                        pass
                                st.success(f"Imported {added} expense rows.")
                                st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Failed to read file: {e}")

        st.markdown("#### Recent Purchases & Expenses")
        st.dataframe(load_csv(EXPENSES_FILE, SCHEMA["expenses"]).sort_values("date", ascending=False), use_container_width=True)
        csv_download(load_csv(EXPENSES_FILE, SCHEMA["expenses"]), "Expenses")

    # --- Menu / Booking (sales) ---
    with tab_objs[3]:
        st.header("🍽️ Menu / Booking")
        inv = list_inventory()
        # show only items whose category equals 'Menu' (case-insensitive)
        inv_menu = inv[inv["category"].astype(str).str.strip().str.lower() == "menu"]
        if inv_menu.empty:
            st.info("No items with category 'Menu' available.")
        else:
            names = ["-- Select --"] + inv_menu["item_name"].tolist()
            with st.form("booking_form", clear_on_submit=True):
                b_date = st.date_input("Date", date.today())
                payment_mode = st.radio("Payment mode", ["Cash", "Credit"], horizontal=True)
                customer_mobile = st.text_input("Customer mobile", disabled=(payment_mode == "Cash"), help="Required for Credit only")
                b_item = st.selectbox("Item", names)
                b_qty = st.number_input("Qty", min_value=1, step=1, value=1, format="%d")
                default_price = 0
                if b_item != "-- Select --":
                    default_price = int(inv_menu[inv_menu["item_name"] == b_item]["sell_price"].iloc[0] or 0)
                use_menu_price = st.checkbox("Use menu price", value=True)
                b_price = st.number_input("Price (₹)", min_value=0, step=5, format="%d", value=default_price, disabled=use_menu_price)
                b_rem = st.text_input("Remarks")
                if st.form_submit_button("➕ Add Booking"):
                    if b_item == "-- Select --":
                        st.error("Select item")
                    elif payment_mode == "Credit" and not customer_mobile.strip():
                        st.error("Customer mobile is required for credit bookings.")
                    else:
                        cid = customer_mobile.strip() if (payment_mode == "Credit" and customer_mobile.strip()) else "GUEST"
                        pid = inv_menu[inv_menu["item_name"] == b_item]["item_id"].iloc[0]
                        # Check stock by reading inventory; avoid calling adjust_stock as a dry run
                        current_stock = float(list_inventory().loc[list_inventory()["item_id"] == pid, "stock_qty"].iloc[0] or 0)
                        if current_stock < b_qty:
                            # show modal
                            insufficient_stock_dialog(b_item, current_stock, float(b_qty))
                        else:
                            rate_to_use = int(inv_menu[inv_menu["item_name"] == b_item]["sell_price"].iloc[0]) if use_menu_price else round_to_5(b_price)
                            ok, msg = record_order(b_date, cid, pid, b_item, b_qty, rate_to_use, payment_mode, user_id=user["user_id"], remarks=b_rem)
                            if ok:
                                st.success("Booking recorded & stock updated.")
                                st.experimental_rerun()
                            else:
                                st.error("Failed to record booking.")

        st.markdown("#### Recent Bookings")
        st.dataframe(load_csv(ORDERS_FILE, SCHEMA["orders"]).sort_values("date", ascending=False), use_container_width=True)
        csv_download(load_csv(ORDERS_FILE, SCHEMA["orders"]), "Sales_Orders")

    # --- Payments ---
    with tab_objs[4]:
        st.header("Customer Payments")
        balances = compute_customer_balances()
        st.dataframe(balances if not balances.empty else new_df(["customer_id","credit_sales_total","payments_total","pending_balance"]), use_container_width=True)
        with st.form("payment_form", clear_on_submit=True):
            p_date = st.date_input("Date", date.today())
            p_cust = st.text_input("Customer mobile")
            p_amt = st.number_input("Amount", min_value=0.0, step=0.1)
            p_mode = st.selectbox("Mode", ["Cash","UPI","Card","Other"])
            p_rem = st.text_input("Remarks")
            if st.form_submit_button("Record Payment"):
                if not p_cust or p_amt <= 0:
                    st.error("Customer and valid amount required.")
                else:
                    record_payment(p_date, p_cust, p_amt, p_mode, user_id=user["user_id"], remarks=p_rem)
                    st.success("Payment recorded.")
                    st.experimental_rerun()
        st.markdown("#### Payment History")
        st.dataframe(load_csv(PAYMENTS_FILE, SCHEMA["payments"]).sort_values("date", ascending=False), use_container_width=True)
        csv_download(load_csv(PAYMENTS_FILE, SCHEMA["payments"]), "Payments")

    # --- Reports ---
    with tab_objs[5]:
        st.header("Reports & Exports")
        today = date.today()
        default_start = today.replace(day=1)
        c1, c2, c3 = st.columns([1.2, 1.2, 1.6])
        with c1: start_date = st.date_input("Start date", default_start)
        with c2: end_date = st.date_input("End date", today)
        with c3: filter_cust = st.text_input("Filter by Customer (mobile)")
        exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
        ords = load_csv(ORDERS_FILE, SCHEMA["orders"])
        pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"])

        def drange(df, col="date"):
            if df.empty: return df
            df2 = df.copy()
            df2[col] = pd.to_datetime(df2[col], errors="coerce").dt.date
            return df2[(df2[col] >= start_date) & (df2[col] <= end_date)]

        exp_f = drange(exp, "date")
        ord_f = drange(ords, "date")
        pay_f = drange(pays, "date")
        if filter_cust:
            ord_f = ord_f[ord_f["customer_id"].astype(str) == str(filter_cust)]
            pay_f = pay_f[pay_f["customer_id"].astype(str) == str(filter_cust)]
        cash_sales = ord_f[ord_f["payment_mode"].str.lower() == "cash"]["total"].astype(float).sum() if not ord_f.empty else 0.0
        total_sales = ord_f["total"].astype(float).sum() if not ord_f.empty else 0.0
        total_exp = exp_f["amount"].astype(float).sum() if not exp_f.empty else 0.0
        net_cash = cash_sales - total_exp

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Expenses (range)", f"₹ {total_exp:,.2f}")
        k2.metric("Sales (range)", f"₹ {total_sales:,.2f}")
        k3.metric("Cash Sales (range)", f"₹ {cash_sales:,.2f}")
        k4.metric("Net Cash", f"₹ {net_cash:,.2f}")

        st.markdown("#### Expenses (filtered)")
        st.dataframe(exp_f, use_container_width=True)
        csv_download(exp_f, "Expenses_Filtered")

        st.markdown("#### Sales (filtered)")
        st.dataframe(ord_f, use_container_width=True)
        csv_download(ord_f, "Sales_Filtered")

        st.markdown("#### Payments (filtered)")
        st.dataframe(pay_f, use_container_width=True)
        csv_download(pay_f, "Payments_Filtered")

        st.markdown("#### Customer Balances")
        st.dataframe(compute_customer_balances(), use_container_width=True)
        csv_download(compute_customer_balances(), "Customer_Balances")

    # --- Users (Admin only) ---
    if user["role"] == "admin":
        with tab_objs[-1]:
            st.header("User Management (Admin)")
            users_full = load_csv(USERS_FILE, SCHEMA["users"])
            # present grid WITHOUT showing password_hash to avoid accidental editing
            grid = users_full[["user_id", "name", "role", "mobile"]].copy()
            grid.insert(0, "DELETE", False)
            edited_users = st.data_editor(
                grid,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "DELETE": st.column_config.CheckboxColumn(help="Tick to delete this row on Save"),
                    "role": st.column_config.SelectboxColumn(options=["admin", "staff", "customer"]),
                },
                key="users_editor_v1"
            )

            cA, cB = st.columns([0.45, 0.55])
            with cA:
                if st.button("💾 Save Users"):
                    keep = edited_users[~edited_users["DELETE"]].drop(columns=["DELETE"]).copy()
                    original = users_full.copy()
                    # update existing users and add new ones with default password
                    for _, r in keep.iterrows():
                        uid = str(r["user_id"]).strip()
                        if uid and (original["user_id"] == uid).any():
                            idx = original.index[original["user_id"] == uid][0]
                            original.loc[idx, ["name", "role", "mobile"]] = [r["name"], r["role"], r["mobile"]]
                        else:
                            if not uid:
                                continue
                            new_row = {
                                "user_id": uid, "name": r["name"], "role": r["role"], "mobile": r["mobile"],
                                "password_hash": hash_pw("welcome123")
                            }
                            original = pd.concat([original, pd.DataFrame([new_row])], ignore_index=True)
                    # remove rows deleted by omission
                    keep_ids = set(str(x) for x in keep["user_id"].dropna().astype(str))
                    original = original[original["user_id"].astype(str).isin(keep_ids)]
                    save_csv(original, USERS_FILE)
                    st.success("Users table saved. New users get default password: welcome123")
                    st.experimental_rerun()
            with cB:
                st.markdown("### Add / Reset User")
                with st.form("add_user_form"):
                    u_id = st.text_input("User ID")
                    u_name = st.text_input("Full Name")
                    u_role = st.selectbox("Role", ["admin", "staff", "customer"])
                    u_mobile = st.text_input("Mobile")
                    u_pw = st.text_input("Password", type="password")
                    if st.form_submit_button("Save User"):
                        if not (u_id and u_name and u_mobile and u_pw):
                            st.error("All fields required.")
                        else:
                            create_or_update_user(u_id, u_name, u_role, u_mobile, u_pw)
                            st.success("User saved.")
                            st.experimental_rerun()

# -----------------------
# Run
# -----------------------
if st.session_state.user is None:
    login_page()
else:
    app_ui()
