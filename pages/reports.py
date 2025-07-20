import streamlit as st
import pandas as pd
import plotly.express as px
from utils.helpers import load_data

st.set_page_config(page_title="Reports", layout="wide")

# Admin only
if 'user_role' not in st.session_state or st.session_state.user_role != "admin":
    st.warning("Unauthorized access")
    st.switch_page("app.py")

# Load data
orders = load_data('orders')
menu = load_data('menu')

st.title("Reports")

# Date range filter
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date")
with col2:
    end_date = st.date_input("End Date")

# Filter orders
orders['date'] = pd.to_datetime(orders['timestamp']).dt.date
filtered_orders = orders[(orders['date'] >= start_date) & (orders['date'] <= end_date)]

# Metrics
total_orders = len(filtered_orders)
total_revenue = filtered_orders['total'].sum()
avg_order = filtered_orders['total'].mean()

st.subheader(f"Summary: {start_date} to {end_date}")
col1, col2, col3 = st.columns(3)
col1.metric("Total Orders", total_orders)
col2.metric("Total Revenue", f"${total_revenue:,.2f}")
col3.metric("Average Order", f"${avg_order:,.2f}")

# Charts
st.subheader("Visualizations")
tab1, tab2 = st.tabs(["Revenue Trend", "Popular Items"])

with tab1:
    daily_revenue = filtered_orders.groupby('date')['total'].sum().reset_index()
    fig = px.line(daily_revenue, x='date', y='total', title="Daily Revenue")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    # Count items from orders
    item_counts = {}
    for items_str in filtered_orders['items']:
        items = eval(items_str)
        for item, qty in items.items():
            item_counts[item] = item_counts.get(item, 0) + qty
    
    top_items = pd.DataFrame({
        'item': list(item_counts.keys()),
        'count': list(item_counts.values())
    }).sort_values('count', ascending=False).head(10)
    
    fig = px.bar(top_items, x='item', y='count', title="Top Selling Items")
    st.plotly_chart(fig, use_container_width=True)
