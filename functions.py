import pandas as pd
import streamlit as st
import json
import base64
import requests
import threading
import time

PRODUCTS_CSV_URL = st.secrets["products_csv_url"]
ORDERS_CSV_URL = st.secrets["orders_csv_url"]
WRITE_API_URL = st.secrets["write_api_url"]


# LOAD PRODUCTS WITH CACHING
@st.cache_data(ttl=60)
def load_products():
    return pd.read_csv(PRODUCTS_CSV_URL)

#  LOAD ORDERS
def load_orders():
    try:
        df = pd.read_csv(ORDERS_CSV_URL)

        if "products" not in df.columns:
            df["products"] = ""

        return df

    except:
        return pd.DataFrame(columns=["order_id", "office", "products"])

# SEND ORDERS TO GOOGLE APPS SCRIPT
def send_order(order: dict):
    """Send order to Google Apps Script"""
    # Ensure products are a JSON string
    if "products" in order and isinstance(order["products"], list):
        order["products"] = json.dumps(order["products"])
        st.success("Order sent!")
    
    try:
        r = requests.post(
            WRITE_API_URL,
            data=order,  # form-encoded for Apps Script
            timeout=10
        )
        #st.info(f"Server response: {r.text}")
    except Exception as e:
        st.error(f"Failed to send order: {e}")

# REFRESH ORDERS  
def refresh_orders():

    new_orders = load_orders()

    new_ids = set(new_orders["order_id"]) if not new_orders.empty else set()
    old_ids = st.session_state.last_order_ids

    changed = new_ids != old_ids

    if changed:
        st.session_state.orders_cache = new_orders
        st.session_state.last_order_ids = new_ids

    return changed

# DELETE ORDERS AFTER "COMPLETE"
def delete_order_background(order_id):

    def worker():
        try:
            requests.post(
                WRITE_API_URL,
                data={"action": "delete", "order_id": order_id},
                timeout=2
            )
        except:
            pass

    threading.Thread(target=worker, daemon=True).start()

# FORMAT PRODUCTS
def format_products(prod_json):

    if not prod_json:
        return []

    try:
        return [
            f"{p['quantity']} x {p['name']} ({p['colour']}, {p['size']})"
            for p in json.loads(prod_json)
        ]

    except:
        return [f"Invalid product data: {prod_json}"]

# NOTIFICATION SOUND FOR NEW ORDERS
def play_notification():

    try:
        with open("assets/incoming_order.mp3", "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        st.markdown(
            f"""
            <audio autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """,
            unsafe_allow_html=True
        )

    except:
        pass

# IMAGE TO BASE64
def get_base64(file):
        with open(file, "rb") as f:
            return base64.b64encode(f.read()).decode()