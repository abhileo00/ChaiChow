import streamlit as st
import pandas as pd
from utils.db import get_db_connection
from datetime import date

def manage_expenses():
    st.header("Expense Management")
    
    with st.form("expense_form"):
        description = st.text_input("Expense Description")
        amount = st.number_input("Amount", min_value=0.0, step=0.1)
        expense_date = st.date_input("Date", date.today())
        
        if st.form_submit_button("Add Expense"):
            if not description or amount <= 0:
                st.error("Please fill all fields correctly")
            else:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO expenses (description, amount, date) VALUES (?, ?, ?)",
                    (description, amount, expense_date)
                )
                conn.commit()
                conn.close()
                st.success("Expense added successfully!")
    
    st.subheader("Expense Records")
    conn = get_db_connection()
    expenses_df = pd.read_sql("SELECT * FROM expenses", conn)
    conn.close()
    
    if not expenses_df.empty:
        st.dataframe(expenses_df)
        st.download_button(
            "Export as CSV",
            expenses_df.to_csv(index=False),
            "expenses.csv",
            "text/csv"
        )
    else:
        st.info("No expenses recorded yet")
