# app.py — DailyShop Dairy (single-file)
# Requirements:
#   pip install streamlit pandas fpdf
# Run:
#   streamlit run app.py

import os
import io
import hashlib
import uuid
from datetime import datetime, date
import pandas as pd
import streamlit as st
from fpdf import FPDF

# -----------------------
# Global Config
# -----------------------
APP_TITLE = "🛒 DailyShop Dairy"
DATA_DIR = "data"
PRICE_STEP = 5  # ₹5 increments

# File paths
USERS_FILE = os.path.join(DATA_DIR, "users.csv")
INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.csv")
PURCHASES_FILE = os.path.join(DATA_DIR, "purchases.csv")
EXPENSES_FILE = os.path.join(DATA_DIR, "expenses.csv")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.csv")
PAYMENTS_FILE = os.path.join(DATA_DIR, "payments.csv")
SESSIONS_FILE = os.path.join(DATA_DIR, "user_sessions.csv")

# Schemas (exact headers)
SCHEMA = {
    "users": [
        "user_id", "name", "mobile", "password", "role", "tab", "active"
    ],
    "inventory": [
        "item_id", "item_name", "Area", "category", "unit",
        "stock_qty", "rate", "min_qty", "sell_price"
    ],
    "purchases": [
        "purchase_id", "date", "item_id", "item_name", "category",
        "unit", "qty", "rate", "total", "remarks"
    ],
    "expenses": [
        "expense_id", "date", "category", "item", "amount", "remarks"
    ],
    "orders": [
        "order_id", "date", "customer_name", "mobile", "item_id", "item_name",
        "category", "qty", "price", "total", "payment_mode", "status"
    ],
    "payments": [
        "payment_id", "date", "customer_name", "mobile", "amount", "remarks"
    ],
    "sessions": [
        "mobile", "last_tab", "last_login"
    ],
}

# -----------------------
# Streamlit page config
# -----------------------
st.set_page_config(page_title="DailyShop Dairy", layout="wide")

# -----------------------
# Utilities
# -----------------------

def ensure_data_dir():
    if os.path.exists(DATA_DIR) and not os.path.isdir(DATA_DIR):
        try:
            os.remove(DATA_DIR)
        except Exception:
            pass
    os.makedirs(DATA_DIR, exist_ok=True)


def csv_new(cols):
    return pd.DataFrame(columns=cols)


def load_csv(path: str, cols: list) -> pd.DataFrame:
    """Load CSV with safe schema enforcement (adds missing columns)."""
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
        except Exception:
            df = pd.read_csv(path, encoding="latin1")
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        # Return in exact column order
        return df[cols]
    else:
        df = csv_new(cols)
        df.to_csv(path, index=False)
        return df


def save_csv(df: pd.DataFrame, path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df.to_csv(path, index=False)


def md5_short(*parts) -> str:
    txt = "|".join([str(p) for p in parts])
    return hashlib.md5(txt.encode("utf-8")).hexdigest()[:10]


def ts_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"


def round_to_step(value: float, step: int = PRICE_STEP) -> int:
    try:
        return int(round(float(value) / step) * step)
    except Exception:
        return 0


def money(v) -> str:
    try:
        return f"₹ {float(v):,.2f}"
    except Exception:
        return "₹ 0.00"

# -----------------------
# Bootstrap initial data
# -----------------------

def bootstrap_files():
    ensure_data_dir()
    # Users with default admin
    if not os.path.exists(USERS_FILE):
        admin_row = {
            "user_id": "UADMIN",
            "name": "Admin User",
            "mobile": "9999999999",
            "password": "admin123",  # plain as per spec
            "role": "admin",
            # Allowed tabs (internal keys): inv,pur,exp,ord,pay,rep,usr,menu,bal
            "tab": "inv,pur,exp,ord,pay,rep,usr,menu,bal",
            "active": "Yes",
        }
        dfu = pd.DataFrame([admin_row], columns=SCHEMA["users"])
        save_csv(dfu, USERS_FILE)
    # Others
    for path, key in [
        (INVENTORY_FILE, "inventory"),
        (PURCHASES_FILE, "purchases"),
        (EXPENSES_FILE, "expenses"),
        (ORDERS_FILE, "orders"),
        (PAYMENTS_FILE, "payments"),
        (SESSIONS_FILE, "sessions"),
    ]:
        if not os.path.exists(path):
            save_csv(csv_new(SCHEMA[key]), path)


bootstrap_files()

# -----------------------
# Authentication & Session Resume
# -----------------------

def load_users() -> pd.DataFrame:
    return load_csv(USERS_FILE, SCHEMA["users"])


def authenticate(mobile: str, password: str):
    users = load_users()
    # Safety for missing columns ensured by load_csv
    row = users[
        (users["mobile"].astype(str) == str(mobile))
        & (users["password"].astype(str) == str(password))
        & (users["active"].astype(str).str.lower() == "yes")
    ]
    if not row.empty:
        return row.iloc[0].to_dict()
    return None


def get_last_tab_for(mobile: str) -> str:
    df = load_csv(SESSIONS_FILE, SCHEMA["sessions"])
    r = df[df["mobile"].astype(str) == str(mobile)]
    return (r.iloc[0]["last_tab"]) if not r.empty else "dashboard"


def set_last_tab_for(mobile: str, tab_key: str):
    df = load_csv(SESSIONS_FILE, SCHEMA["sessions"])
    r = df[df["mobile"].astype(str) == str(mobile)]
    ts = datetime.now().isoformat(timespec="seconds")
    if r.empty:
        df.loc[len(df)] = [mobile, tab_key, ts]
    else:
        idx = r.index[0]
        df.loc[idx, ["last_tab", "last_login"]] = [tab_key, ts]
    save_csv(df, SESSIONS_FILE)


# -----------------------
# Data access helpers
# -----------------------

def load_inventory() -> pd.DataFrame:
    df = load_csv(INVENTORY_FILE, SCHEMA["inventory"]).copy()
    # Numeric coercion
    for c in ["stock_qty", "rate", "min_qty", "sell_price"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    # Enforce sell_price rounding
    df["sell_price"] = df["sell_price"].apply(lambda x: round_to_step(x))
    return df


def save_inventory(df: pd.DataFrame):
    # Validate & round sell_price to ₹5 and int
    df = df.copy()
    if "DELETE" in df.columns:
        # Cast to boolean safely
        df["DELETE"] = df["DELETE"].fillna(False).astype(bool)
        df = df[~df["DELETE"]].drop(columns=["DELETE"])  # remove deleted rows
    for c in ["stock_qty", "rate", "min_qty", "sell_price"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["sell_price"] = df["sell_price"].apply(lambda v: int(round_to_step(v)))
    save_csv(df[SCHEMA["inventory"]], INVENTORY_FILE)


def list_customers() -> pd.DataFrame:
    u = load_users()
    return u[u["role"].astype(str).str.lower() == "customer"].copy()


# -----------------------
# Stock operations
# -----------------------

def adjust_stock(item_id: str, delta: float):
    inv = load_inventory()
    row = inv[inv["item_id"].astype(str) == str(item_id)]
    if row.empty:
        return False, "Item not found"
    idx = row.index[0]
    new_qty = float(inv.loc[idx, "stock_qty"]) + float(delta)
    if new_qty < 0:
        return False, "Insufficient stock"
    inv.loc[idx, "stock_qty"] = new_qty
    save_inventory(inv)
    return True, new_qty


# -----------------------
# PDF helpers
# -----------------------

def df_to_pdf_bytes(title: str, df: pd.DataFrame) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, txt=title, ln=True)
    pdf.ln(2)
    pdf.set_font("Arial", size=9)
    if df.empty:
        pdf.cell(0, 6, "No data", ln=True)
        return pdf.output(dest="S").encode("latin1", "ignore")
    cols = list(df.columns)
    max_cols = min(8, len(cols))  # keep narrow
    cols = cols[:max_cols]
    colw = max(22, (pdf.w - 20) / max_cols)
    for c in cols:
        pdf.cell(colw, 7, str(c)[:20], border=1)
    pdf.ln()
    for _, r in df.iterrows():
        for c in cols:
            txt = str(r.get(c, ""))
            safe = txt.encode("latin1", "replace").decode("latin1")
            pdf.cell(colw, 6, safe[:22], border=1)
        pdf.ln()
    return pdf.output(dest="S").encode("latin1", "ignore")


# -----------------------
# UI helpers
# -----------------------

def kpi(label, value):
    st.markdown(
        f"""
        <div style='background:#fff;padding:12px 16px;border-radius:12px;box-shadow:0 6px 18px rgba(0,0,0,.06);'>
            <div style='font-size:20px;font-weight:700'>{value}</div>
            <div style='color:#6b7280'>{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def csv_download(df: pd.DataFrame, label: str):
    if df.empty:
        st.warning("No data to export.")
        return
    st.download_button(
        f"⬇ Download {label} (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{label.replace(' ','_').lower()}.csv",
        mime="text/csv",
    )


# -----------------------
# Login / Access Control
# -----------------------
if "user" not in st.session_state:
    st.session_state.user = None


def login_page():
    st.markdown(f"<h2 style='text-align:center;color:#2563eb'>{APP_TITLE}</h2>", unsafe_allow_html=True)
    st.info("Login with mobile and password. Default admin: 9999999999 / admin123")
    with st.form("login_form"):
        mobile = st.text_input("📱 Mobile")
        password = st.text_input("🔒 Password", type="password")
        if st.form_submit_button("Login", use_container_width=True):
            user = authenticate(mobile, password)
            if user:
                st.session_state.user = user
                st.success(f"Welcome {user['name']} ({user['role']})")
                st.rerun()
            else:
                st.error("Invalid credentials or inactive user.")


# -----------------------
# Tabs: Inventory
# -----------------------

def ui_inventory():
    st.subheader("📦 Inventory")

    inv = load_inventory()
    # Add a DELETE boolean column for safe deletion
    if "DELETE" not in inv.columns:
        inv["DELETE"] = False

    st.markdown("###### Inline edit inventory (use DELETE to remove rows)")
    edited = st.data_editor(
        inv,
        key="inv_editor",
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "DELETE": st.column_config.CheckboxColumn(default=False),
            "sell_price": st.column_config.NumberColumn(help="Rounded to ₹5 increments automatically"),
        },
    )

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("💾 Save Inventory", type="primary", use_container_width=True):
            try:
                # Auto-generate missing item_id from name+category
                edited = edited.copy()
                for i, r in edited.iterrows():
                    if not str(r.get("item_id", "")).strip() and str(r.get("item_name", "")).strip():
                        edited.at[i, "item_id"] = md5_short(str(r.get("item_name")), str(r.get("category")))
                save_inventory(edited)
                st.success("Inventory saved.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save inventory: {e}")
    with c2:
        # Inventory CSV import template
        sample = pd.DataFrame([
            {
                "item_id": md5_short("Milk 500ml", "Menu"),
                "item_name": "Milk 500ml",
                "Area": "Dairy",
                "category": "Menu",
                "unit": "Pack",
                "stock_qty": 50,
                "rate": 34,
                "min_qty": 10,
                "sell_price": 40,
            }
        ], columns=SCHEMA["inventory"])        
        st.download_button(
            "📥 Download Inventory Template",
            data=sample.to_csv(index=False).encode("utf-8"),
            file_name="inventory_template.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with c3:
        up = st.file_uploader("Import Inventory CSV", type=["csv"], accept_multiple_files=False)
        if up is not None:
            try:
                dfu = pd.read_csv(up)
                # Ensure schema & rounding
                for c in SCHEMA["inventory"]:
                    if c not in dfu.columns:
                        dfu[c] = 0 if c in ["stock_qty","rate","min_qty","sell_price"] else ""
                for c in ["stock_qty","rate","min_qty","sell_price"]:
                    dfu[c] = pd.to_numeric(dfu[c], errors="coerce").fillna(0)
                dfu["sell_price"] = dfu["sell_price"].apply(lambda v: int(round_to_step(v)))
                save_inventory(dfu[SCHEMA["inventory"]])
                st.success("Inventory imported.")
                st.rerun()
            except Exception as e:
                st.error(f"Import failed: {e}")

    st.markdown("#### Low Stock Alerts")
    inv = load_inventory()
    low = inv[inv["stock_qty"] < inv["min_qty"]]
    if low.empty:
        st.info("No low-stock items.")
    else:
        st.dataframe(low[["item_id","item_name","stock_qty","min_qty","sell_price"]], use_container_width=True)


# -----------------------
# Tabs: Purchases & Expenses
# -----------------------

def ui_purchases_expenses():
    st.subheader("🧾 Purchases & Expenses")
    inv = load_inventory()

    colA, colB = st.columns(2)

    # Purchase form
    with colA:
        st.markdown("### Stock Purchase (adds to inventory)")
        with st.form("purchase_form", clear_on_submit=True):
            p_date = st.date_input("Date", datetime.now().date())
            # Category + Item selection from inventory
            cats = sorted(inv["category"].dropna().astype(str).unique().tolist()) if not inv.empty else []
            sel_cat = st.selectbox("Category", ["--Select--"] + cats)
            items_in_cat = inv[inv["category"].astype(str) == str(sel_cat)] if sel_cat != "--Select--" else inv.iloc[0:0]
            item_labels = [f"{r.item_name} | {r.unit} | stock:{int(r.stock_qty)}" for _, r in items_in_cat.iterrows()]
            sel_label = st.selectbox("Item", ["--Select--"] + item_labels)
            qty = st.number_input("Qty", min_value=0.0, step=1.0, value=0.0)
            rate = st.number_input("Purchase Rate (₹)", min_value=0.0, step=0.5, value=0.0)
            remarks = st.text_input("Remarks", "")
            ok_btn = st.form_submit_button("Add Purchase")
        if ok_btn:
            if sel_cat == "--Select--" or sel_label == "--Select--":
                st.error("Select category and item.")
            elif qty <= 0 or rate <= 0:
                st.error("Quantity and Rate must be positive.")
            else:
                # Find item
                r = items_in_cat.iloc[item_labels.index(sel_label)]
                purchase_id = ts_id("PUR")
                total = float(qty) * float(rate)
                purch = load_csv(PURCHASES_FILE, SCHEMA["purchases"])                
                purch.loc[len(purch)] = [
                    purchase_id,
                    p_date.isoformat(),
                    r.item_id,
                    r.item_name,
                    r.category,
                    r.unit,
                    float(qty),
                    float(rate),
                    round(total, 2),
                    remarks,
                ]
                save_csv(purch, PURCHASES_FILE)
                ok, new = adjust_stock(r.item_id, float(qty))
                if ok:
                    st.success(f"Purchase recorded. New stock: {new}")
                    st.rerun()
                else:
                    st.error(new)

    # Expense form
    with colB:
        st.markdown("### Expense (non-stock)")
        with st.form("expense_form", clear_on_submit=True):
            e_date = st.date_input("Date", datetime.now().date())
            e_cat = st.text_input("Expense Category", "Transport")
            e_item = st.text_input("Expense Item/Description")
            e_amount = st.number_input("Amount (₹)", min_value=0.0, step=1.0, value=0.0)
            e_rem = st.text_input("Remarks", "")
            e_ok = st.form_submit_button("Record Expense")
        if e_ok:
            if e_amount <= 0:
                st.error("Amount must be > 0")
            else:
                exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"])                
                exp.loc[len(exp)] = [
                    ts_id("EXP"), e_date.isoformat(), e_cat, e_item, float(e_amount), e_rem
                ]
                save_csv(exp, EXPENSES_FILE)
                st.success("Expense recorded.")
                st.rerun()

    st.markdown("#### Recent Purchases")
    purch = load_csv(PURCHASES_FILE, SCHEMA["purchases"]).sort_values("date", ascending=False)
    st.dataframe(purch, use_container_width=True)
    csv_download(purch, "purchases")

    st.markdown("#### Recent Expenses")
    exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"]).sort_values("date", ascending=False)
    st.dataframe(exp, use_container_width=True)
    csv_download(exp, "expenses")
    if not exp.empty and st.button("Export Expenses PDF"):
        pdf_bytes = df_to_pdf_bytes("Expenses", exp)
        st.download_button("Download PDF", pdf_bytes, file_name="expenses.pdf", mime="application/pdf")


# -----------------------
# Tabs: Bookings / Sales (Menu)
# -----------------------

def ui_bookings_sales():
    st.subheader("🛒 Bookings / Sales (Menu)")
    inv = load_inventory()
    menu = inv[inv["category"].astype(str) == "Menu"].copy()
    if menu.empty:
        st.info("No 'Menu' items found in inventory.")
        return

    # Category → item dropdown
    cats = sorted(menu["category"].dropna().unique().tolist())
    # In Menu view cats will be only ["Menu"], but keep structure for future
    sel_cat = st.selectbox("Category", cats)
    items = menu[menu["category"] == sel_cat].copy()

    # Two-step: show item names
    sel_item_name = st.selectbox("Item", items["item_name"].tolist())
    sel_row = items[items["item_name"] == sel_item_name].iloc[0]

    # Customer handling
    st.markdown("#### Customer & Booking")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        payment_mode = st.radio("Payment Mode", ["Cash", "Credit"], horizontal=True)
    with col2:
        if payment_mode == "Cash":
            customer_name = st.text_input("Customer Name", value="Guest")
            mobile = st.text_input("Mobile (optional)", value="")
        else:
            # Credit requires registered customer
            cust_df = list_customers()
            if cust_df.empty:
                st.warning("No registered customers. Add in Users tab.")
                customer_name = ""
                mobile = ""
            else:
                cust_df = cust_df[cust_df["active"].astype(str).str.lower() == "yes"]
                cust_options = [f"{r['name']} ({r['mobile']})" for _, r in cust_df.iterrows()]
                pick = st.selectbox("Select Customer", cust_options)
                # Parse chosen
                name_part = pick.split("(")[0].strip()
                mobile_part = pick.split("(")[-1].replace(")", "").strip()
                customer_name = name_part
                mobile = mobile_part
    with col3:
        qty = st.number_input("Quantity", min_value=1.0, step=1.0, value=1.0)
        default_price = int(round_to_step(sel_row["sell_price"]))
        price = st.number_input("Price (₹)", min_value=0, step=PRICE_STEP, value=default_price)
        price = int(round_to_step(price))

    if st.button("Confirm Booking", type="primary"):
        # Stock check
        if qty > float(sel_row["stock_qty"]):
            st.error("❌ Insufficient stock for this item.")
            st.stop()
        # Enforce credit requirements
        if payment_mode == "Credit" and (not mobile or not customer_name):
            st.error("Credit booking requires a registered customer.")
            st.stop()
        # Record order
        order = load_csv(ORDERS_FILE, SCHEMA["orders"])
        total = float(qty) * float(price)
        order.loc[len(order)] = [
            ts_id("ORD"), datetime.now().isoformat(timespec="seconds"),
            customer_name if payment_mode == "Cash" else customer_name,
            mobile if payment_mode == "Cash" else mobile,
            sel_row["item_id"], sel_row["item_name"], sel_row["category"],
            float(qty), int(price), round(total, 2), payment_mode, "Confirmed"
        ]
        save_csv(order, ORDERS_FILE)
        ok, new_qty = adjust_stock(str(sel_row["item_id"]), -float(qty))
        if ok:
            st.success(f"Order recorded. New stock: {new_qty}")
            st.rerun()
        else:
            st.error(new_qty)

    # Recent bookings
    st.markdown("#### Recent Bookings")
    ords = load_csv(ORDERS_FILE, SCHEMA["orders"]).sort_values("date", ascending=False)
    st.dataframe(ords.head(50), use_container_width=True)
    csv_download(ords, "orders")


# -----------------------
# Tabs: Payments
# -----------------------

def compute_balances() -> pd.DataFrame:
    ords = load_csv(ORDERS_FILE, SCHEMA["orders"]).copy()
    pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"]).copy()
    if ords.empty and pays.empty:
        return pd.DataFrame(columns=["mobile","customer_name","credit_sales","payments","pending"])    
    ords["total"] = pd.to_numeric(ords["total"], errors="coerce").fillna(0)
    cred = ords[ords["payment_mode"].astype(str).str.lower() == "credit"].copy()
    ogrp = cred.groupby(["mobile","customer_name"])['total'].sum().reset_index().rename(columns={"total":"credit_sales"})

    pays["amount"] = pd.to_numeric(pays["amount"], errors="coerce").fillna(0)
    pgrp = pays.groupby(["mobile","customer_name"])['amount'].sum().reset_index().rename(columns={"amount":"payments"})

    df = pd.merge(ogrp, pgrp, on=["mobile","customer_name"], how="outer").fillna(0)
    df["pending"] = df["credit_sales"] - df["payments"]
    df = df.sort_values("pending", ascending=False)
    return df


def ui_payments():
    st.subheader("💵 Payments & Balances")

    # Balances
    bal = compute_balances()
    st.markdown("#### Customer Balances")
    st.dataframe(bal, use_container_width=True)
    csv_download(bal, "customer_balances")

    # Payment form
    with st.form("pay_form", clear_on_submit=True):
        pay_date = st.date_input("Date", datetime.now().date())
        # from users list of customers for consistency
        custs = list_customers()
        if not custs.empty:
            custs = custs[custs["active"].astype(str).str.lower() == "yes"]
            options = [f"{r['name']} ({r['mobile']})" for _, r in custs.iterrows()]
            pick = st.selectbox("Customer", options)
            cname = pick.split("(")[0].strip()
            cmob = pick.split("(")[-1].replace(")","" ).strip()
        else:
            st.warning("No customers in user list. You can still type below.")
            cname = st.text_input("Customer Name")
            cmob = st.text_input("Mobile")
        amt = st.number_input("Amount (₹)", min_value=0.0, step=1.0)
        rem = st.text_input("Remarks", "Settlement")
        ok = st.form_submit_button("Record Payment")
    if ok:
        if amt <= 0:
            st.error("Amount must be > 0")
        else:
            pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"])            
            pays.loc[len(pays)] = [ts_id("PAY"), pay_date.isoformat(), cname, cmob, float(amt), rem]
            save_csv(pays, PAYMENTS_FILE)
            st.success("Payment recorded.")
            st.rerun()

    st.markdown("#### Payment History")
    ph = load_csv(PAYMENTS_FILE, SCHEMA["payments"]).sort_values("date", ascending=False)
    st.dataframe(ph, use_container_width=True)
    csv_download(ph, "payments")


# -----------------------
# Tabs: Reports
# -----------------------

def ui_reports():
    st.subheader("🧮 Reports")
    today = date.today()
    start = st.date_input("Start date", today.replace(day=1))
    end = st.date_input("End date", today)

    def in_range(df, col="date"):
        if df.empty:
            return df
        df = df.copy()
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
        return df[(df[col] >= start) & (df[col] <= end)]

    exp = in_range(load_csv(EXPENSES_FILE, SCHEMA["expenses"]))
    ords = in_range(load_csv(ORDERS_FILE, SCHEMA["orders"]))
    pays = in_range(load_csv(PAYMENTS_FILE, SCHEMA["payments"]))

    cash_sales = ords[ords["payment_mode"].astype(str).str.lower()=="cash"]["total"].astype(float).sum() if not ords.empty else 0
    total_sales = ords["total"].astype(float).sum() if not ords.empty else 0
    total_exp = exp["amount"].astype(float).sum() if not exp.empty else 0
    net_cash = cash_sales - total_exp

    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi("Expenses (range)", money(total_exp))
    with c2: kpi("Sales (range)", money(total_sales))
    with c3: kpi("Cash Sales", money(cash_sales))
    with c4: kpi("Net Cash", money(net_cash))

    st.markdown("#### Expenses (filtered)")
    st.dataframe(exp, use_container_width=True)
    csv_download(exp, "expenses_filtered")

    st.markdown("#### Sales (filtered)")
    st.dataframe(ords, use_container_width=True)
    csv_download(ords, "sales_filtered")

    st.markdown("#### Payments (filtered)")
    st.dataframe(pays, use_container_width=True)
    csv_download(pays, "payments_filtered")

    st.markdown("#### Customer Balances (all time)")
    bal = compute_balances()
    st.dataframe(bal, use_container_width=True)
    csv_download(bal, "customer_balances_all")

    if st.button("Export Summary PDF"):
        summary = pd.DataFrame({
            "Metric": ["Expenses (range)", "Sales (range)", "Cash Sales", "Net Cash"],
            "Value": [money(total_exp), money(total_sales), money(cash_sales), money(net_cash)],
        })
        b = df_to_pdf_bytes("DailyShop Summary", summary)
        st.download_button("Download PDF", data=b, file_name="summary.pdf", mime="application/pdf")


# -----------------------
# Tabs: Users (Admin only)
# -----------------------

def ui_users():
    st.subheader("👥 User Management (Admin Only)")
    users = load_users()

    st.info("Toggle per-user tab access by editing the 'tab' column (comma-separated keys): inv,pur,exp,ord,pay,rep,usr,menu,bal")

    # Add DELETE column for safe deletion
    if "DELETE" not in users.columns:
        users["DELETE"] = False

    edited = st.data_editor(
        users,
        key="users_editor",
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "DELETE": st.column_config.CheckboxColumn(default=False),
            "active": st.column_config.SelectboxColumn(options=["Yes","No"]),
            "role": st.column_config.SelectboxColumn(options=["admin","staff","customer"]),
        },
    )

    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button("💾 Save Users", type="primary", use_container_width=True):
            try:
                e = edited.copy()
                # Delete marked rows
                if "DELETE" in e.columns:
                    e["DELETE"] = e["DELETE"].fillna(False).astype(bool)
                    e = e[~e["DELETE"]].drop(columns=["DELETE"])
                # Ensure required cols and defaults
                for c in SCHEMA["users"]:
                    if c not in e.columns:
                        e[c] = ""
                # Fallbacks
                e["active"] = e["active"].replace({"": "Yes"})
                save_csv(e[SCHEMA["users"]], USERS_FILE)
                st.success("Users saved.")
                st.rerun()
            except Exception as ex:
                st.error(f"Save failed: {ex}")
    with c2:
        template = pd.DataFrame([
            {"user_id":"UCUST1","name":"Walk-in Guest","mobile":"","password":"","role":"customer","tab":"menu,bal","active":"Yes"}
        ], columns=SCHEMA["users"])        
        st.download_button("📥 Download Users Template", template.to_csv(index=False).encode("utf-8"), file_name="users_template.csv", mime="text/csv", use_container_width=True)
    with c3:
        up = st.file_uploader("Import Users CSV", type=["csv"], accept_multiple_files=False)
        if up is not None:
            try:
                du = pd.read_csv(up)
                for c in SCHEMA["users"]:
                    if c not in du.columns:
                        du[c] = ""
                save_csv(du[SCHEMA["users"]], USERS_FILE)
                st.success("Users imported.")
                st.rerun()
            except Exception as e:
                st.error(f"Import failed: {e}")

    st.markdown("#### Admin Tools")
    colA, colB = st.columns(2)
    with colA:
        if st.button("🔄 Reset Current Page (all roles)", use_container_width=True):
            # Soft reset: rerun only
            st.experimental_rerun()
    with colB:
        if st.button("🧨 Admin: Reset Full App Session", type="primary", use_container_width=True):
            # Admin-only full reset: clear session_state and last_tab memory
            st.session_state.clear()
            # wipe sessions file
            save_csv(csv_new(SCHEMA["sessions"]), SESSIONS_FILE)
            st.experimental_rerun()


# -----------------------
# Main App
# -----------------------

def app_ui():
    user = st.session_state.user

    # Header bar
    left, right = st.columns([0.75, 0.25])
    with left:
        st.markdown(f"<h3 style='margin:0;color:#0f172a'>{APP_TITLE}</h3>", unsafe_allow_html=True)
    with right:
        st.markdown(f"**{user['name']}** · {user['role']}")
        if st.button("Logout"):
            set_last_tab_for(user["mobile"], st.session_state.get("_active_tab_key", "dashboard"))
            st.session_state.user = None
            st.rerun()

    # Determine accessible tabs from role & per-user tab flags
    role = str(user.get("role","staff")).lower()
    allowed_keys = set(str(user.get("tab","inv,pur,exp,ord,pay,rep,menu,bal"))).replace(" ", "").split(",")
    allowed_keys = set([k for k in allowed_keys if k])

    # Tab map (key -> (label, function))
    TAB_MAP = {
        "dashboard": ("📊 Dashboard", None),
        "inv": ("📦 Inventory", ui_inventory),
        "pur": ("🧾 Purchases & Expenses", ui_purchases_expenses),
        "ord": ("🛒 Sales / Orders", ui_bookings_sales),
        "pay": ("💵 Payments", ui_payments),
        "rep": ("📈 Reports", ui_reports),
        "usr": ("👥 Users", ui_users),
        "menu": ("🍽️ Menu / Bookings", ui_bookings_sales),
        "bal": ("📒 My Balance", ui_payments),
    }

    # Role presets
    if role == "admin":
        available = ["dashboard","inv","pur","ord","pay","rep","usr","menu","bal"]
    elif role == "staff":
        available = ["dashboard","inv","pur","ord","pay","rep","menu","bal"]
    else:  # customer
        available = ["dashboard","menu","bal"]

    # Intersect with per-user allowed keys
    keys = [k for k in available if (k == "dashboard" or k in allowed_keys)]

    # Restore last tab per user
    last = get_last_tab_for(user["mobile"]) if user.get("mobile") else "dashboard"
    if last not in keys:
        last = "dashboard"

    labels = [TAB_MAP[k][0] for k in keys]
    default_index = keys.index(last) if last in keys else 0

    # Render tabs
    tabs = st.tabs(labels)
    for i, key in enumerate(keys):
        with tabs[i]:
            st.session_state["_active_tab_key"] = key
            set_last_tab_for(user["mobile"], key)
            if key == "dashboard":
                # Dashboard content
                inv = load_inventory()
                exp = load_csv(EXPENSES_FILE, SCHEMA["expenses"])    
                ords = load_csv(ORDERS_FILE, SCHEMA["orders"])    
                pays = load_csv(PAYMENTS_FILE, SCHEMA["payments"])  

                total_exp = exp["amount"].astype(float).sum() if not exp.empty else 0.0
                total_sales = ords["total"].astype(float).sum() if not ords.empty else 0.0
                stock_val = (inv["stock_qty"] * inv["rate"]).sum() if not inv.empty else 0.0
                pending = compute_balances()
                pending_total = pending["pending"].sum() if not pending.empty else 0.0

                c1,c2,c3,c4 = st.columns(4)
                with c1: kpi("Total Expenses", money(total_exp))
                with c2: kpi("Total Sales", money(total_sales))
                with c3: kpi("Stock Value (Est.)", money(stock_val))
                with c4: kpi("Pending Balances", money(pending_total))

                st.markdown("#### Low Stock Alerts")
                low = inv[inv["stock_qty"] < inv["min_qty"]]
                if low.empty:
                    st.info("No low-stock items.")
                else:
                    st.dataframe(low[["item_id","item_name","stock_qty","min_qty","sell_price"]], use_container_width=True)
            else:
                fn = TAB_MAP[key][1]
                if fn:
                    fn()


# -----------------------
# Entrypoint
# -----------------------
if st.session_state.user is None:
    login_page()
else:
    app_ui()
