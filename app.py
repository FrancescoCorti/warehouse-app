import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import os
import json
import base64
from PIL import Image

# ---------------------------
# CSV SETUP
# ---------------------------
if not os.path.exists("datasets/products.csv"):
    st.error("products.csv not found")
    st.stop()

products = pd.read_csv("datasets/products.csv", index_col=False)

if not os.path.exists("datasets/orders.csv"):
    pd.DataFrame(columns=["order_id","office","products"]).to_csv("datasets/orders.csv", index=False)

# ---------------------------
# SESSION STATE: PERSIST SELECTED PAGE
# ---------------------------
if "mode" not in st.session_state:
    st.session_state.mode = "Office"  # default

st.session_state.mode = st.sidebar.radio(
    "Dashboard Mode",
    ["Office", "Warehouse"],
    index=0 if st.session_state.mode == "Office" else 1
)

mode = st.session_state.mode

# ---------------------------
# HEADER
# ---------------------------
st.title("Office ↔ Warehouse Order System")


def get_base64(file):
    with open(file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

img = get_base64("background/background.jpg")

page_element = f"""
<style>
[data-testid="stAppViewContainer"] {{
  background-image: url("data:image/jpg;base64,{img}");
  background-size: cover;
}}

[data-testid="stHeader"] {{
  background-color: rgba(0,0,0,0);
}}
</style>
"""
st.markdown(page_element, unsafe_allow_html=True)

# ---------------------------
# OFFICE INTERFACE
# ---------------------------
if mode == "Office":
    st.header("Office Order Page")

    if "cart" not in st.session_state:
        st.session_state.cart = []

    # Product selection
    kid = st.selectbox("Adult/Kid", sorted(products["kid"].unique())) # kid/adult

    if kid == '-':
        category = st.selectbox("Category", sorted(products["category"].unique())) # category

        name = st.selectbox(
        "Product", 
        sorted(products[products["category"] == category]["name"].unique())) # product name

        colour = st.selectbox(
            "Colour",
            sorted(products[(products["name"] == name) & (products["category"] == category)]["colour"].unique()) # colour
        )

        size = st.selectbox(
            "Size",
            products[(products["name"] == name) & (products["colour"] == colour) & (products["category"] == category)]["size"].unique() # size
        )
    else:
        category = st.selectbox("Category", sorted(products[products["kid"] == kid]["category"].unique())) # category

        name = st.selectbox(
            "Product", 
            sorted(products[(products["category"] == category) & (products["kid"] == kid)]["name"].unique()) # product name
        ) 

        colour = st.selectbox(
            "Colour",
            sorted(products[(products["name"] == name) & (products["category"] == category) & (products["kid"] == kid)]["colour"].unique()) # colour
        )

        size = st.selectbox(
            "Size",
            products[(products["name"] == name) & (products["colour"] == colour) & (products["category"] == category) & (products["kid"] == kid)]["size"].unique() # size
        )

    quantity = st.number_input("Quantity", min_value=1, step=1) # quantity selection

    if st.button("Add to Cart"):
        st.session_state.cart.append({
            "name": name,
            "colour": colour,
            "size": size,
            "quantity": quantity
        })
        st.success(f"Added {quantity} x {name} {colour} {size} to cart")

    # Show cart
    if st.session_state.cart:
        st.subheader("Current Order")
        st.table(pd.DataFrame(st.session_state.cart))

    office = st.text_input("Office Name")

    if st.button("Send Order"):
        if len(st.session_state.cart) == 0 or not office.strip():
            st.error("Add at least one product and fill in office name")
        else:
            orders = pd.read_csv("datasets/orders.csv", index_col=False)
            new_id = orders["order_id"].max() + 1 if len(orders) > 0 else 1
            new_order = {
                "order_id": new_id,
                "office": office,
                "products": json.dumps(st.session_state.cart)
            }

            orders = pd.concat([orders, pd.DataFrame([new_order])], ignore_index=True)
            orders.to_csv("datasets/orders.csv", index=False)

            st.success("Order sent!")
            st.session_state.cart = []

# ---------------------------
# WAREHOUSE INTERFACE
# ---------------------------
if mode == "Warehouse":
    st.header("Incoming Orders")

    # INTERNAL AUTO‑REFRESH
    st_autorefresh(interval=5000, limit=None, key="warehouse_refresh")

    # LOAD ORDERS
    orders = pd.read_csv("datasets/orders.csv", index_col=False)

    # ORDER SOUND NOTIFICATION
    if "last_order_count" not in st.session_state:
        st.session_state.last_order_count = 0

    current_count = len(orders)

    def play_notification():
        with open("assets/incoming_order.mp3", "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()

            md = f"""
            <audio autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """

            st.markdown(md, unsafe_allow_html=True)

    if current_count > st.session_state.last_order_count:
        play_notification()

    st.session_state.last_order_count = current_count

    # FORMAT PRODUCTS
    def format_products(prod_json):
        prod_list = json.loads(prod_json)
        return [f"{p['quantity']} x {p['name']} ({p['colour']}, {p['size']})" for p in prod_list]
    
    # DISPLAY ORDERS
    if len(orders) > 0:
        orders = orders.sort_values(by="order_id", ascending=True)

        for i, row in orders.iterrows():

            with st.container(border=True):

                st.subheader(f"Order #{row['order_id']}")

                products = format_products(row["products"])

                for p in products:
                    st.write(p)

                st.write("")

                col1, col2 = st.columns([3,1])

                with col2:
                    if st.button(
                        "✅ Complete",
                        key=f"complete_{row['order_id']}",
                        use_container_width=True
                    ):
                        orders = orders[orders["order_id"] != row["order_id"]]
                        orders.to_csv("datasets/orders.csv", index=False)

                        st.rerun()
    else:
        st.info("No incoming orders")