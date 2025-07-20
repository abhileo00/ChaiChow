import pandas as pd
import os

DATA_DIR = "data"

def load_data(filename):
    """Load a CSV file from the data directory"""
    filepath = os.path.join(DATA_DIR, f"{filename}.csv")
    if not os.path.exists(filepath):
        # Return empty DataFrame with expected columns
        if filename == "users":
            return pd.DataFrame(columns=['user_id', 'name', 'password', 'role', 'email', 
                                       'status', 'credit_limit', 'current_balance'])
        elif filename == "menu":
            return pd.DataFrame(columns=['item_id', 'item_name', 'description', 'price', 
                                      'category', 'available'])
        elif filename == "inventory":
            return pd.DataFrame(columns=['item_id', 'item_name', 'quantity', 'unit', 
                                       'min_required'])
        elif filename == "orders":
            return pd.DataFrame(columns=['order_id', 'customer_id', 'staff_id', 'items', 
                                       'total', 'payment_mode', 'status', 'timestamp'])
        elif filename == "feedback":
            return pd.DataFrame(columns=['feedback_id', 'user_id', 'rating', 'type', 
                                       'comment', 'name', 'timestamp'])
    return pd.read_csv(filepath)

def save_data(df, filename):
    """Save a DataFrame to the data directory"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    filepath = os.path.join(DATA_DIR, f"{filename}.csv")
    df.to_csv(filepath, index=False)
