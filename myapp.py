import streamlit as st
import pandas as pd

# =======================
# Load Users from CSV
# =======================
def load_users():
    try:
        return pd.read_csv("users.csv").to_dict("records")
    except FileNotFoundError:
        st.error("users.csv not found. Please create it with columns: mobile,password,role")
        return []

# =======================
# Authenticate
# =======================
def authenticate_user(mobile, password, users):
    for u in users:
        if str(u["mobile"]) == str(mobile) and str(u["password"]) == str(password):
            return u
    return None

# =======================
# Tabs rendering
# =======================
def render_dashboard():
    st.subheader("📊 Dashboard")
    st.info("Welcome to DailyShop Dairy")

def render_inventory():
    st.subheader("📦 Inventory")
    st.write("Inventory management page...")

def render_purchase():
    st.subheader("🛒 Purchase")
    st.write("Purchase records page...")

def render_expenses():
    st.subheader("💰 Expenses")
    st.write("Expense tracking page...")

def render_orders():
    st.subheader("🧾 Orders")
    st.write("Orders management page...")

def render_payments():
    st.subheader("💳 Payments")
    st.write("Customer payments page...")

def render_reports():
    st.subheader("📑 Reports")
    st.write("Reports page...")

def render_users():
    st.subheader("👥 User Management")
    st.write("Manage users here...")

# =======================
# Main App
# =======================
def app():
    st.set_page_config(page_title="DailyShop Dairy", layout="wide")

    # session init
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.active_tab = "Dashboard"

    users = load_users()

    # -----------------------
    # Login page
    # -----------------------
    if not st.session_state.authenticated:
        st.title("DailyShop Dairy - Login")

        mobile = st.text_input("Mobile")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            user = authenticate_user(mobile, password, users)
            if user:
                st.session_state.authenticated = True
                st.session_state.user = user
                st.success(f"Welcome {user['role'].capitalize()}")
                st.rerun()
            else:
                st.error("Invalid credentials or inactive user.")
        return

    # -----------------------
    # Logged In Section
    # -----------------------
    user = st.session_state.user
    role = user.get("role", "").lower()

    st.sidebar.success(f"Logged in as: {role.capitalize()} ({user['mobile']})")
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.rerun()

    # Tabs based on role
    if role == "master":
        tabs = ["Dashboard", "Inventory", "Purchase", "Expenses", "Orders", "Payments", "Reports", "Users"]
    else:  # staff
        tabs = ["Dashboard", "Orders", "Payments", "Reports"]

    selected = st.tabs(tabs)

    # Render selected tab
    for i, tab in enumerate(tabs):
        with selected[i]:
            if tab == "Dashboard":
                render_dashboard()
            elif tab == "Inventory":
                render_inventory()
            elif tab == "Purchase":
                render_purchase()
            elif tab == "Expenses":
                render_expenses()
            elif tab == "Orders":
                render_orders()
            elif tab == "Payments":
                render_payments()
            elif tab == "Reports":
                render_reports()
            elif tab == "Users":
                render_users()

# =======================
# Run App
# =======================
if __name__ == "__main__":
    app()
