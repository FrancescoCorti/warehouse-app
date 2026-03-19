import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_option_menu import option_menu
import datetime
import smtplib
from email.mime.text import MIMEText
from functions import *

# ---------------------------
# LOGIN PAGE
# ---------------------------

# DEFINE ALLOWED IDs
ALLOWED_EMAIL = st.secrets["allowed_email"]

# LOGIN
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("Login")

    try:
        img = get_base64("figures/background.jpg")
        st.markdown(f"""
        <style>
        [data-testid="stAppViewContainer"] {{
        background-image: url("data:image/jpg;base64,{img}");
        background-size: cover;
        }}
        [data-testid="stHeader"] {{
        background-color: rgba(0,0,0,0);
        }}
        </style>
        """, unsafe_allow_html=True)
    except:
        pass

    email = st.text_input("Enter your credentials", placeholder="Credentials")
    
    if st.button("Login"):

        allowed = [e.lower() for e in ALLOWED_EMAIL]

        if email.strip().lower() in allowed:
            st.session_state.logged_in = True
            st.success("Logged in successfully!")

            st.rerun()
        else:
            st.error("Access denied. Invalid email.")

if st.session_state.logged_in:
    # ---------------------------
    # LOAD PRODUCTS
    # ---------------------------
    products = load_products()

    if products.empty:
        st.error("Products sheet is empty")
        st.stop()

    # ---------------------------
    # SESSION STATE + SIDEBAR
    # ---------------------------

    # STATE
    if "mode" not in st.session_state:
        st.session_state.mode = "Product Request"

    # SIDEBAR
    LOGO_LONG = "figures/logo_long.png"
    LOGO_SHORT = "figures/logo_short.png"

    st.html("""
        <style>
            [alt=Logo] {
            height: 3.5rem;
            }
        </style>
                """)

    with st.sidebar:
        st.logo(LOGO_LONG, icon_image = LOGO_SHORT, size = "large")
        selected = option_menu("Menu", ["Product Request", 'Warehouse',"---","Info"], 
            icons=['cart-plus', 'box', '', 'info-circle'], menu_icon="menu-up", default_index=0)
        
        # Update session state when selection changes
        if st.session_state.mode != selected:
            st.session_state.mode = selected

    mode = st.session_state.mode

    # ---------------------------
    # PAGE FORMATTING
    # ---------------------------

    st.title("Warehouse Order System")

    try:
        img = get_base64("figures/background.jpg")
        st.markdown(f"""
        <style>
        [data-testid="stAppViewContainer"] {{
        background-image: url("data:image/jpg;base64,{img}");
        background-size: cover;
        }}
        [data-testid="stHeader"] {{
        background-color: rgba(0,0,0,0);
        }}
        </style>
        """, unsafe_allow_html=True)
    except:
        pass

    # ---------------------------
    # PRODUCT REQUEST INTERFACE
    # ---------------------------

    if mode == "Product Request":

        st.header("Request Dashboard")

        # ---------------------------
        # SESSION STATE
        # ---------------------------
        if "cart" not in st.session_state:
            st.session_state.cart = []

        # ---------------------------
        # PRODUCT FILTER
        # ---------------------------
        kid = st.selectbox("Adult / Kid", sorted(products["kid"].unique()))

        filtered_products = products.copy()

        if kid != "-":
            filtered_products = filtered_products[filtered_products["kid"] == kid]

        # CATEGORY
        category = st.selectbox(
            "Category",
            sorted(filtered_products["category"].unique())
        )

        filtered_products = filtered_products[filtered_products["category"] == category]

        # PRODUCT
        name = st.selectbox(
            "Product",
            sorted(filtered_products["name"].unique())
        )

        filtered_products = filtered_products[filtered_products["name"] == name]

        # COLOUR
        colour = st.selectbox(
            "Colour",
            sorted(filtered_products["colour"].unique())
        )

        filtered_products = filtered_products[filtered_products["colour"] == colour]

        # SIZE
        size = st.selectbox(
            "Size",
            sorted(filtered_products["size"].unique())
        )

        quantity = st.number_input("Quantity", min_value=1, step=1)

        st.divider()

        # ---------------------------
        # ADD TO CART
        # ---------------------------
        if st.button("Add to Cart"):

            item = {
                "name": name,
                "colour": colour,
                "size": size,
                "quantity": quantity
            }

            st.session_state.cart.append(item)

            st.success(f"Added {quantity} × {name} ({colour}, {size})")

        # ---------------------------
        # CART DISPLAY
        # ---------------------------
        if st.session_state.cart:

            st.subheader("Current Order")

            cart_df = pd.DataFrame(st.session_state.cart)

            for i, row in cart_df.iterrows():

                col1, col2, col3, col4, col5 = st.columns([3,2,2,2,1])

                col1.write(row["name"])
                col2.write(row["colour"])
                col3.write(row["size"])
                col4.write(row["quantity"])

                if col5.button("🗑️", key=f"remove_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()

        else:
            st.info("Cart is empty")

        st.divider()

        # ---------------------------
        # OFFICE INPUT
        # ---------------------------
        office = st.text_input("Office Name")

        # ---------------------------
        # SEND ORDER
        # ---------------------------
        if st.button("Send Order"):

            if not st.session_state.cart:
                st.error("Add at least one product")

            elif not office.strip():
                st.error("Please enter office name")

            else:

                orders = load_orders()

                # ORDER ID
                now = datetime.datetime.now()
                new_id = int(now.strftime("%d%H%M%S") + f"{int(now.microsecond/1000):03d}")

                if not orders.empty and "order_id" in orders.columns:
                    while new_id in orders["order_id"].values:
                        now = datetime.datetime.now()
                        new_id = int(now.strftime("%d%H%M%S") + f"{int(now.microsecond/1000):03d}")

                new_order = {
                    "order_id": new_id,
                    "office": office.strip(),
                    "products": st.session_state.cart.copy()
                }

                send_order(new_order)

                # CLEAR CART
                st.session_state.cart.clear()

                st.success("Order sent successfully!")

                st.rerun()

    # ------------------------------
    # WAREHOUSE INTERFACE
    # ------------------------------
    if mode == "Warehouse":

        if "hidden_orders" not in st.session_state:
            st.session_state.hidden_orders = set()

        if "known_order_ids" not in st.session_state:
            st.session_state.known_order_ids = set()

        st.header("Incoming Orders")

        # AUTO-REFRESH
        st_autorefresh(interval=10000, key="warehouse_refresh")

        # LOAD ORDERS
        orders = load_orders()

        # LOCALLY HIDE DELETED ORDERS
        if not orders.empty:
            orders = orders[~orders["order_id"].isin(st.session_state.hidden_orders)]

        # NEW ORDERS + NOTIFICATION
        current_ids = set(orders["order_id"]) if not orders.empty else set()

        new_orders = current_ids - st.session_state.known_order_ids

        if new_orders:
            play_notification()

        st.session_state.known_order_ids = current_ids

        # DISPLAY ORDERS
        if orders.empty:
            st.info("No incoming orders")
        else:
            orders = orders.sort_values(by="order_id")

            for row in orders.to_dict("records"):

                with st.container(border=True):
                    col_left, col_right = st.columns([3,1])

                    # HEADER
                    with col_left:
                        st.subheader(f"Order #{row['order_id']}")

                    with col_right:
                        st.markdown(
                            f"<h3 style='text-align:right; margin-top:0'>{row['office']}</h3>",
                            unsafe_allow_html=True
                        )

                    st.divider()

                    # PRODUCTS
                    products = format_products(row["products"])

                    for p in products:
                        st.markdown(
                            f"<div style='font-size:20px; font-weight:500'>{p}</div>",
                            unsafe_allow_html=True
                        )

                    st.write("")

                    # COMPLETE BUTTON AND DELETE
                    col1, col2 = st.columns([3,1])

                    with col2:
                        if st.button(
                            "✔️ Complete",
                            key=f"complete_{row['order_id']}",
                            use_container_width=True
                        ):
                            delete_order_async(row["order_id"])
                            st.rerun()
                


    # ------------------------------
    # INFO INTERFACE
    # ------------------------------
    if mode == "Info":

        st.header("Information")
        st.markdown("""
        **How it works:**

        - Use _**Product Request**_ to create orders by
          selecting products and quantities, and to submit them to the
          warehouse.
        - Use _**Orders**_ to display incoming orders in real-time.
          Mark orders as complete to remove them from the list.
        - Use _**Add New Product**_ to add new products to the
          system, which will be available for future orders. In case of a bulk
          upload of new products, the user is suggested to operate directly on
          the Google Sheet database.


        **Note:** Product list is updated to February 2026.
                    
        For any updates' request, issues, or suggestions, please use the form
        below:
        """)

        # FEEDBACK FORM
        set_form = st.form(
            "feedback",
            clear_on_submit=True,
            enter_to_submit=False,
            border=True,
            width="stretch",
        )

        sentence = set_form.text_area(
            "Your feedback",
            placeholder="Write your message here...",
            height=200
        )

        # SUBMIT TO EMAIL   
        submit = set_form.form_submit_button("Submit")

        if submit:
            sender = st.secrets["feedback_sender"]
            password = st.secrets["password_sender"]
            receiver = st.secrets["feedback_receiver"]

            msg = MIMEText(sentence)
            msg["Subject"] = "New Warehouse Feedback"
            msg["From"] = sender
            msg["To"] = receiver

            try:
                server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
                server.login(sender, password)
                server.send_message(msg)
                server.quit()

                st.success("Feedback submitted! Thank you.")

            except:
                st.error("Failed to send feedback.")

        
        