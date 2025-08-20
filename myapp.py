# app.py — DailyShop Dairy (single file)
# Requirements:
#   pip install streamlit pandas fpdf
# Run:
#   streamlit run app.py

import os
import hashlib
from datetime import date
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

# Sanity check schema
for key, cols in SCHEMA.items():
    assert isinstance(cols, list) and all(isinstance(c, str) for c in cols), f"Invalid SCHEMA['{key}']"

st.set_page_config(page_title=APP_TITLE, layout="wide")

# -----------------------
# Utilities
# -----------------------
def safe_rerun():
    """Rerun Streamlit app, compatible with multiple versions."""
    try:
        st.rerun()
    except AttributeError:
        try:
            st.experimental_rerun()
        except Exception:
            st.stop()

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
        except:
            df = pd.read_csv(path, dtype=str, encoding="latin1", engine="python", on_bad_lines="skip")
        for c in cols:
            if c not in df.columns:
                df[c] = None
        return df[cols]
    return new_df(cols)

def save_csv(df, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def check_pw(raw: str, hashed: str) -> bool:
    return hash_pw(raw) == hashed

def round_to_5(n) -> int:
    try:
        return int(5 * round(float(n) / 5.0))
    except:
        return 0

# -----------------------
# Bootstrap
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

# -----------------------
# Business Logic
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
    for col in ["stock_qty", "rate", "min_qty", "sell_price"]:
        inv[col] = pd.to_numeric(inv[col], errors="coerce").fillna(0)
    return inv

def upsert_inventory(item_id, item_name, category, unit, stock_qty, rate, min_qty, sell_price=0):
    inv = list_inventory()
    sell_price = round_to_5(sell_price)
    exists = inv[inv["item_id"] == item_id]
    if exists.empty:
        inv.loc[len(inv)] = [item_id, item_name, category, unit,
                              float(stock_qty), float(rate), float(min_qty), sell_price]
    else:
        idx = exists.index[0]
        inv.loc[idx, ["item_name", "category", "unit", "stock_qty", "rate", "min_qty", "sell_price"]] = [
            item_name, category, unit, float(stock_qty), float(rate), float(min_qty), sell_price
        ]
    save_csv(inv, INVENTORY_FILE)

def adjust_stock(item_id, delta):
    inv = list_inventory()
    row = inv[inv["item_id"] == item_id]
    if row.empty:
        return False, "Item not found"
    idx = row.index[0]
    current = float(inv.at[idx, "stock_qty"] or 0)
    new = current + float(delta)
    if new < 0:
        return False, {"current": current, "required": abs(delta)}
    inv.at[idx, "stock_qty"] = new
    save_csv(inv, INVENTORY_FILE)
    return True, new

def record_expense(dt, category, item, amount, user_id="", remarks=""):
    df = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    df.loc[len(df)] = [dt.isoformat() if isinstance(dt, date) else str(dt),
                       "Expense", category, item, "", 0.0, 0.0, float(amount), user_id, remarks]
    save_csv(df, EXPENSES_FILE)

def record_purchase(dt, category, item_name, item_id, qty, rate, user_id="", remarks=""):
    amount = round(float(qty) * float(rate), 2)
    df = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
    df.loc[len(df)] = [dt.isoformat() if isinstance(dt, date) else str(dt),
                       "Purchase", category, item_name, item_id, qty, rate, amount, user_id, remarks]
    save_csv(df, EXPENSES_FILE)
    return adjust_stock(item_id, qty)

def record_order(dt, customer_id, item_id, item_name, qty, rate, payment_mode, user_id="", remarks=""):
    total = round(float(qty) * float(rate), 2)
    balance = total if payment_mode.lower() == "credit" else 0.0
    df = load_csv(ORDERS_FILE, SCHEMA["orders"])
    df.loc[len(df)] = [dt.isoformat() if isinstance(dt, date) else str(dt),
                       customer_id, item_id, item_name, qty, rate, total, payment_mode, balance, user_id, remarks]
    save_csv(df, ORDERS_FILE)
    return adjust_stock(item_id, -qty)

def record_payment(dt, customer_id, amount, mode, remarks="", user_id=""):
    df = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
    df.loc[len(df)] = [dt.isoformat() if isinstance(dt, date) else str(dt),
                       customer_id, float(amount), mode, remarks, user_id]
    save_csv(df, PAYMENTS_FILE)

def compute_customer_balances():
    orders = load_csv(ORDERS_FILE, SCHEMA["orders"])
    payments = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
    if orders.empty and payments.empty:
        return new_df(["customer_id", "credit_sales_total", "payments_total", "pending_balance"])
    credits = orders[orders["payment_mode"].str.lower() == "credit"]
    credits["total"] = pd.to_numeric(credits["total"], errors="coerce").fillna(0)
    credit_sum = credits.groupby("customer_id")["total"].sum().rename("credit_sales_total")
    payments["amount"] = pd.to_numeric(payments["amount"], errors="coerce").fillna(0)
    pay_sum = payments.groupby("customer_id")["amount"].sum().rename("payments_total")
    df = pd.concat([credit_sum, pay_sum], axis=1).fillna(0)
    df["pending_balance"] = df["credit_sales_total"] - df["payments_total"]
    out = df.reset_index().rename(columns={"index": "customer_id"})
    return out.sort_values("pending_balance", ascending=False)

# -----------------------
# CSV & PDF Exports
# -----------------------
def csv_download(df, label):
    if df.empty:
        st.warning("No data to export.")
        return
    st.download_button(f"⬇ Download {label} (CSV)",
                       data=df.to_csv(index=False).encode("utf-8"),
                       file_name=f"{label.replace(' ','_')}.csv",
                       mime="text/csv")

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
# Low stock modal
# -----------------------
@st.dialog("Insufficient stock")
def insufficient_stock_dialog(item_name: str, have: float, want: float):
    st.error(f"Not enough **{item_name}** in stock.")
    st.write(f"Available: **{have}** • Requested: **{want}**")
    if st.button("OK", type="primary"):
        safe_rerun()

# -----------------------
# UI / App Layout
# -----------------------
if "user" not in st.session_state:
    st.session_state.user = None

def login_page():
    st.markdown(f"<h2 style='text-align:center;color:#2563EB'>{APP_TITLE}</h2>", unsafe_allow_html=True)
    st.write("Login (default admin: mobile=9999999999, pw=admin123)")
    with st.form("login_form"):
        mobile = st.text_input("Mobile")
        pw = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            user = get_user_by_mobile(mobile)
            if user and check_pw(pw, user["password_hash"]):
                st.session_state.user = user
                safe_rerun()
            else:
                st.error("Invalid credentials")

def app_ui():
    user = st.session_state.user
    st.sidebar.markdown("### Actions")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        safe_rerun()

    st.header(f"{APP_TITLE} — Welcome {user['name']} ({user['role']})")
    tabs = ["Dashboard", "Inventory", "Expenses", "Menu / Booking", "Payments", "Reports"]
    if user["role"] == "admin":
        tabs.append("Users")
    tab_sel = st.tabs(tabs)

    with tab_sel[0]:
        # Dashboard implementation with KPI metrics and low stock alerts
        inv = list_inventory()
        exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
        ords = load_csv(ORDERS_FILE, SCHEMA["orders"])
        pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"])
        total_exp = float(exp["amount"].astype(float).sum()) if not exp.empty else 0.0
        total_sales = float(ords["total"].astype(float).sum()) if not ords.empty else 0.0
        stock_val = float((inv["stock_qty"] * inv["rate"]).sum()) if not inv.empty else 0.0
        balances = compute_customer_balances()
        pending_total = float(balances["pending_balance"].sum()) if not balances.empty else 0.0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Expenses", f"₹ {total_exp:,.2f}")
        c2.metric("Total Sales", f"₹ {total_sales:,.2f}")
        c3.metric("Stock Value (Est.)", f"₹ {stock_val:,.2f}")
        c4.metric("Pending Balances", f"₹ {pending_total:,.2f}")

        low = inv[inv["stock_qty"] < inv["min_qty"]]
        st.subheader("Low Stock Alerts")
        if low.empty:
            st.info("No low stock items.")
        else:
            for _, r in low.iterrows():
                st.warning(f"{r['item_name']} — Stock: {r['stock_qty']} (Min: {r['min_qty']})")

    with tab_sel[1]:
        # Inventory with CSV upload and data_editor
        st.subheader("Inventory Management")
        inv = list_inventory().copy()
        with st.expander("Upload Inventory CSV", expanded=False):
            up = st.file_uploader("CSV with columns: Item Name, Category, Unit, Suppliers Rate", type="csv")
            if up:
                try:
                    df_imp = pd.read_csv(up)
                except:
                    up.seek(0); df_imp = pd.read_csv(up, encoding="latin1")
                df_imp.columns = df_imp.columns.str.strip()
                req = {"Item Name", "Category", "Unit", "Suppliers Rate"}
                missing = req - set(df_imp.columns)
                if missing:
                    st.error(f"Missing: {', '.join(missing)}")
                else:
                    st.dataframe(df_imp.head())
                    if st.button("Import Inventory CSV"):
                        added = updated = 0
                        for _, r in df_imp.iterrows():
                            name = str(r["Item Name"]).strip()
                            if not name: continue
                            cid = hashlib.md5(name.encode()).hexdigest()[:8]
                            cat, unit, rate = r["Category"], r["Unit"], float(r["Suppliers Rate"])
                            existing = inv[inv["item_id"] == cid]
                            if existing.empty:
                                upsert_inventory(cid, name, cat, unit, 0, rate, 0, rate)
                                added += 1
                            else:
                                cur = existing.iloc[0]
                                upsert_inventory(cid, name, cat, unit,
                                                 cur["stock_qty"], rate, cur["min_qty"], cur["sell_price"])
                                updated += 1
                        st.success(f"Imported: {added} added, {updated} updated")
                        safe_rerun()

        st.markdown("Inline Inventory Editor")
        inv_df = inv.copy().assign(DELETE=False)
        edited = st.data_editor(inv_df,
                                use_container_width=True,
                                num_rows="dynamic",
                                column_config={
                                    "DELETE": st.column_config.CheckboxColumn(),
                                    "sell_price": st.column_config.NumberColumn(step=5, format="%d", help="Nearest ₹5")
                                },
                                key="inv_editor"
                               )
        c1, c2 = st.columns([0.3, 0.7])
        with c1:
            if st.button("Save Changes"):
                df_save = edited[~edited["DELETE"]].drop(columns=["DELETE"])
                for idx, row in df_save[df_save["item_id"].astype(str).str.strip() == ""].iterrows():
                    df_save.at[idx, "item_id"] = hashlib.md5(row["item_name"].encode()).hexdigest()[:8]
                for c in ["stock_qty", "rate", "min_qty", "sell_price"]:
                    df_save[c] = pd.to_numeric(df_save[c], errors="coerce").fillna(0)
                df_save["sell_price"] = df_save["sell_price"].map(round_to_5)
                df_save = df_save[SCHEMA["inventory"]]
                save_csv(df_save, INVENTORY_FILE)
                st.success("Inventory Updated")
                safe_rerun()
        with c2:
            csv_download(list_inventory(), "Inventory")
            if st.button("Export Inventory PDF"):
                pdf = make_pdf_bytes("Inventory", list_inventory())
                st.download_button("Download Inventory PDF", pdf, "inventory.pdf", "application/pdf")

    with tab_sel[2]:
        # Purchases & Expenses
        st.subheader("Stock Purchase / Expenses")
        inv = list_inventory()
        labels = [f"{r['item_name']} ({r['item_id']})" for _, r in inv.iterrows()]
        colA, colB = st.beta_columns(2)
        with colA:
            with st.form("purchase_f", clear_on_submit=True):
                d = st.date_input("Date", date.today())
                itm = st.selectbox("Item", ["-- Select --"] + labels)
                qty = st.number_input("Qty", min_value=0.0, step=0.1)
                rate = st.number_input("Rate (₹)", min_value=0.0, step=0.1)
                rem = st.text_input("Remarks")
                if st.form_submit_button("Add Purchase"):
                    if itm == "-- Select --": st.error("Select item")
                    elif qty <= 0: st.error("Qty > 0")
                    else:
                        pid = itm.split("(")[-1].strip(")")
                        record_purchase(d, "Purchase", itm.split("(")[0].strip(), pid, qty, rate, user_id=user["user_id"], remarks=rem)
                        st.success("Purchase recorded")
                        safe_rerun()
        with colB:
            with st.form("expense_f", clear_on_submit=True):
                d = st.date_input("Date", date.today())
                cat = st.text_input("Category")
                item = st.text_input("Expense Item")
                amt = st.number_input("Amount (₹)", min_value=0.0, step=0.1)
                rem = st.text_input("Remarks")
                if st.form_submit_button("Add Expense"):
                    if amt <= 0: st.error("Amount > 0")
                    else:
                        record_expense(d, cat, item, amt, user_id=user["user_id"], remarks=rem)
                        st.success("Expense recorded")
                        safe_rerun()
            with st.expander("Upload Expenses CSV"):
                up = st.file_uploader("Upload CSV (Category,Item,Amount,Optional:Date,Remarks,User_id)", type="csv", key="exp_up")
                if up:
                    try:
                        df_imp = pd.read_csv(up)
                    except:
                        up.seek(0); df_imp = pd.read_csv(up, encoding="latin1")
                    df_imp.columns = df_imp.columns.str.strip()
                    req = {"Category", "Item", "Amount"}
                    missing = req - set(df_imp.columns)
                    if missing:
                        st.error(f"Missing columns: {', '.join(missing)}")
                    else:
                        st.dataframe(df_imp.head())
                        if st.button("Import Expenses CSV"):
                            count = 0
                            for _, r in df_imp.iterrows():
                                dval = r.get("Date", date.today())
                                try:
                                    dval = pd.to_datetime(dval).date()
                                except:
                                    dval = date.today()
                                record_expense(dval, r["Category"], r["Item"], float(r["Amount"]), user_id=r.get("User_id", user["user_id"]), remarks=r.get("Remarks", ""))
                                count += 1
                            st.success(f"Imported {count} records")
                            safe_rerun()
        st.markdown("#### Purchase & Expense Records")
        st.dataframe(load_csv(EXPENSES_FILE, SCHEMA["expenses"]).sort_values("date", ascending=False), use_container_width=True)
        csv_download(load_csv(EXPENSES_FILE, SCHEMA["expenses"]), "Expenses")

    with tab_sel[3]:
        # Menu / Booking
        st.subheader("Menu / Booking")
        inv = list_inventory()
        inv_menu = inv[inv["category"].str.strip().str.lower() == "menu"]

        if inv_menu.empty:
            st.info("No 'Menu' items to book.")
        else:
            names = ["-- Select --"] + inv_menu["item_name"].tolist()
            with st.form("book_f", clear_on_submit=True):
                d = st.date_input("Date", date.today())
                mode = st.radio("Payment Mode", ["Cash", "Credit"], horizontal=True)
                cust = st.text_input("Customer Mobile (required for Credit)", disabled=(mode == "Cash"))
                itm = st.selectbox("Item", names)
                qty = st.number_input("Qty", min_value=1, step=1, value=1)
                default_rate = int(inv_menu.loc[inv_menu["item_name"] == itm, "sell_price"].iloc[0] if itm != "-- Select --" else 0)
                use_price = st.checkbox("Use menu price", value=True)
                rate = st.number_input("Price (₹)", min_value=0, step=5, value=default_rate, disabled=use_price)
                rem = st.text_input("Remarks")
                if st.form_submit_button("Add Booking"):
                    if itm == "-- Select --":
                        st.error("Select item")
                    elif mode == "Credit" and not cust.strip():
                        st.error("Customer mobile required")
                    else:
                        current_stock = list_inventory().loc[list_inventory()["item_id"] == inv_menu.loc[inv_menu["item_name"] == itm, "item_id"].iloc[0], "stock_qty"].iloc[0]
                        if current_stock < qty:
                            insufficient_stock_dialog(itm, current_stock, float(qty))
                        else:
                            price_use = default_rate if use_price else round_to_5(rate)
                            resp = record_order(d, cust.strip() if mode == "Credit" and cust.strip() else "GUEST",
                                                inv_menu.loc[inv_menu["item_name"] == itm, "item_id"].iloc[0],
                                                itm, qty, price_use, mode, user_id=user["user_id"], remarks=rem)
                            if resp[0]:
                                st.success("Booking recorded")
                                safe_rerun()
                            else:
                                st.error("Booking failed")
        st.markdown("#### Recent Bookings")
        df_ord = load_csv(ORDERS_FILE, SCHEMA["orders"]).sort_values("date", ascending=False)
        st.dataframe(df_ord, use_container_width=True)
        csv_download(df_ord, "Sales_Orders")

    with tab_sel[4]:
        # Payments
        st.subheader("Customer Payments")
        balances = compute_customer_balances()
        st.dataframe(balances if not balances.empty else new_df(["customer_id", "credit_sales_total", "payments_total", "pending_balance"]), use_container_width=True)
        with st.form("pay_f", clear_on_submit=True):
            d = st.date_input("Date", date.today())
            cust = st.text_input("Customer Mobile")
            amt = st.number_input("Amount", min_value=0.0, step=0.1)
            mode = st.selectbox("Mode", ["Cash", "UPI", "Card", "Other"])
            rem = st.text_input("Remarks")
            if st.form_submit_button("Record Payment"):
                if not cust.strip() or amt <= 0:
                    st.error("Valid customer and amount required")
                else:
                    record_payment(d, cust.strip(), amt, mode, user_id=user["user_id"], remarks=rem)
                    st.success("Payment recorded")
                    safe_rerun()
        st.markdown("#### Payment History")
        df_p = load_csv(PAYMENTS_FILE, SCHEMA["payments"]).sort_values("date", ascending=False)
        st.dataframe(df_p, use_container_width=True)
        csv_download(df_p, "Payments")

    with tab_sel[5]:
        # Reports
        st.subheader("Reports")
        today = date.today()
        st.write("Select date range and optional customer mobile:")
        c1, c2, c3 = st.columns([1.2, 1.2, 1.6])
        with c1:
            start = st.date_input("Start Date", today.replace(day=1))
        with c2:
            end = st.date_input("End Date", today)
        with c3:
            fc = st.text_input("Filter by Customer Mobile")

        exp_df = load_csv(EXPENSES_FILE, SCHEMA["expenses"])
        ord_df = load_csv(ORDERS_FILE, SCHEMA["orders"])
        pay_df = load_csv(PAYMENTS_FILE, SCHEMA["payments"])

        def date_filter(df, field="date"):
            if df.empty:
                return df
            d2 = df.copy()
            d2[field] = pd.to_datetime(d2[field], errors="coerce").dt.date
            return d2[(d2[field] >= start) & (d2[field] <= end)]

        exp_f = date_filter(exp_df)
        ord_f = date_filter(ord_df)
        pay_f = date_filter(pay_df)

        if fc.strip():
            ord_f = ord_f[ord_f["customer_id"] == fc.strip()]
            pay_f = pay_f[pay_f["customer_id"] == fc.strip()]

        cash_sales = ord_f[ord_f["payment_mode"].str.lower() == "cash"]["total"].astype(float).sum() if not ord_f.empty else 0.0
        total_sales = ord_f["total"].astype(float).sum() if not ord_f.empty else 0.0
        total_exp = exp_f["amount"].astype(float).sum() if not exp_f.empty else 0.0
        net_cash = cash_sales - total_exp

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Expenses (filtered)", f"₹ {total_exp:,.2f}")
        k2.metric("Sales (filtered)", f"₹ {total_sales:,.2f}")
        k3.metric("Cash Sales", f"₹ {cash_sales:,.2f}")
        k4.metric("Net Cash", f"₹ {net_cash:,.2f}")

        st.markdown("#### Filtered Expenses")
        st.dataframe(exp_f, use_container_width=True)
        csv_download(exp_f, "Expenses_Filtered")

        st.markdown("#### Filtered Sales")
        st.dataframe(ord_f, use_container_width=True)
        csv_download(ord_f, "Sales_Filtered")

        st.markdown("#### Filtered Payments")
        st.dataframe(pay_f, use_container_width=True)
        csv_download(pay_f, "Payments_Filtered")

        st.markdown("#### Customer Balances")
        bals = compute_customer_balances()
        st.dataframe(bals, use_container_width=True)
        csv_download(bals, "Customer_Balances")

    if user["role"] == "admin":
        with tab_sel[-1]:
            st.subheader("User Management (Admin)")
            users_df = load_csv(USERS_FILE, SCHEMA["users"])
            grid = users_df[["user_id", "name", "role", "mobile"]].assign(DELETE=False)
            edited = st.data_editor(grid, use_container_width=True, num_rows="dynamic",
                                    column_config={"role": st.column_config.SelectboxColumn(options=["admin","staff","customer"])},
                                    key="users_ed")

            c1, c2 = st.columns([0.45, 0.55])
            with c1:
                if st.button("Save Users"):
                    keep = edited[~edited["DELETE"]].drop(columns=["DELETE"])
                    orig = users_df.copy()
                    for _, row in keep.iterrows():
                        uid = str(row["user_id"]).strip()
                        if uid in orig["user_id"].values:
                            idx = orig[orig["user_id"] == uid].index[0]
                            orig.at[idx, "name"] = row["name"]
                            orig.at[idx, "role"] = row["role"]
                            orig.at[idx, "mobile"] = row["mobile"]
                        else:
                            orig = pd.concat([orig, pd.DataFrame([{
                                "user_id": uid,
                                "name": row["name"],
                                "role": row["role"],
                                "mobile": row["mobile"],
                                "password_hash": hash_pw("welcome123")
                            }])], ignore_index=True)
                    orig = orig[orig["user_id"].isin(keep["user_id"].astype(str))]
                    save_csv(orig, USERS_FILE)
                    st.success("Users updated (new users assigned default pw `welcome123`)")
                    safe_rerun()
            with c2:
                st.markdown("### Add / Reset User")
                with st.form("add_user"):
                    u_id = st.text_input("User ID")
                    u_name = st.text_input("Name")
                    u_role = st.selectbox("Role", ["admin","staff","customer"])
                    u_mobile = st.text_input("Mobile")
                    u_pw = st.text_input("Password", type="password")
                    if st.form_submit_button("Save User"):
                        if not all([u_id.strip(), u_name.strip(), u_mobile.strip(), u_pw]):
                            st.error("All fields required")
                        else:
                            create_or_update_user(u_id.strip(), u_name.strip(), u_role, u_mobile.strip(), u_pw)
                            st.success("User created/updated")
                            safe_rerun()

# -----------------------
# Run App
# -----------------------
if st.session_state.user is None:
    login_page()
else:
    app_ui()
