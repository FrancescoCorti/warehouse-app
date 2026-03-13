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
        selected = option_menu("Menu", ["Product Request", 'Warehouse',"Info"], 
            icons=['cart-plus', 'box', 'info-circle'], menu_icon="menu-up", default_index=0)
        
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
    # OFFICE INTERFACE
    # ---------------------------

    if mode == "Product Request":
        st.header("Request Dashboard")

        if "cart" not in st.session_state:
            st.session_state.cart = []

        kid = st.selectbox("Adult/Kid", sorted(products["kid"].unique()))

        # PRODUCT SELECTION
        if kid == '-':
            category = st.selectbox("Category", sorted(products["category"].unique()))
            name = st.selectbox("Product", sorted(products[products["category"] == category]["name"].unique()))
            colour = st.selectbox("Colour", sorted(products[(products["name"] == name) & (products["category"] == category)]["colour"].unique()))
            size = st.selectbox("Size", products[(products["name"] == name) & (products["colour"] == colour) & (products["category"] == category)]["size"].unique())
        else:
            category = st.selectbox("Category", sorted(products[products["kid"] == kid]["category"].unique()))
            name = st.selectbox("Product", sorted(products[(products["category"] == category) & (products["kid"] == kid)]["name"].unique()))
            colour = st.selectbox("Colour", sorted(products[(products["name"] == name) & (products["category"] == category) & (products["kid"] == kid)]["colour"].unique()))
            size = st.selectbox("Size", products[(products["name"] == name) & (products["colour"] == colour) & (products["category"] == category) & (products["kid"] == kid)]["size"].unique())

        quantity = st.number_input("Quantity", min_value=1, step=1)

        # ADD TO CART
        if st.button("Add to Cart"):
            st.session_state.cart.append({
                "name": name,
                "colour": colour,
                "size": size,
                "quantity": quantity
            })
            st.success(f"Added {quantity} x {name} ({colour}, {size}) to cart")

        if st.session_state.cart:
            st.subheader("Current Order")
            st.table(pd.DataFrame(st.session_state.cart))

        office = st.text_input("Office Name")

        # SUBMIT THE ORDER
        if st.button("Send Order"):
            
            if len(st.session_state.cart) == 0 or not office.strip():
                st.error("Add at least one product and fill in office name")
            else:
                orders = load_orders()

                # ORDER ID GENERATION (TIME-BASED)
                now = datetime.datetime.now()
                new_id = int(now.strftime("%d%H%M%S") + f"{int(now.microsecond/1000):03d}")  # DDHHMMSSmmm

                # UNIQUENESS CHECK
                if not orders.empty and "order_id" in orders.columns:
                    while new_id in orders["order_id"].values:
                        now = datetime.datetime.now()
                        new_id = int(now.strftime("%d%H%M%S") + f"{int(now.microsecond/1000):03d}")

                new_order = {
                    "order_id": new_id,
                    "office": office.strip(),
                    "products": st.session_state.cart
                }

                send_order(new_order)
                st.session_state.cart = []
                st.rerun()

    # ------------------------------
    # WAREHOUSE INTERFACE
    # ------------------------------

    # INITIALISE STATES
    if "known_order_ids" not in st.session_state:
        st.session_state.known_order_ids = set()
    if "locally_deleted_orders" not in st.session_state:
        st.session_state.locally_deleted_orders = set()


    if mode == "Warehouse":

        st.header("Incoming Orders")

        st_autorefresh(interval=10000, key="warehouse_refresh")
        
        # LOAD ORDERS
        orders = load_orders()

        """ debugging info
        st.write("Orders dataframe:", orders)
        st.write("Orders shape:", orders.shape)
        st.write("Columns:", orders.columns)

        if not orders.empty:
            orders = orders[
                ~orders["order_id"].isin(st.session_state.locally_deleted_orders)
            ]

        st.write("Deleted orders:", st.session_state.locally_deleted_orders)
        st.write("Orders before filter:", len(orders))
        """
        
        # DETECT NEW ORDERS - NOTIFICATION SOUND
        current_ids = set(orders["order_id"]) if not orders.empty else set()

        new_orders = current_ids - st.session_state.known_order_ids

        if new_orders:
            play_notification()

        st.session_state.known_order_ids = current_ids

        
        # DISPLAY ORDERS
        orders_container = st.container()

        with orders_container:

            if not orders.empty:

                orders = orders.sort_values(by="order_id")

                for _, row in orders.iterrows():

                    with st.container(border=True):

                        col_left, col_right = st.columns([3,1])

                        # FORMATTING ORDER BOX
                        with col_left:
                            st.subheader(f"Order #{row['order_id']}")

                        with col_right:
                            st.markdown(
                                f"<h3 style='text-align:right; margin-top:0'>{row['office']}</h3>",
                                unsafe_allow_html=True
                            )

                        st.divider()

                        products = format_products(row["products"])

                        for p in products:
                            st.markdown(
                                f"<div style='font-size:20px; font-weight:500'>{p}</div>",
                                unsafe_allow_html=True
                            )

                        st.write("")

                        col1, col2 = st.columns([3,1])

                        # COMPLETE BUTTON AND TRIGGER DELETION
                        with col2:

                            if st.button(
                                "✅ Complete",
                                key=f"complete_{row['order_id']}",
                                use_container_width=True
                            ):

                                # INSTAT UI REMOVAL
                                st.session_state.locally_deleted_orders.add(row["order_id"])

                                # BACKGROUND DELETION
                                delete_order_background(row["order_id"])

                                st.rerun()

            else:
                st.info("No incoming orders")
                


    # ------------------------------
    # INFO INTERFACE
    # ------------------------------
    if mode == "Info":

        st.header("Information")
        st.markdown("""
        **How it works:**

        - The "Product Request" page allows users to create orders by selecting
          products and quantities, and submitting them to the warehouse.
        - The "Warehouse" page displays incoming orders in real-time. Warehouse
          staff can mark orders as complete, which removes them from the list.

        **Technical details:**

        - Orders are stored in a Google Sheet, which acts as a database.
        - The app uses Streamlit's session state to manage user interactions and
          real-time updates.

        **Note:** Product list is updated to February 2026, and new products are
        integrated by modifying the relative sheet.
                    
        For any updates' request, issues, or suggestions, please fill the form below:
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

        
        