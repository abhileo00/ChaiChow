import streamlit as st
import pandas as pd
import os
from datetime import datetime

# -----------------------------
# Config
# -----------------------------
st.set_page_config(page_title="DailyShop Dairy", page_icon="🛒", layout="wide")

DATA_DIR = "data"
INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.csv")
EXPENSES_FILE = os.path.join(DATA_DIR, "expenses.csv")
IMPORT_FILE = os.path.join(DATA_DIR, "DailyShop Dairy.csv")

# -----------------------------
# Helpers
# -----------------------------
def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_csv(path, cols):
    if os.path.exists(path):
        return pd.read_csv(path)
    else:
        return pd.DataFrame(columns=cols)

def save_csv(df, path):
    df.to_csv(path, index=False)

def import_from_master_csv():
    if not os.path.exists(IMPORT_FILE):
        return False, "No import file found."

    try:
        df = pd.read_csv(IMPORT_FILE)

        # Ensure required columns exist
        required_cols = ["Date", "Item", "Category", "Qty", "Unit Price", "Total Amount", "Type"]
        for col in required_cols:
            if col not in df.columns:
                return False, f"Missing column in import: {col}"

        # Inventory: filter purchases
        inv = df[df["Type"].str.lower() == "purchase"].copy()
        inv = inv[["Item", "Category", "Qty", "Unit Price"]]
        inv.rename(columns={"Qty": "Stock", "Unit Price": "Price"}, inplace=True)
        save_csv(inv, INVENTORY_FILE)

        # Expenses: filter expenses
        exp = df[df["Type"].str.lower() == "expense"].copy()
        exp = exp[["Date", "Item", "Total Amount"]]
        exp.rename(columns={"Total Amount": "Amount"}, inplace=True)
        save_csv(exp, EXPENSES_FILE)

        return True, "Import successful."

    except Exception as e:
        return False, f"Error: {str(e)}"

# -----------------------------
# Authentication
# -----------------------------
def login():
    st.subheader("🔐 Admin Login")
    mobile = st.text_input("📱 Mobile Number")
    password = st.text_input("🔑 Password", type="password")
    if st.button("Login"):
        if mobile == "9999999999" and password == "admin":
            st.session_state["logged_in"] = True
            st.success("✅ Welcome Master Admin!")
        else:
            st.error("❌ Invalid credentials.")

# -----------------------------
# Pages
# -----------------------------
def dashboard():
    st.subheader("📊 Dashboard")

    inv = load_csv(INVENTORY_FILE, ["Item", "Category", "Stock", "Price"])
    exp = load_csv(EXPENSES_FILE, ["Date", "Item", "Amount"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Items", len(inv))
    c2.metric("Total Stock", inv["Stock"].sum() if not inv.empty else 0)
    c3.metric("Total Expenses", exp["Amount"].sum() if not exp.empty else 0)

    st.write("### Inventory Snapshot")
    st.dataframe(inv)

    st.write("### Recent Expenses")
    st.dataframe(exp.tail(5))

def inventory_page():
    st.subheader("📦 Inventory Management")
    df = load_csv(INVENTORY_FILE, ["Item", "Category", "Stock", "Price"])

    with st.form("add_item"):
        item = st.text_input("Item")
        category = st.text_input("Category")
        stock = st.number_input("Stock", min_value=0, step=1)
        price = st.number_input("Price", min_value=0.0, step=0.5)
        submitted = st.form_submit_button("➕ Add Item")
        if submitted and item:
            df = pd.concat([df, pd.DataFrame([[item, category, stock, price]], 
                                             columns=["Item", "Category", "Stock", "Price"])], ignore_index=True)
            save_csv(df, INVENTORY_FILE)
            st.success(f"Item {item} added!")

    st.write("### Current Inventory")
    st.dataframe(df)

def expenses_page():
    st.subheader("💸 Expense Management")
    df = load_csv(EXPENSES_FILE, ["Date", "Item", "Amount"])

    with st.form("add_expense"):
        date = st.date_input("Date", datetime.today())
        item = st.text_input("Expense Item")
        amount = st.number_input("Amount", min_value=0.0, step=1.0)
        submitted = st.form_submit_button("➕ Add Expense")
        if submitted and item:
            df = pd.concat([df, pd.DataFrame([[date, item, amount]], 
                                             columns=["Date", "Item", "Amount"])], ignore_index=True)
            save_csv(df, EXPENSES_FILE)
            st.success(f"Expense {item} added!")

    st.write("### Expenses List")
    st.dataframe(df)

def reports_page():
    st.subheader("📑 Reports")
    inv = load_csv(INVENTORY_FILE, ["Item", "Category", "Stock", "Price"])
    exp = load_csv(EXPENSES_FILE, ["Date", "Item", "Amount"])

    if not exp.empty:
        exp["Date"] = pd.to_datetime(exp["Date"])
        daily = exp.groupby(exp["Date"].dt.date)["Amount"].sum()
        st.write("### Daily Expense Report")
        st.dataframe(daily)

        weekly = exp.groupby(exp["Date"].dt.to_period("W"))["Amount"].sum()
        st.write("### Weekly Expense Report")
        st.dataframe(weekly)

        monthly = exp.groupby(exp["Date"].dt.to_period("M"))["Amount"].sum()
        st.write("### Monthly Expense Report")
        st.dataframe(monthly)
    else:
        st.info("No expenses found.")

def import_page():
    st.subheader("📥 Import Data")
    if st.button("Run Import from DailyShop Dairy.csv"):
        success, msg = import_from_master_csv()
        if success:
            st.success(msg)
        else:
            st.error(msg)

# -----------------------------
# Main
# -----------------------------
def main():
    ensure_data_dir()
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    st.title("🛒 DailyShop Dairy")
    st.caption("Manage inventory, purchases, sales, expenses & cash")

    if not st.session_state["logged_in"]:
        login()
        return

    menu = st.tabs(["🏠 Dashboard", "📦 Inventory", "💸 Expenses", "📑 Reports", "📥 Import Data"])

    with menu[0]:
        dashboard()
    with menu[1]:
        inventory_page()
    with menu[2]:
        expenses_page()
    with menu[3]:
        reports_page()
    with menu[4]:
        import_page()

if __name__ == "__main__":
    main()
