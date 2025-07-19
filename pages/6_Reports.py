import streamlit as st
import pandas as pd
import plotly.express as px

def render():
    if st.session_state.user_role != "admin":
        st.warning("⛔ Admin access required")
        return
    
    st.title("📊 Sales Reports")
    orders_df = pd.read_csv("data/orders.csv")
    
    if orders_df.empty:
        st.warning("No order data available")
        return
    
    # Date range filter
    orders_df['created_at'] = pd.to_datetime(orders_df['created_at'])
    min_date = orders_df['created_at'].min().date()
    max_date = orders_df['created_at'].max().date()
    
    col1, col2 = st.columns(2)
    start_date = col1.date_input("Start Date", min_date)
    end_date = col2.date_input("End Date", max_date)
    
    filtered = orders_df[
        (orders_df['created_at'].dt.date >= start_date) & 
        (orders_df['created_at'].dt.date <= end_date)
    ]
    
    # Metrics
    total_orders = len(filtered)
    total_revenue = filtered['total_amount'].sum()
    avg_order = total_revenue / total_orders if total_orders > 0 else 0
    
    st.metric("Total Orders", total_orders)
    st.metric("Total Revenue", f"₹{total_revenue:,.2f}")
    st.metric("Average Order", f"₹{avg_order:,.2f}")
    
    # Charts
    fig1 = px.line(
        filtered.groupby(filtered['created_at'].dt.date)['total_amount'].sum().reset_index(),
        x='created_at',
        y='total_amount',
        title="Daily Revenue"
    )
    st.plotly_chart(fig1)
    
    fig2 = px.pie(
        filtered.groupby('payment_mode')['total_amount'].sum().reset_index(),
        values='total_amount',
        names='payment_mode',
        title="Revenue by Payment Type"
    )
    st.plotly_chart(fig2)
