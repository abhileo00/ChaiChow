import streamlit as st
import pandas as pd
from utils.db import get_data_as_df
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime

def generate_reports():
    st.header("📝 Business Reports")
    
    # Sales Report
    st.subheader("Sales Report")
    sales_df = get_data_as_df("sales")
    
    if not sales_df.empty:
        st.dataframe(sales_df)
        st.download_button(
            "Download Sales CSV",
            sales_df.to_csv(index=False),
            "sales_report.csv",
            "text/csv"
        )
    else:
        st.info("No sales data available")
    
    # Expenses Report
    st.subheader("Expenses Report")
    expenses_df = get_data_as_df("expenses")
    
    if not expenses_df.empty:
        st.dataframe(expenses_df)
        st.download_button(
            "Download Expenses CSV",
            expenses_df.to_csv(index=False),
            "expenses_report.csv",
            "text/csv"
        )
    else:
        st.info("No expenses data available")
    
    # Combined PDF Report
    st.subheader("Combined Business Report")
    if st.button("Generate PDF Report"):
        pdf_path = "reports/business_report.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title = Paragraph("Smart Food Business Manager Report", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Date
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_para = Paragraph(f"Generated on: {date_str}", styles['Normal'])
        story.append(date_para)
        story.append(Spacer(1, 24))
        
        # Sales Summary
        sales_header = Paragraph("Sales Summary", styles['Heading2'])
        story.append(sales_header)
        
        if not sales_df.empty:
            total_sales = sales_df['quantity'] * sales_df['rate']
            sales_summary = [
                ["Total Sales", f"${total_sales.sum():.2f}"],
                ["Average Sale", f"${total_sales.mean():.2f}"],
                ["Top Selling Item", sales_df['item'].mode().values[0]]
            ]
            sales_table = Table(sales_summary)
            story.append(sales_table)
        else:
            story.append(Paragraph("No sales data available", styles['Normal']))
        
        story.append(Spacer(1, 12))
        
        # Expenses Summary
        expenses_header = Paragraph("Expenses Summary", styles['Heading2'])
        story.append(expenses_header)
        
        if not expenses_df.empty:
            expenses_summary = [
                ["Total Expenses", f"${expenses_df['amount'].sum():.2f}"],
                ["Average Expense", f"${expenses_df['amount'].mean():.2f}"],
                ["Highest Expense", f"${expenses_df['amount'].max():.2f}"]
            ]
            expenses_table = Table(expenses_summary)
            story.append(expenses_table)
        else:
            story.append(Paragraph("No expenses data available", styles['Normal']))
        
        doc.build(story)
        
        with open(pdf_path, "rb") as f:
            st.download_button(
                "Download PDF Report",
                f.read(),
                "business_report.pdf",
                "application/pdf"
            )
