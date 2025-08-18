import streamlit as st
import pandas as pd
import os
from fpdf import FPDF

# ===================== #
# Utility Functions
# ===================== #

def load_users(file_path="users.csv"):
    """Load users from CSV file"""
    if os.path.exists(file_path):
        try:
            users_df = pd.read_csv(file_path, dtype=str)
            users = {}
            for _, row in users_df.iterrows():
                users[row["mobile"]] = {
                    "password": row["password"],
                    "role": row.get("role", "staff")  # default role = staff
                }
            return users
        except Exception as e:
            st.error(f"❌ Failed to load users.csv: {e}")
            return {}
    else:
        st.warning("⚠️ users.csv not found. No users available.")
        return {}

def load_shop_data(file_path="DailyShop Dairy.csv"):
    """Load shop data from CSV"""
    if os.path.exists(file_path):
        try:
            return pd.read_csv(file_path)
        except Exception as e:
            st.error(f"❌ Failed to load shop data: {e}")
            return pd.DataFrame()
    else:
        st.warning("⚠️ DailyShop Dairy.csv not found. Starting empty.")
        return pd.DataFrame()

def make_simple_pdf_bytes(df, title="Report"):
    """Generate a PDF report from dataframe"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt=title, ln=True, align="C")

    # Table headers
    col_width = pdf.w / (len(df.columns) + 1)
    for col in df.columns:
        pdf.cell(col_width, 10, col, border=1)
    pdf.ln()

    # Table rows
    for _, row in df.iterrows():
        for item in row:
            text = str(item)
            # Handle unicode by replacing unsupported chars
            safe_text = text.encode("latin-1", "replace").decode("latin-1")
            pdf.cell(col_width, 10, safe_text, border=1)
        pdf.ln()

    return pdf.output(dest="S").encode("latin-1")

# ===================== #
# App Logic
# ===================== #

st.set_page_config(page_title="DailyShop Dairy", layout="wide")
st.title("🛒 DailyShop Dairy")
st.caption("Manage inventory, purchases, sales, expenses & cash")

# Load users
USERS = load_users()

# Authentication
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None

if not st.session_state["logged_in"]:
    st.subheader("🔐 Login")

    mobile = st.text_input("📱 Mobile Number")
    password = st.text_input("🔑 Password", type="password")

    if st.button("Login"):
        if mobile in USERS and USERS[mobile]["password"] == password:
            st.session_state["logged_in"] = True
            st.session_state["user_role"] = USERS[mobile]["role"]
            st.success(f"✅ Welcome {st.session_state['user_role'].capitalize()}!")
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

else:
    role = st.session_state["user_role"]
    st.sidebar.title(f"👤 {role.capitalize()} Panel")
    st.sidebar.button("Logout", on_click=lambda: st.session_state.update({"logged_in": False, "user_role": None}))

    # Load shop data
    data = load_shop_data()

    # Dashboard
    st.subheader("📊 Dashboard")
    if data.empty:
        st.info("No data available yet.")
    else:
        st.dataframe(data)

        # PDF Report button
        if st.button("📄 Download Report as PDF"):
            pdf_bytes = make_simple_pdf_bytes(data, title="DailyShop Dairy Report")
            st.download_button("⬇️ Download PDF", pdf_bytes, "report.pdf", "application/pdf")

    # Role-based Access
    if role == "master":
        st.subheader("⚙️ Admin Features")
        st.write("Add user management, delete entries, etc.")
    else:
        st.subheader("👥 Staff Access")
        st.write("Limited access to sales & inventory.")
