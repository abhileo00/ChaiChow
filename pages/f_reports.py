import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

def render():
    if st.session_state.user_role != "admin":
        st.error("⛔ Admin access required")
        return

    st.header("📊 Sales Reports")
    try:
        orders_df = pd.read_csv("data/orders.csv")
        orders_df['created_at'] = pd.to_datetime(orders_df['created_at'])
    except:
        st.error("Failed to load order data")
        return
    
    # Date range selector
    default_end = datetime.now()
    default_start = default_end - timedelta(days=30)
    col1, col2 = st.columns(2)
    start_date = col1.date_input("Start Date", value=default_start)
    end_date = col2.date_input("End Date", value=default_end)
    
    # Filter data
    filtered = orders_df[
        (orders_df['created_at'].dt.date >= start_date) & 
        (orders_df['created_at'].dt.date <= end_date)
    ]
    
    if filtered.empty:
        st.warning("No orders in selected period")
        return
    
    # Key metrics
    total_orders = len(filtered)
    total_revenue = filtered['total_amount'].sum()
    avg_order = total_revenue / total_orders
    
    st.subheader(f"📅 Period: {start_date} to {end_date}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Orders", total_orders)
    col2.metric("Total Revenue", f"₹{total_revenue:,.2f}")
    col3.metric("Avg Order Value", f"₹{avg_order:,.2f}")
    
    # Daily trends
    st.subheader("📈 Daily Trends")
    daily = filtered.set_index('created_at').resample('D').agg({
        'order_id': 'count',
        'total_amount': 'sum'
    }).rename(columns={'order_id': 'orders', 'total_amount': 'revenue'}).reset_index()
    
    tab1, tab2 = st.tabs(["Orders", "Revenue"])
    with tab1:
        st.plotly_chart(
            px.line(daily, x='created_at', y='orders', title="Orders per Day"),
            use_container_width=True
        )
    with tab2:
        st.plotly_chart(
            px.line(daily, x='created_at', y='revenue', title="Revenue per Day"),
            use_container_width=True
        )
    
    # Payment analysis
    st.subheader("💳 Payment Analysis")
    payment_df = filtered.groupby('payment_mode').agg({
        'order_id': 'count',
        'total_amount': 'sum'
    }).rename(columns={'order_id': 'orders', 'total_amount': 'revenue'}).reset_index()
    
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            px.pie(payment_df, values='orders', names='payment_mode', 
                 title="Orders by Payment Mode"),
            use_container_width=True
        )
    with col2:
        st.plotly_chart(
            px.pie(payment_df, values='revenue', names='payment_mode',
                 title="Revenue by Payment Mode"),
            use_container_width=True
        )
