import streamlit as st
import pandas as pd
import hashlib
import uuid
from datetime import datetime, date
from pathlib import Path
from io import BytesIO
from fpdf import FPDF

# =============================
# -------- CONFIG -------------
# =============================
APP_TITLE = "DailyShop Dairy"
DATA_DIR = Path("data")
FILES = {
    "users": DATA_DIR / "users.csv",
    "inventory": DATA_DIR / "inventory.csv",
    "purchases": DATA_DIR / "purchases.csv",
    "expenses": DATA_DIR / "expenses.csv",
    "orders": DATA_DIR / "orders.csv",
    "payments": DATA_DIR / "payments.csv",
    # session persistence of last visited tab per user
    "sessions": DATA_DIR / "user_sessions.csv",
}

# Price rounding step (₹). The prompt mentions ₹5 increments in multiple places; keep 5 by default.
PRICE_STEP = 5

# Tabs dictionary (stable keys)
TABS = {
    "Inventory": "inventory",
    "Purchases": "purchases",
    "Expenses": "expenses",
    "Bookings / Menu": "bookings",
    "Payments": "payments",
    "Reports": "reports",
    "User Management": "users_admin",
    "My Balance": "customer_balance",
    "Admin Tools": "admin_tools",
}

# =============================
# ------- UTILITIES -----------
# =============================

def md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:12]


def ts_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"


def round_to_step(value: float, step: int = PRICE_STEP) -> int:
    if pd.isna(value):
        return 0
    return int(round(value / step) * step)


def ensure_data_files():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Create empty dataframes with headers if missing
    if not FILES["users"].exists():
        df = pd.DataFrame([
            {
                "user_id": md5("9999999999"),
                "name": "Admin",
                "mobile": "9999999999",
                "password": "admin123",
                "role": "admin",
                # 'tab' = comma-separated list of allowed tab keys for non-admin users
                "tab": ",".join([TABS[t] for t in [
                    "Inventory","Purchases","Expenses","Bookings / Menu","Payments","Reports","My Balance"
                ]]),
                "active": "Yes",
            }
        ], columns=["user_id","name","mobile","password","role","tab","active"])
        df.to_csv(FILES["users"], index=False)

    if not FILES["inventory"].exists():
        inv_cols = [
            "item_id","item_name","Area","category","unit","stock_qty","rate","min_qty","sell_price"
        ]
        pd.DataFrame(columns=inv_cols).to_csv(FILES["inventory"], index=False)

    if not FILES["purchases"].exists():
        pd.DataFrame(columns=[
            "purchase_id","date","item_id","item_name","category","unit","qty","rate","total","remarks"
        ]).to_csv(FILES["purchases"], index=False)

    if not FILES["expenses"].exists():
        pd.DataFrame(columns=[
            "expense_id","date","category","item","amount","remarks"
        ]).to_csv(FILES["expenses"], index=False)

    if not FILES["orders"].exists():
        pd.DataFrame(columns=[
            "order_id","date","customer_name","mobile","item_id","item_name","category","qty","price","total","payment_mode","status"
        ]).to_csv(FILES["orders"], index=False)

    if not FILES["payments"].exists():
        pd.DataFrame(columns=[
            "payment_id","date","customer_name","mobile","amount","remarks"
        ]).to_csv(FILES["payments"], index=False)

    if not FILES["sessions"].exists():
        pd.DataFrame(columns=["user_id","last_tab","ts"]).to_csv(FILES["sessions"], index=False)


def load_csv(key: str) -> pd.DataFrame:
    ensure_data_files()
    path = FILES[key]
    try:
        df = pd.read_csv(path)
    except Exception:
        df = pd.DataFrame()
    return df


def save_csv(key: str, df: pd.DataFrame):
    path = FILES[key]
    df.to_csv(path, index=False)


def download_csv_button(df: pd.DataFrame, filename: str, label: str = "Download CSV"):
    return st.download_button(
        label=label,
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )


def df_to_pdf_bytes(df: pd.DataFrame, title: str = "Report") -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, title, ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Arial", size=10)
    # Table header
    col_widths = [max(20, min(60, len(str(c))*3)) for c in df.columns]
    for i, col in enumerate(df.columns):
        pdf.cell(col_widths[i], 8, str(col), border=1)
    pdf.ln()
    # Rows
    for _, row in df.iterrows():
        for i, col in enumerate(df.columns):
            pdf.cell(col_widths[i], 8, str(row[col]), border=1)
        pdf.ln()
    out = BytesIO()
    pdf.output(out)
    return out.getvalue()


def download_pdf_button(df: pd.DataFrame, filename: str, title: str):
    pdf_bytes = df_to_pdf_bytes(df, title)
    return st.download_button(
        label=f"Download PDF",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
    )


def set_last_tab(user_id: str, last_tab_key: str):
    sess = load_csv("sessions")
    now = datetime.now().isoformat()
    if user_id in set(sess["user_id"]) if not sess.empty else set():
        sess.loc[sess["user_id"] == user_id, ["last_tab","ts"]] = [last_tab_key, now]
    else:
        sess = pd.concat([sess, pd.DataFrame([{ "user_id": user_id, "last_tab": last_tab_key, "ts": now }])], ignore_index=True)
    save_csv("sessions", sess)


def get_last_tab(user_id: str) -> str:
    sess = load_csv("sessions")
    if sess.empty:
        return TABS["Bookings / Menu"]
    row = sess.loc[sess["user_id"] == user_id]
    if row.empty:
        return TABS["Bookings / Menu"]
    return str(row.iloc[0]["last_tab"]) or TABS["Bookings / Menu"]


# =============================
# ------- AUTH ----------------
# =============================

def authenticate(mobile: str, password: str):
    users = load_csv("users")
    if users.empty:
        return None
    row = users[(users["mobile"].astype(str) == str(mobile)) & (users["password"] == password) & (users["active"] == "Yes")]
    if row.empty:
        return None
    r = row.iloc[0]
    return {
        "user_id": str(r["user_id"]),
        "name": str(r["name"]),
        "mobile": str(r["mobile"]),
        "role": str(r["role"]),
        "tabs": set(str(r.get("tab", "")).split(",")) if pd.notna(r.get("tab", "")) else set(),
    }


def require_login():
    if "auth" not in st.session_state:
        st.session_state["auth"] = None
    if st.session_state["auth"] is None:
        st.title(APP_TITLE)
        st.subheader("Login")
        with st.form("login_form", clear_on_submit=False):
            mobile = st.text_input("Mobile", value="")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
        if submitted:
            user = authenticate(mobile, password)
            if user:
                st.session_state["auth"] = user
                # Jump to last tab if any
                last_tab = get_last_tab(user["user_id"]) if user["role"] != "admin" else TABS["Bookings / Menu"]
                st.session_state["active_tab_key"] = last_tab
                st.success(f"Welcome, {user['name']}!")
                st.rerun()
            else:
                st.error("Invalid credentials or inactive user.")
        st.stop()


# =============================
# ------- DATA HELPERS --------
# =============================

def get_inventory() -> pd.DataFrame:
    df = load_csv("inventory")
    for c in ["stock_qty","rate","min_qty","sell_price"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


def upsert_inventory(df: pd.DataFrame):
    # Validation & rounding rules
    if not df.empty:
        df["sell_price"] = df["sell_price"].apply(lambda x: round_to_step(pd.to_numeric(x, errors='coerce') or 0))
        for c in ["stock_qty","rate","min_qty"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        # Ensure DELETE present as bool if exists
        if "DELETE" in df.columns:
            df["DELETE"] = df["DELETE"].astype(bool)
            df = df.loc[~df["DELETE"]].drop(columns=["DELETE"]) if "DELETE" in df.columns else df
        # Ensure item_id exists
        df["item_id"] = df.apply(lambda r: r["item_id"] if pd.notna(r.get("item_id","")) and str(r["item_id"]).strip() != "" else md5(f"{r['item_name']}_{r['category']}") , axis=1)
    save_csv("inventory", df)


def add_purchase(item_row, qty: float, rate: float, remarks: str=""):
    inv = get_inventory()
    purchases = load_csv("purchases")
    pid = ts_id("PUR")
    total = float(qty) * float(rate)
    new_row = {
        "purchase_id": pid,
        "date": date.today().isoformat(),
        "item_id": item_row["item_id"],
        "item_name": item_row["item_name"],
        "category": item_row["category"],
        "unit": item_row["unit"],
        "qty": qty,
        "rate": rate,
        "total": total,
        "remarks": remarks,
    }
    purchases = pd.concat([purchases, pd.DataFrame([new_row])], ignore_index=True)
    save_csv("purchases", purchases)
    # Update stock
    inv.loc[inv["item_id"] == item_row["item_id"], "stock_qty"] += qty
    save_csv("inventory", inv)


def add_expense(category: str, item: str, amount: float, remarks: str=""):
    exp = load_csv("expenses")
    new_row = {
        "expense_id": ts_id("EXP"),
        "date": date.today().isoformat(),
        "category": category,
        "item": item,
        "amount": float(amount),
        "remarks": remarks,
    }
    exp = pd.concat([exp, pd.DataFrame([new_row])], ignore_index=True)
    save_csv("expenses", exp)


def add_order(customer_name: str, mobile: str, item_row, qty: float, price: float, payment_mode: str):
    inv = get_inventory()
    orders = load_csv("orders")
    # Stock check
    current_stock = float(inv.loc[inv["item_id"] == item_row["item_id"], "stock_qty"].iloc[0])
    if qty > current_stock:
        return False, f"Insufficient stock. Available: {current_stock} {item_row['unit']}"
    price = round_to_step(price)
    total = float(qty) * float(price)
    new_row = {
        "order_id": ts_id("ORD"),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "customer_name": customer_name,
        "mobile": mobile,
        "item_id": item_row["item_id"],
        "item_name": item_row["item_name"],
        "category": item_row["category"],
        "qty": qty,
        "price": price,
        "total": total,
        "payment_mode": payment_mode,
        "status": "Confirmed",
    }
    orders = pd.concat([orders, pd.DataFrame([new_row])], ignore_index=True)
    save_csv("orders", orders)
    # Reduce stock
    inv.loc[inv["item_id"] == item_row["item_id"], "stock_qty"] -= qty
    save_csv("inventory", inv)
    return True, "Order recorded."


def add_payment(customer_name: str, mobile: str, amount: float, remarks: str=""):
    pays = load_csv("payments")
    new_row = {
        "payment_id": ts_id("PAY"),
        "date": date.today().isoformat(),
        "customer_name": customer_name,
        "mobile": mobile,
        "amount": float(amount),
        "remarks": remarks,
    }
    pays = pd.concat([pays, pd.DataFrame([new_row])], ignore_index=True)
    save_csv("payments", pays)


def compute_balances() -> pd.DataFrame:
    orders = load_csv("orders")
    payments = load_csv("payments")
    # Only credit orders count towards balance
    if not orders.empty:
        credit = orders[orders["payment_mode"] == "Credit"].copy()
        credit_tot = credit.groupby(["mobile","customer_name"], dropna=False)["total"].sum().reset_index().rename(columns={"total":"credit_total"})
    else:
        credit_tot = pd.DataFrame(columns=["mobile","customer_name","credit_total"])    
    if not payments.empty:
        pay_tot = payments.groupby(["mobile","customer_name"], dropna=False)["amount"].sum().reset_index().rename(columns={"amount":"paid_total"})
    else:
        pay_tot = pd.DataFrame(columns=["mobile","customer_name","paid_total"])    
    df = pd.merge(credit_tot, pay_tot, on=["mobile","customer_name"], how="outer").fillna(0)
    if df.empty:
        df = pd.DataFrame(columns=["mobile","customer_name","credit_total","paid_total","pending"])
    df["pending"] = df.get("credit_total", 0) - df.get("paid_total", 0)
    return df.sort_values("pending", ascending=False)


# =============================
# ------- UI SECTIONS ---------
# =============================

def sidebar_user_info():
    auth = st.session_state.get("auth")
    if not auth:
        return
    st.sidebar.markdown(f"**User:** {auth['name']} ({auth['role']})")
    st.sidebar.markdown(f"**Mobile:** {auth['mobile']}")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.experimental_rerun()


def topnav(role: str, allowed_tab_keys: set):
    """Return selected tab key based on role & allowed tabs. Persist selection to sessions.csv."""
    all_items = []
    if role == "customer":
        all_items = ["Bookings / Menu", "My Balance"]
    elif role == "staff":
        all_items = ["Bookings / Menu","Inventory","Purchases","Expenses","Payments","Reports"]
    elif role == "admin":
        all_items = ["Bookings / Menu","Inventory","Purchases","Expenses","Payments","Reports","User Management","Admin Tools"]

    # filter by allowed tabs if non-admin
    labels = []
    for label in all_items:
        key = TABS[label]
        if role == "admin" or (allowed_tab_keys and key in allowed_tab_keys):
            labels.append(label)

    default_key = st.session_state.get("active_tab_key") or (TABS[labels[0]] if labels else TABS["Bookings / Menu"]) 

    # Render as pills
    cols = st.columns(len(labels)) if labels else []
    selected_key = default_key
    for i, label in enumerate(labels):
        key = TABS[label]
        if cols[i].button(label, use_container_width=True):
            selected_key = key
    st.session_state["active_tab_key"] = selected_key

    # persist selection
    auth = st.session_state.get("auth")
    if auth:
        set_last_tab(auth["user_id"], selected_key)
    return selected_key


# ---------- Inventory ----------

def ui_inventory():
    st.subheader("Inventory")
    inv = get_inventory()

    # Low stock alert
    low = inv[(inv["stock_qty"] < inv["min_qty"]) & (inv["min_qty"] > 0)] if not inv.empty else pd.DataFrame()
    if not low.empty:
        st.warning(f"Low stock alerts: {len(low)} items below minimum.")
        with st.expander("View Low Stock Items"):
            st.dataframe(low[["item_name","stock_qty","min_qty","unit"]])

    # Sample template download
    sample = pd.DataFrame([
        {"item_id":"","item_name":"Milk","Area":"Dairy","category":"Menu","unit":"Ltr","stock_qty":50,"rate":48,"min_qty":10,"sell_price":50},
        {"item_id":"","item_name":"Curd","Area":"Dairy","category":"Menu","unit":"Kg","stock_qty":20,"rate":80,"min_qty":5,"sell_price":85},
    ], columns=["item_id","item_name","Area","category","unit","stock_qty","rate","min_qty","sell_price"])
    st.download_button("Download Inventory Template CSV", sample.to_csv(index=False).encode("utf-8"), file_name="inventory_template.csv")

    st.markdown("**Inline Edit Inventory** (toggle DELETE to remove rows; sell price auto-rounded to ₹5)")
    edit_df = inv.copy()
    edit_df["DELETE"] = False
    edited = st.data_editor(edit_df, num_rows="dynamic", use_container_width=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Save Inventory Changes", type="primary"):
            try:
                upsert_inventory(edited)
                st.success("Inventory saved.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")
    with c2:
        uploaded = st.file_uploader("Import Inventory CSV", type=["csv"], accept_multiple_files=False)
        if uploaded is not None:
            try:
                new_df = pd.read_csv(uploaded)
                # Conform columns
                needed = ["item_id","item_name","Area","category","unit","stock_qty","rate","min_qty","sell_price"]
                for col in needed:
                    if col not in new_df.columns:
                        new_df[col] = None
                new_df = new_df[needed]
                merged = pd.concat([inv, new_df], ignore_index=True)
                upsert_inventory(merged)
                st.success("Imported and saved.")
                st.rerun()
            except Exception as e:
                st.error(f"Import failed: {e}")
    with c3:
        download_csv_button(inv, "inventory.csv")


# ---------- Purchases ----------

def ui_purchases():
    st.subheader("Purchases (Stock In)")
    inv = get_inventory()

    if inv.empty:
        st.info("No inventory yet. Please add items in Inventory tab.")
        return

    # Selection: Category -> Item
    col1, col2, col3 = st.columns(3)
    with col1:
        categories = sorted(inv["category"].dropna().unique().tolist())
        sel_cat = st.selectbox("Category", options=categories)
    items = inv[inv["category"] == sel_cat]
    with col2:
        item_name = st.selectbox("Item", options=items["item_name"].tolist())
    item_row = items[items["item_name"] == item_name].iloc[0].to_dict()

    with col3:
        st.write("**Live Stock**")
        st.metric(label=f"{item_row['item_name']} ({item_row['unit']})", value=float(item_row['stock_qty']))

    col4, col5, col6 = st.columns(3)
    with col4:
        qty = st.number_input("Quantity", min_value=0.0, step=1.0)
    with col5:
        rate = st.number_input("Purchase Rate (₹)", min_value=0.0, step=1.0, value=float(item_row.get("rate", 0)))
    with col6:
        remarks = st.text_input("Remarks", value="")

    if st.button("Add Purchase", type="primary"):
        if qty <= 0 or rate <= 0:
            st.error("Enter valid quantity and rate.")
        else:
            add_purchase(item_row, qty, rate, remarks)
            st.success("Purchase added & stock updated.")
            st.rerun()

    # Table
    p = load_csv("purchases")
    st.markdown("### Recent Purchases")
    st.dataframe(p.tail(50), use_container_width=True)
    c1, c2 = st.columns(2)
    with c1:
        download_csv_button(p, "purchases.csv")
    with c2:
        download_pdf_button(p, "purchases.pdf", "Purchases Report")


# ---------- Expenses ----------

def ui_expenses():
    st.subheader("Expenses")
    col1, col2, col3 = st.columns(3)
    with col1:
        exp_cat = st.text_input("Expense Category", value="Transport")
    with col2:
        exp_item = st.text_input("Item/Description", value="")
    with col3:
        exp_amt = st.number_input("Amount (₹)", min_value=0.0, step=1.0)
    rem = st.text_input("Remarks", value="")
    if st.button("Add Expense", type="primary"):
        if exp_amt <= 0:
            st.error("Amount must be > 0")
        else:
            add_expense(exp_cat, exp_item, exp_amt, rem)
            st.success("Expense added.")
            st.rerun()

    e = load_csv("expenses")
    st.markdown("### Recent Expenses")
    st.dataframe(e.tail(100), use_container_width=True)
    c1, c2 = st.columns(2)
    with c1:
        download_csv_button(e, "expenses.csv")
    with c2:
        download_pdf_button(e, "expenses.pdf", "Expenses Report")


# ---------- Bookings / Menu ----------

def ui_bookings():
    st.subheader("Bookings / Menu (Only category == 'Menu')")
    inv = get_inventory()
    menu_df = inv[inv["category"] == "Menu"].copy()

    if menu_df.empty:
        st.info("No 'Menu' items available in Inventory.")
        return

    # Two-step dropdown: Category -> Item (categories will all be 'Menu', so we filter by Area instead for utility)
    col1, col2 = st.columns(2)
    with col1:
        areas = ["ALL"] + sorted(menu_df["Area"].dropna().unique().tolist())
        sel_area = st.selectbox("Area/Section", options=areas)
    items_filtered = menu_df if sel_area == "ALL" else menu_df[menu_df["Area"] == sel_area]
    with col2:
        item_name = st.selectbox("Item", options=items_filtered["item_name"].tolist())
    item_row = items_filtered[items_filtered["item_name"] == item_name].iloc[0].to_dict()

    st.metric(label=f"Live Stock: {item_row['item_name']} ({item_row['unit']})", value=float(item_row['stock_qty']))

    qty = st.number_input("Quantity", min_value=1.0, step=1.0)
    price_default = float(item_row.get("sell_price", 0))
    price = st.number_input("Price (₹)", min_value=0.0, step=1.0, value=round_to_step(price_default))

    pay_mode = st.radio("Payment Mode", options=["Cash","Credit"], horizontal=True)

    # Customer selection rules
    users = load_csv("users")
    customer_rows = users[(users["role"] == "customer") & (users["active"] == "Yes")]
    customer_list = [f"{r['name']} | {r['mobile']}" for _, r in customer_rows.iterrows()]

    if pay_mode == "Cash":
        cust_name = st.text_input("Customer Name (optional)", value="Guest")
        mobile = st.text_input("Mobile (optional)", value="")
    else:
        sel = st.selectbox("Select Customer (Registered)", options=customer_list if len(customer_list)>0 else ["-- No customers --"])
        if "|" in sel:
            parts = [p.strip() for p in sel.split("|")]
            cust_name, mobile = parts[0], parts[1]
        else:
            cust_name, mobile = "", ""

    if st.button("Book / Record Sale", type="primary"):
        if qty <= 0:
            st.error("Quantity must be > 0")
        elif pay_mode == "Credit" and (mobile == "" or cust_name == ""):
            st.error("For Credit bookings, select a registered customer.")
        else:
            ok, msg = add_order(cust_name if pay_mode=="Credit" else (cust_name or "Guest"), mobile if pay_mode=="Credit" else "", item_row, qty, price, pay_mode)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    # Recent orders
    orders = load_csv("orders")
    st.markdown("### Recent Bookings")
    st.dataframe(orders.tail(100), use_container_width=True)
    c1, c2 = st.columns(2)
    with c1:
        download_csv_button(orders, "orders.csv")
    with c2:
        download_pdf_button(orders, "orders.pdf", "Orders Report")


# ---------- Payments ----------

def ui_payments():
    st.subheader("Payments")
    balances = compute_balances()

    # Payment form
    users = load_csv("users")
    customer_rows = users[(users["role"] == "customer") & (users["active"] == "Yes")]
    customer_list = [f"{r['name']} | {r['mobile']}" for _, r in customer_rows.iterrows()]

    col1, col2 = st.columns(2)
    with col1:
        sel = st.selectbox("Select Customer", options=customer_list if len(customer_list)>0 else ["-- No customers --"])
    if "|" in sel:
        parts = [p.strip() for p in sel.split("|")]
        cust_name, mobile = parts[0], parts[1]
    else:
        cust_name, mobile = "", ""
    with col2:
        amount = st.number_input("Payment Amount (₹)", min_value=0.0, step=1.0)
    remarks = st.text_input("Remarks", value="Settlement")

    if st.button("Record Payment", type="primary"):
        if amount <= 0:
            st.error("Amount must be > 0")
        elif mobile == "":
            st.error("Select a valid customer.")
        else:
            add_payment(cust_name, mobile, amount, remarks)
            st.success("Payment recorded.")
            st.rerun()

    st.markdown("### Customer Balances")
    st.dataframe(balances, use_container_width=True)
    c1, c2 = st.columns(2)
    with c1:
        download_csv_button(balances, "balances.csv", label="Download Balances CSV")
    with c2:
        download_pdf_button(balances, "balances.pdf", "Customer Balances")


# ---------- Reports ----------

def ui_reports():
    st.subheader("Reports")
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("From", value=date.today().replace(day=1))
    with col2:
        end = st.date_input("To", value=date.today())

    orders = load_csv("orders")
    expenses = load_csv("expenses")
    payments = load_csv("payments")

    def filter_by_date(df, col="date"):
        if df.empty:
            return df
        # coerce datetime
        d = df.copy()
        try:
            d[col] = pd.to_datetime(d[col])
        except Exception:
            pass
        return d[(d[col] >= pd.to_datetime(start)) & (d[col] <= pd.to_datetime(end))]

    f_orders = filter_by_date(orders, "date")
    f_exp = filter_by_date(expenses, "date")
    f_pay = filter_by_date(payments, "date")

    sales_total = float(f_orders["total"].sum()) if not f_orders.empty else 0.0
    exp_total = float(f_exp["amount"].sum()) if not f_exp.empty else 0.0
    cash_sales = float(f_orders[f_orders["payment_mode"] == "Cash"]["total"].sum()) if not f_orders.empty else 0.0
    net_cash = cash_sales - exp_total

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Sales (₹)", f"{sales_total:,.0f}")
    k2.metric("Expenses (₹)", f"{exp_total:,.0f}")
    k3.metric("Cash Sales (₹)", f"{cash_sales:,.0f}")
    k4.metric("Net Cash (₹)", f"{net_cash:,.0f}")

    st.markdown("### Sales")
    st.dataframe(f_orders, use_container_width=True)
    st.markdown("### Expenses")
    st.dataframe(f_exp, use_container_width=True)
    st.markdown("### Payments")
    st.dataframe(f_pay, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        download_csv_button(f_orders, "sales_filtered.csv", label="Sales CSV")
    with c2:
        download_csv_button(f_exp, "expenses_filtered.csv", label="Expenses CSV")
    with c3:
        download_csv_button(f_pay, "payments_filtered.csv", label="Payments CSV")

    st.divider()
    st.markdown("### Balances Snapshot")
    bal = compute_balances()
    st.dataframe(bal, use_container_width=True)


# ---------- User Management (Admin) ----------

def ui_users_admin():
    st.subheader("User Management (Admin)")
    users = load_csv("users")

    with st.expander("Add New User"):
        c1,c2,c3,c4 = st.columns(4)
        with c1:
            name = st.text_input("Name")
        with c2:
            mobile = st.text_input("Mobile")
        with c3:
            password = st.text_input("Password", value="pass123")
        with c4:
            role = st.selectbox("Role", options=["staff","customer","admin"], index=0)
        # Tab access control (stored in 'tab' column as comma-separated keys)
        allowed = []
        st.markdown("**Tab Access (for non-admin):**")
        tab_cols = st.columns(4)
        checks = [
            ("Bookings / Menu", tab_cols[0].checkbox("Bookings / Menu", value=True)),
            ("Inventory", tab_cols[1].checkbox("Inventory", value=(role=="staff"))),
            ("Purchases", tab_cols[2].checkbox("Purchases", value=(role=="staff"))),
            ("Expenses", tab_cols[3].checkbox("Expenses", value=(role=="staff"))),
        ]
        tab_cols2 = st.columns(4)
        checks += [
            ("Payments", tab_cols2[0].checkbox("Payments", value=(role=="staff"))),
            ("Reports", tab_cols2[1].checkbox("Reports", value=(role=="staff"))),
            ("My Balance", tab_cols2[2].checkbox("My Balance", value=(role=="customer"))),
        ]
        if st.button("Create User", type="primary"):
            if not name or not mobile:
                st.error("Name and Mobile are required.")
            else:
                user_id = md5(str(mobile))
                allowed_keys = [TABS[label] for label, ok in checks if ok]
                new_row = {
                    "user_id": user_id,
                    "name": name,
                    "mobile": mobile,
                    "password": password,
                    "role": role,
                    "tab": ",".join(allowed_keys),
                    "active": "Yes",
                }
                users = pd.concat([users, pd.DataFrame([new_row])], ignore_index=True)
                save_csv("users", users)
                st.success("User created.")
                st.rerun()

    st.markdown("### Edit Users (inline)")
    users_edit = users.copy()
    users_edit["DELETE"] = False
    edited = st.data_editor(users_edit, num_rows="dynamic", use_container_width=True, disabled=["user_id"]) 

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Save Users", type="primary"):
            try:
                if "DELETE" in edited.columns:
                    edited["DELETE"] = edited["DELETE"].astype(bool)
                    edited = edited.loc[~edited["DELETE"]].drop(columns=["DELETE"]) 
                save_csv("users", edited)
                st.success("Users saved.")
                st.rerun()
            except Exception as e:
                st.error(f"Save failed: {e}")
    with c2:
        master_pass = st.text_input("Set All Passwords To", value="", type="password")
        if st.button("Mass Reset Passwords"):
            if master_pass.strip() == "":
                st.error("Enter a password.")
            else:
                users["password"] = master_pass
                save_csv("users", users)
                st.success("All passwords reset.")
    with c3:
        download_csv_button(users, "users.csv", label="Download Users CSV")


# ---------- Customer Balance (Customer role) ----------

def ui_customer_balance():
    auth = st.session_state.get("auth")
    if not auth:
        st.stop()
    st.subheader("My Balance & History")

    orders = load_csv("orders")
    payments = load_csv("payments")
    my_orders = orders[(orders["mobile"].astype(str) == str(auth["mobile"]))]
    my_pay = payments[(payments["mobile"].astype(str) == str(auth["mobile"]))]

    credit_total = float(my_orders[my_orders["payment_mode"] == "Credit"]["total"].sum()) if not my_orders.empty else 0.0
    paid_total = float(my_pay["amount"].sum()) if not my_pay.empty else 0.0
    pending = credit_total - paid_total

    k1,k2,k3 = st.columns(3)
    k1.metric("Credit (₹)", f"{credit_total:,.0f}")
    k2.metric("Paid (₹)", f"{paid_total:,.0f}")
    k3.metric("Pending (₹)", f"{pending:,.0f}")

    st.markdown("### My Credit Orders")
    st.dataframe(my_orders, use_container_width=True)
    st.markdown("### My Payments")
    st.dataframe(my_pay, use_container_width=True)


# ---------- Admin Tools ----------

def ui_admin_tools():
    st.subheader("Admin Tools")
    st.write("Only Admin can reset UI states.")
    if st.button("Reset My Current Page State"):
        # Soft reset current page state (keep auth)
        keep = st.session_state.get("auth")
        last_tab = st.session_state.get("active_tab_key")
        st.session_state.clear()
        st.session_state["auth"] = keep
        st.session_state["active_tab_key"] = last_tab
        st.success("Current page state cleared.")
    if st.button("Full App UI Reset (All Users)", type="primary"):
        # Clear session persistence file
        pd.DataFrame(columns=["user_id","last_tab","ts"]).to_csv(FILES["sessions"], index=False)
        st.success("All users' last-tab memory cleared.")


# =============================
# -------- MAIN APP -----------
# =============================

def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    ensure_data_files()

    require_login()
    sidebar_user_info()

    auth = st.session_state.get("auth")
    role = auth["role"]
    allowed_keys = auth["tabs"] if auth["role"] != "admin" else set()

    active_key = topnav(role, allowed_keys)

    # Route to sections
    if active_key == TABS["Inventory"] and role in ["admin","staff"]:
        ui_inventory()
    elif active_key == TABS["Purchases"] and role in ["admin","staff"]:
        ui_purchases()
    elif active_key == TABS["Expenses"] and role in ["admin","staff"]:
        ui_expenses()
    elif active_key == TABS["Bookings / Menu"]:
        ui_bookings()
    elif active_key == TABS["Payments"] and role in ["admin","staff"]:
        ui_payments()
    elif active_key == TABS["Reports"] and role in ["admin","staff"]:
        ui_reports()
    elif active_key == TABS["User Management"] and role == "admin":
        ui_users_admin()
    elif active_key == TABS["My Balance"] and role == "customer":
        ui_customer_balance()
    elif active_key == TABS["Admin Tools"] and role == "admin":
        ui_admin_tools()
    else:
        st.info("You do not have access to this tab.")


if __name__ == "__main__":
    main()
