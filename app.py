# app.py
import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime

st.set_page_config(page_title="DailyShop Dairy", layout="wide")

DATA_FILE = "DailyShop Dairy.csv"

# ------------------------------
# Load Data Function
# ------------------------------
def load_data():
    """Load inventory and expenses from the CSV file."""
    inventory = pd.DataFrame()
    expenses = pd.DataFrame()

    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE, encoding="utf-8")

            # normalize column names
            df.columns = df.columns.str.strip().str.lower()

            # inventory
            if all(col in df.columns for col in ["item", "quantity", "unit_price"]):
                inventory = df[["item", "quantity", "unit_price"]].copy()
                inventory["quantity"] = pd.to_numeric(inventory["quantity"], errors="coerce").fillna(0)
                inventory["unit_price"] = pd.to_numeric(inventory["unit_price"], errors="coerce").fillna(0)

            # expenses
            if all(col in df.columns for col in ["date", "expense", "amount"]):
                expenses = df[["date", "expense", "amount"]].copy()
                expenses["amount"] = pd.to_numeric(expenses["amount"], errors="coerce").fillna(0)

        except Exception as e:
            st.warning(f"❌ Error reading CSV: {e}")
    else:
        st.warning("⚠️ Data file not found, starting with empty records.")

    return inventory, expenses


# ------------------------------
# PDF Export
# ------------------------------
def make_simple_pdf_bytes(title, df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Title
    pdf.cell(200, 10, txt=title, ln=True, align="C")

    # Table
    if not df.empty:
        col_width = pdf.w / (len(df.columns) + 1)
        pdf.set_font("Arial", size=10)

        # Header
        for col in df.columns:
            pdf.cell(col_width, 10, str(col), border=1)
        pdf.ln()

        # Rows
        for _, row in df.iterrows():
            for val in row:
                safe_val = str(val).encode("latin-1", "replace").decode("latin-1")
                pdf.cell(col_width, 10, safe_val, border=1)
            pdf.ln()

    return pdf.output(dest="S").encode("latin-1")


# ------------------------------
# Authentication
# ------------------------------
def login():
    st.title("🛒 DailyShop Dairy")
    st.caption("Manage inventory, purchases, sales, expenses & cash")

    mobile = st.text_input("📱 Mobile Number", value="9999999999")
    password = st.text_input("🔑 Password", type="password")

    if st.button("Login"):
        if mobile == "9999999999" and password == "admin123":
            st.session_state["logged_in"] = True
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")


# ------------------------------
# Dashboard
# ------------------------------
def dashboard(inventory, expenses):
    st.subheader("📊 Dashboard")

    total_expenses = expenses["amount"].sum() if not expenses.empty else 0
    stock_value = (inventory["quantity"] * inventory["unit_price"]).sum() if not inventory.empty else 0

    c1, c2 = st.columns(2)
    c1.metric("₹ Total Expenses", f"{total_expenses:,.2f}")
    c2.metric("₹ Stock Value (Est.)", f"{stock_value:,.2f}")

    if not inventory.empty:
        st.write("⚠️ Low stock alerts")
        low_stock = inventory[inventory["quantity"] < 5]
        st.table(low_stock if not low_stock.empty else pd.DataFrame({"Message": ["No low-stock items."]}))


# ------------------------------
# Inventory Page
# ------------------------------
def inventory_page(inventory):
    st.subheader("📦 Inventory")
    st.dataframe(inventory)

    if st.download_button("⬇ Download Inventory CSV", inventory.to_csv(index=False).encode("utf-8"),
                          "inventory.csv", "text/csv"):
        st.success("Inventory downloaded!")

    if st.download_button("⬇ Download Inventory PDF",
                          make_simple_pdf_bytes("Inventory Report", inventory),
                          "inventory.pdf", "application/pdf"):
        st.success("Inventory PDF generated!")


# ------------------------------
# Expenses Page
# ------------------------------
def expenses_page(expenses):
    st.subheader("💰 Expenses")
    st.dataframe(expenses)

    if st.download_button("⬇ Download Expenses CSV", expenses.to_csv(index=False).encode("utf-8"),
                          "expenses.csv", "text/csv"):
        st.success("Expenses downloaded!")

    if st.download_button("⬇ Download Expenses PDF",
                          make_simple_pdf_bytes("Expenses Report", expenses),
                          "expenses.pdf", "application/pdf"):
        st.success("Expenses PDF generated!")


# ------------------------------
# Main App
# ------------------------------
def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login()
        return

    st.sidebar.title("🛒 DailyShop Dairy")
    st.sidebar.caption("Master Admin · admin")

    choice = st.sidebar.radio("Navigation", ["📊 Dashboard", "📦 Inventory", "💰 Expenses"])

    inventory, expenses = load_data()

    if choice == "📊 Dashboard":
        dashboard(inventory, expenses)
    elif choice == "📦 Inventory":
        inventory_page(inventory)
    elif choice == "💰 Expenses":
        expenses_page(expenses)


if __name__ == "__main__":
    main()
