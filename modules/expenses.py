import streamlit as st
import pandas as pd
from utils.db import get_db_connection, execute_query
from datetime import date

def manage_expenses():
    st.header("💸 Expense Management")
    
    with st.form("expense_form"):
        description = st.text_input("Expense Description")
        amount = st.number_input("Amount ($)", min_value=0.0, step=0.1)
        expense_date = st.date_input("Date", date.today())
        
        if st.form_submit_button("Add Expense"):
            if not description or amount <= 0:
                st.error("Please fill all fields correctly")
            else:
                execute_query(
                    "INSERT INTO expenses (description, amount, date) VALUES (?, ?, ?)",
                    (description, amount, expense_date)
                )
                st.success("Expense added successfully!")
    
    st.subheader("Expense Records")
    expenses_df = pd.read_sql("SELECT * FROM expenses", get_db_connection())
    
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
