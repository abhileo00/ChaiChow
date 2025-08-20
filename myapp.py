import os, hashlib
from datetime import datetime, date
import pandas as pd
import streamlit as st
from fpdf import FPDF

APP_TITLE = "🛒 DailyShop Dairy"
DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.csv")
INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.csv")
EXPENSES_FILE = os.path.join(DATA_DIR, "expenses.csv")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.csv")
PAYMENTS_FILE = os.path.join(DATA_DIR, "payments.csv")

SCHEMA = {
    "users": ["user_id","name","role","mobile","password_hash"],
    "inventory": ["item_id","item_name","category","unit","stock_qty","rate","min_qty","sell_price"],
    "expenses": ["date","type","category","item","item_id","qty","rate","amount","user_id","remarks"],
    "orders": ["date","customer_id","item_id","item_name","qty","rate","total","payment_mode","balance","user_id","remarks"],
    "payments": ["date","customer_id","amount","mode","remarks","user_id"]
}

for key, cols in SCHEMA.items():
    assert isinstance(cols, list) and all(isinstance(c, str) for c in cols), f"SCHEMA['{key}'] invalid"

st.set_page_config(page_title=APP_TITLE, layout="wide")

def safe_make_data_dir():
    if os.path.exists(DATA_DIR) and not os.path.isdir(DATA_DIR):
        os.remove(DATA_DIR)
    os.makedirs(DATA_DIR, exist_ok=True)

def new_df(cols): return pd.DataFrame(columns=cols)

def load_csv(path, cols):
    assert isinstance(cols, list) and all(isinstance(c, str) for c in cols)
    if os.path.exists(path):
        df = pd.read_csv(path, dtype=str)
        for c in cols:
            if c not in df.columns:
                df[c]=None
        return df[cols]
    return new_df(cols)

def save_csv(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")

def hash_pw(pw): return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def check_pw(raw, hashed): return hash_pw(raw)==hashed

def round_to_5(n):
    try: return int(5*round(float(n)/5.0))
    except: return 0

def bootstrap_files():
    safe_make_data_dir()
    if not os.path.exists(USERS_FILE):
        admin = pd.DataFrame([{"user_id":"admin","name":"Master Admin","role":"admin","mobile":"9999999999","password_hash":hash_pw("admin123")}], columns=SCHEMA["users"])
        save_csv(admin, USERS_FILE)
    for path,cols in [(INVENTORY_FILE, SCHEMA["inventory"]), (EXPENSES_FILE, SCHEMA["expenses"]), (ORDERS_FILE, SCHEMA["orders"]), (PAYMENTS_FILE, SCHEMA["payments"])]:
        if not os.path.exists(path):
            save_csv(new_df(cols), path)
        else:
            df = load_csv(path, cols)
            save_csv(df, path)

bootstrap_files()

# Business logic functions (get_user_by_mobile, list_inventory, record_order, etc.)
# Reimplement same as earlier code...

# UI Code with CSV upload integration and Menu filter
if "user" not in st.session_state: st.session_state.user=None

def login_page():
    st.title(APP_TITLE)
    st.info("Login (admin 9999999999 / admin123)")
    with st.form("login"):
        mobile = st.text_input("Mobile")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user = get_user_by_mobile(mobile)
            if user and check_pw(pw, user["password_hash"]):
                st.session_state.user=user; st.experimental_rerun()
            else: st.error("Invalid credentials")

def app_ui():
    user = st.session_state.user
    tabs = ["Dashboard","Inventory","Expenses","Menu / Booking","Payments","Reports"]
    if user["role"]=="admin": tabs.append("Users")
    tab_objs = st.tabs(tabs)

    # Inventory tab with CSV uploader
    with tab_objs[1]:
        st.header("Inventory Master")
        with st.expander("Upload Inventory CSV"):
            upload = st.file_uploader("Upload CSV (Item Name,Category,Unit,Suppliers Rate)", type="csv")
            if upload:
                df_imp = pd.read_csv(upload)
                req = {'Item Name','Category','Unit','Suppliers Rate'}
                if not req.issubset(set(df_imp.columns.str.strip())):
                    st.error("Missing columns: " + ", ".join(req-set(df_imp.columns.str.strip())))
                else:
                    st.dataframe(df_imp.head())
                    if st.button("Process Upload"):
                        inv=list_inventory(); added=updated=0
                        for _,r in df_imp.iterrows():
                            name,cat,unit,rate = r['Item Name'].strip(),r['Category'],r['Unit'],float(r['Suppliers Rate'])
                            iid = hashlib.md5(name.encode()).hexdigest()[:8]
                            existing = inv[inv['item_id']==iid]
                            if existing.empty:
                                upsert_inventory(iid,name,cat,unit,0,rate,0,rate); added+=1
                            else:
                                upsert_inventory(iid,name,cat,unit,existing.iloc[0]['stock_qty'],rate,existing.iloc[0]['min_qty'],existing.iloc[0]['sell_price']); updated+=1
                        st.success(f"Added {added}, Updated {updated}")
                        st.experimental_rerun()
        # ... existing inline data_editor code ...

    # Menu / Booking tab: filter category "Menu"
    with tab_objs[3]:
        st.header("Menu / Booking")
        inv=list_inventory()
        inv = inv[inv['category']=="Menu"]
        if inv.empty:
            st.info("No 'Menu' items available.")
        else:
            names = ["-- Select --"]+inv["item_name"].tolist()
            with st.form("booking"):
                cust = st.text_input("Customer mobile (Credit only)")
                item = st.selectbox("Item", names)
                qty = st.number_input("Qty", min_value=1, step=1, format="%d")
                pm = st.radio("Payment", ["Cash","Credit"])
                price = st.number_input("Price (₹)", min_value=0, step=5, format="%d", value=int(inv[inv["item_name"]==item]["sell_price"].iloc[0]) if item!="-- Select --" else 0)
                rem = st.text_input("Remarks")
                if st.form_submit_button("Book"):
                    if item=="-- Select --": st.error("Choose an item")
                    elif pm=="Credit" and not cust.strip(): st.error("Mobile required for Credit")
                    else:
                        cid = cust.strip() if pm=="Credit" else (cust.strip() or "GUEST")
                        pid = inv[inv["item_name"]==item]["item_id"].iloc[0]
                        ok,det = adjust_stock(pid,-qty)
                        if not ok:
                            have = inv[inv["item_id"]==pid]["stock_qty"].iloc[0]
                            insufficient_stock_dialog(item,have,qty)
                        else:
                            adjust_stock(pid,qty)
                            record_order(date.today(),cid,pid,item,qty,price,pm,user["user_id"],rem)
                            st.success("Booked successfully")
                            st.experimental_rerun()
        # ... display recent orders and exports ...

    if st.sidebar.button("Logout"):
        st.session_state.user=None
        st.experimental_rerun()

if st.session_state.user is None:
    login_page()
else:
    app_ui()
