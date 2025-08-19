# tests/test_core.py
import os
import tempfile
import pandas as pd
import pytest
from datetime import date

# We import functions by path. Ensure tests run with project root as working dir.
from app import save_csv, load_csv, SCHEMA, adjust_stock, record_order, list_inventory, save_inventory_from_editor

def setup_tmp_inventory(tmp_path):
    # create a small inventory file
    inv = pd.DataFrame([
        {"item_id":"aaa11111","item_name":"Milk","category":"Dairy","unit":"ltr","stock_qty":10,"rate":20.0,"selling_price":25,"min_qty":2},
        {"item_id":"bbb22222","item_name":"Butter","category":"Dairy","unit":"kg","stock_qty":5,"rate":200.0,"selling_price":210,"min_qty":1}
    ])
    inv_file = tmp_path/"inventory.csv"
    inv.to_csv(inv_file, index=False)
    return str(inv_file), inv

def test_adjust_stock(tmp_path, monkeypatch):
    inv_file, inv_df = setup_tmp_inventory(tmp_path)
    # monkeypatch the DATA_DIR path in app to use tmp files (simple approach)
    import app
    monkeypatch.setattr(app, "INVENTORY_FILE", inv_file)
    # Decrease stock by 3
    ok, new = app.adjust_stock("aaa11111", -3)
    assert ok is True
    assert float(new) == pytest.approx(7.0)

def test_record_order_insufficient(tmp_path, monkeypatch):
    inv_file, inv_df = setup_tmp_inventory(tmp_path)
    import app
    monkeypatch.setattr(app, "INVENTORY_FILE", inv_file)
    # Try to order more than available
    res = app.record_order(date.today(), "9999999999", "bbb22222", "Butter", 10, 200.0, 210, "Cash", user_id="test", remarks="")
    assert res is False or (isinstance(res, tuple) and res[0] is False)

# Note: These tests are minimal scaffolds. For full coverage add more tests for saving, editing, low-stock workflow.

