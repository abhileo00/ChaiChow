import sqlite3
import os
import pandas as pd

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'sfbm.sqlite')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        date TEXT DEFAULT CURRENT_DATE
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        rate REAL NOT NULL,
        date TEXT DEFAULT CURRENT_DATE
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventory (
        item TEXT PRIMARY KEY,
        quantity INTEGER NOT NULL
    )''')
    
    conn.commit()
    conn.close()

def get_data_as_df(table_name):
    conn = get_db_connection()
    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df

def execute_query(query, params=()):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()
