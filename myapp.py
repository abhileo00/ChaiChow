# app.py - DailyShop Dairy
import streamlit as st
import pandas as pd
import os, hashlib, uuid, datetime

DATA_DIR = "data"

# ---------- Utility ----------
def ensure_data_files():
    os.makedirs(DATA_DIR, exist_ok=True)

    default_files = {
        "users.csv": ["user_id","name","mobile","password","role","tab","active"],
        "inventory.csv": ["item_id","item_name","area","category","unit","stock_qty","rate","min_qty","sell_price"],
        "purchases.csv": ["purchase_id","date","item_id","item_name","category","unit","qty","rate","total","remarks"],
        "expenses.csv": ["expense_id","date","category","item","amount","remarks"],
        "orders.csv": ["order_id","date","customer_name","mobile","item_id","item_name","category","qty","price","total","payment_mode","status"],
        "payments.csv": ["payment_id","date","customer_name","mobile","amount","remarks"],
    }

    for file, cols in default_files.items():
        path = os.path.join(DATA_DIR, file)
        if not os.path.exists(path):
            df = pd.DataFrame(columns=cols)
            df.to_csv(path, index=False)

    # default admin
    users = pd.read_csv(os.path.join(DATA_DIR,"users.csv"))
    if users.empty:
        admin_id = hashlib.md5("9999999999".encode()).hexdigest()
        users.loc[len(users)] = [admin_id,"Admin","9999999999","admin123","admin",
                                 "inv,pur,exp,ord,pay,rep,menu,bal,usr","Yes"]
        users.to_csv(os.path.join(DATA_DIR,"users.csv"), index=False)

def load_csv(name):
    return pd.read_csv(os.path.join(DATA_DIR, name))

def save_csv(name, df):
    df.to_csv(os.path.join(DATA_DIR, name), index=False)

def make_id(prefix="id"):
    return prefix + "_" + uuid.uuid4().hex[:8]

# ---------- Authentication ----------
def login_page():
    st.title("🔐 DailyShop Dairy - Login")

    mobile = st.text_input("Mobile")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        users = load_csv("users.csv")
        user = users[(users["mobile"]==mobile)&(users["password"]==password)&(users["active"]=="Yes")]
        if not user.empty:
            st.session_state.user = user.iloc[0].to_dict()
            st.session_state.logged_in = True
            if "last_tab" not in st.session_state:
                st.session_state.last_tab = "Dashboard"
            st.success("Login successful ✅")
            st.rerun()
        else:
            st.error("Invalid credentials or inactive user.")

# ---------- Tabs ----------
def dashboard():
    st.subheader("📊 Dashboard")
    st.write("Welcome,", st.session_state.user["name"])

def inventory_tab():
    st.subheader("📦 Inventory")
    df = load_csv("inventory.csv")
    st.data_editor(df, num_rows="dynamic")
    if st.button("Save Inventory"):
        save_csv("inventory.csv", df)
        st.success("Saved ✅")

def purchases_tab():
    st.subheader("🛒 Purchases")
    df = load_csv("purchases.csv")
    st.data_editor(df, num_rows="dynamic")
    if st.button("Save Purchases"):
        save_csv("purchases.csv", df)
        st.success("Saved ✅")

def expenses_tab():
    st.subheader("💸 Expenses")
    df = load_csv("expenses.csv")
    st.data_editor(df, num_rows="dynamic")
    if st.button("Save Expenses"):
        save_csv("expenses.csv", df)
        st.success("Saved ✅")

def orders_tab():
    st.subheader("🧾 Orders")
    df = load_csv("orders.csv")
    st.data_editor(df, num_rows="dynamic")
    if st.button("Save Orders"):
        save_csv("orders.csv", df)
        st.success("Saved ✅")

def payments_tab():
    st.subheader("💰 Payments")
    df = load_csv("payments.csv")
    st.data_editor(df, num_rows="dynamic")
    if st.button("Save Payments"):
        save_csv("payments.csv", df)
        st.success("Saved ✅")

def reports_tab():
    st.subheader("📑 Reports")
    st.info("Reports will be generated here.")

def menu_tab():
    st.subheader("🍽 Menu / Bookings")
    st.info("Customer order booking interface.")

def balance_tab():
    st.subheader("📉 Customer Balance")
    st.info("Balance/credit view for customers.")

def user_mgmt_tab():
    st.subheader("👥 User Management (Admin only)")
    df = load_csv("users.csv")
    st.data_editor(df, num_rows="dynamic")
    if st.button("Save Users"):
        save_csv("users.csv", df)
        st.success("Users saved ✅")

# ---------- Main ----------
def main_app():
    if not st.session_state.get("logged_in", False):
        login_page()
        return

    role = st.session_state.user["role"]
    allowed = st.session_state.user.get("tab","").replace(" ","").split(",")

    tab_map = {
        "Dashboard": dashboard,
        "inv": inventory_tab,
        "pur": purchases_tab,
        "exp": expenses_tab,
        "ord": orders_tab,
        "pay": payments_tab,
        "rep": reports_tab,
        "menu": menu_tab,
        "bal": balance_tab,
        "usr": user_mgmt_tab,
    }

    # Admin always full access
    if role=="admin":
        show_tabs = list(tab_map.keys())
    else:
        show_tabs = ["Dashboard"] + [k for k in tab_map if k in allowed]

    tabs = st.tabs(show_tabs)
    for i,tab_name in enumerate(show_tabs):
        with tabs[i]:
            tab_map[tab_name]()

    st.sidebar.success(f"Logged in as {st.session_state.user['name']} ({role})")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

# ---------- Run ----------
ensure_data_files()
main_app()
