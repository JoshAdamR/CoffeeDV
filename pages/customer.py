import time
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_config import store  # Import Firestore client from config
from datetime import datetime
from navigation import make_sidebar, logout
from functions import cookies
import pandas as pd
from streamlit_extras.stylable_container import stylable_container
import stripe
import random
from dbcoffee import branch_table, product_table, size_table, milk_option_table, addon_table, coupon_table, user_table, temperature_table, sugar_level_table
import webbrowser
from PIL import Image
import requests
from io import BytesIO
from time import sleep
from datetime import datetime


make_sidebar()

st.write(cookies.getAll())
stripe_secret = st.secrets.stripe 

# Set up Stripe
stripe.api_key = stripe_secret['stripe_id']

# Initialize Firestore
db = store

import base64

def resized_image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str


# Fetch data from Firestore
def fetch_data_from_firestore():

    # Processing the tables
    branches = {row['branch_id']: row['branch_name'] for _, row in branch_table.iterrows()}
    products = product_table.to_dict(orient='records')
    sizes = {
        row['size_id']: {'name': row['size_name'], 'price': row['price']}
        for _, row in size_table.iterrows()
    }
    milks = {row['type_of_milk']: row['price'] for _, row in milk_option_table.iterrows()}
    addons = {row['add_on_name']: row['add_on_price'] for _, row in addon_table.iterrows()}

    return branches, products, sizes, milks, addons

def get_product_details():
    
    sizes = {
        row['size_id']: {'name': row['size_name'], 'price': row['price']}
        for _, row in size_table.iterrows()
    }
    add_ons = {
        row['add_on_id']: {'name': row['add_on_name'], 'price': row['add_on_price']}
        for _, row in addon_table.iterrows()
    }
    temperatures = {
        row['temp_id']: {'name': row['temp'], 'price': row['price']}
        for _, row in temperature_table.iterrows()
    }
    milk_options = {
        row['milk_id']: {'name': row['type_of_milk'], 'price': row['price']}
        for _, row in milk_option_table.iterrows()
    }
    sugar_levels = {
        row['sugar_id']: {'name': row['level'], 'price': row['price']}
        for _, row in sugar_level_table.iterrows()
    }

    return sizes, add_ons, temperatures, sugar_levels, milk_options

def get_coupon_details(coupon_code):
    filtered_coupon = coupon_table[coupon_table['coupon_code'] == coupon_code]
    if not filtered_coupon.empty:
        return filtered_coupon.iloc[0].to_dict()
    else:
        return None
    
def get_loyalty_points(email):
    # Query the 'customer' collection where the email matches
    customer_ref = db.collection('customer').document(email) # Assuming unique email
    customer_docs = customer_ref.get()

    # If a customer is found, get their loyalty points
    if customer_docs.exists:
        current_points = customer_docs.to_dict().get("loyalty_points", 0)
        return current_points
    else:
        return 0  # Return 0 if no customer is found

def update_loyalty_points(email, amount_paid, points_used=0):
    try:
        # Earned loyalty points (1 point per dollar spent)
        loyalty_points_earned = int(amount_paid)

        customer_ref = db.collection("customer").document(email)
        customer = customer_ref.get()

        if customer.exists:
            # Fetch current loyalty points
            current_points = customer.to_dict().get("loyalty_points", 0)

            # Deduct points used and add points earned
            new_points = current_points - points_used + loyalty_points_earned

            # Update the database
            customer_ref.update({"loyalty_points": new_points})
            return new_points
        else:
            print(f"Customer with email {email} not found.")
            return None  # Customer not found
    except Exception as e:
        print(f"Error updating loyalty points: {str(e)}")
        return None

def calculate_total_price(base_price, size_price, add_ons_prices, temp_price, milk_type_price):
    total_addons_price = sum(add_ons_prices.values())
    return base_price + size_price + total_addons_price + temp_price + milk_type_price

def get_next_cart_id():
    """
    Retrieve the next order ID by querying the cart collection and finding the last created ID.
    """
    cart_ref = db.collection("cart")
    last_order = cart_ref.order_by("cart_id", direction=firestore.Query.DESCENDING).limit(1).stream()

    for doc in last_order:
        last_id = doc.to_dict().get("cart_id", "")
        if last_id.startswith("CART"):
            last_number = int(last_id[4:])  # Extract the numeric part of the ID
            return f"CART{last_number + 1:03d}"

    # If no documents found or no cart_id, start from ORD001
    return "CART001"

def display_branch_and_menu(branches, products, sizes):
    # Sidebar Branch Selection
    branch_names = list(branches.values())
    selected_branch_name = st.selectbox("📍 Select Branch", branch_names)

    # Get the corresponding branch ID for the selected branch name
    selected_branch_id = next(branch_id for branch_id, branch_name in branches.items() if branch_name == selected_branch_name)

    cookies.set("branch_id", selected_branch_id)

    # Category Selection with Icons
    category_filter = st.selectbox("🍽️ Select Category", ["All Drinks", "Coffee", "Tea"], index=0)

    # Filter Products by Category and Branch
    filtered_menu = [item for item in products if category_filter == "All Drinks" or item.get("product_category") == category_filter]

    # Show message if no products match the filter
    if not filtered_menu:
        st.write("😞 No products found in this category.")
    else:
        # Set the layout for the menu (Grid Style)
        num_columns = 2  # Changed to 2 columns for the layout
        rows = [filtered_menu[i:i + num_columns] for i in range(0, len(filtered_menu), num_columns)]

        for row in rows:
            cols = st.columns(num_columns)
            for col, item in zip(cols, row):
                with col:
                    # Product Image and Name
                    st.image(item.get("image_url", ""), use_column_width  =True)
                    st.markdown(f"### {item.get('product_name', 'Unknown Product')}")
                    st.write(f"💲 RM{item.get('base_price', 0):.2f}")
                    
                    # Add Button with Hover Effect and Immediate Feedback
                    add_button_key = f"add_{item['product_id']}"
                    if st.button(f"🛒 Add {item['product_name']}", key=add_button_key):
                        st.session_state["selected_product_id"] = item["product_id"]
                    
                    # Expander for Customization Options
                    if "selected_product_id" in st.session_state and st.session_state["selected_product_id"] == item["product_id"]:
                        with st.expander(f"🔧 Customize your {item['product_name']}"):

                            size_options = [details['name'] for details in sizes.values()]
                            add_ons_options = [details['name'] for details in add_ons.values()]
                            temperature_options = [details['name'] for details in temperatures.values()]
                            sugar_options = [details['name'] for details in sugar_levels.values()]
                            milk_options = [details['name'] for details in milk_types.values()]

                            size = st.selectbox(f"Size for {item['product_name']}", options=size_options, key=f"size_{item['product_id']}")
                            add_on = ["None"] if not (add_on := st.multiselect(f"Add-Ons for {item['product_name']}", options=add_ons_options, key=f"addons_{item['product_id']}")) else add_on
                            temperature = st.selectbox(f"Select Temperature", options=temperature_options, key=f"temperature_{item['product_id']}")
                            sugar_level = st.selectbox(f"Sugar Level", options=sugar_options, key=f"sugar_{item['product_id']}")
                            milk_type = st.selectbox(f"Milk Type", options=milk_options, key=f"milk_{item['product_id']}")

                            # Add to Cart Button with Price Breakdown
                            if st.button(f"🛒 Add to Cart", key=f"add_to_cart_{item['product_id']}"):
                                # Fetch corresponding prices using proper lookup
                                size_price = next((details["price"] for key, details in sizes.items() if details["name"] == size), 0)
                                add_ons_prices = {addon: next((price for name, price in addons.items() if name == addon), 0) for addon in add_on}
                                temperature_price = next((item["price"] for key, item in temperatures.items() if item["name"] == temperature), 0)
                                milk_type_price = next((price for name, price in milks.items() if name == milk_type), 0)

                                # Calculate total price
                                total_price = item["base_price"] + size_price + sum(add_ons_prices.values()) + temperature_price + milk_type_price

                                # Prepare Cart Item
                                cart_id = get_next_cart_id()
                                cart_item = {
                                    "cart_id": cart_id,
                                    "branch_id": selected_branch_id,
                                    "name": item["product_name"],
                                    "category": item["product_category"],
                                    "size": size,
                                    "addons": add_on,
                                    "temperature": temperature,
                                    "sugar_level": sugar_level,
                                    "milk_type": milk_type,
                                    "price": total_price,
                                    "status": "In Cart",
                                    "email": cookies.get("email"),
                                    "quantity": 1
                                }

                                # Save to Firebase
                                db.collection("cart").document(cart_id).set(cart_item)
                                
                                # Success Confirmation
                                st.success(f"✔️ Successfully added {item['product_name']} to the cart with Cart ID: {cart_id}!")
                                st.info(f"Total Price: RM{total_price:.2f}")
                                st.session_state["selected_product_id"] = None

    # Additional UX improvements
    st.write("---")
    st.write("💬 For any questions or assistance, feel free to reach out to our staff!") 

def display_cart(email):
    st.title("Your Cart")

    # Fetch loyalty points for the customer
    loyalty_points = get_loyalty_points(email)

    # Show the current loyalty points
    st.markdown(f"**Current Loyalty Points: {loyalty_points} points**")

    # Fetch cart items for the given email and status
    cart_items = fetch_cart_items(email=cookies.get("email"), status="In Cart")

    if cart_items:
        st.markdown("### Cart Summary")

        # Convert cart items to a DataFrame for display
        # df = pd.DataFrame(cart_items)
        # st.dataframe(df)

        total_price = 0
        coupon_discount = 0
        loyalty_points_discount = 0
        final_price = 0

        # Iterate through the items in the cart
        for index, item in enumerate(cart_items):
            #branch_id = item.get("branch_id", None)
            #branch_name = branches.get(branch_id, "Unknown Branch")
            def get_product_image(item, product_table):
                # Filter the DataFrame to find the product by its name
                product_data = product_table[product_table['product_name'] == item['name']]

                # If a product is found, return the 'image_url' from the first row
                if not product_data.empty:
                    return product_data.iloc[0]['image_url']
                else:
                    return None  # Return None if no product is found
                
            image_url = get_product_image(item, product_table)

            # Create three columns for layout
            image_col, details_col, price_col = st.columns([2, 2, 1])

            # First column: Image
            with image_col:
                # Replace `item['image_url']` with the actual key for the image in your data
                st.image(image_url)

            # Second column: Item details
            with details_col:
                st.title(item['name'])
                st.markdown(f"**Size:  {item['size']}**")
                st.markdown(f"**Qty:  {item['quantity']}**")
                st.markdown(f"**Addon:  {', '.join(item['addons'])}**")
                st.markdown(f"**{item['temperature']} | {item['sugar_level']} | {item['milk_type']}**")
                

            with price_col:
                item_total = item['price'] * item['quantity']
                total_price += item_total

                # Use custom HTML to align the price at the bottom of the column
                st.title("")
                st.markdown("")
                st.markdown("")
                st.markdown(f"")
                st.markdown(f"")
                st.markdown(f"")
                st.markdown(f"")
                st.markdown(f"")
                st.markdown(f"")
                st.markdown(
                            f"""
                            <div style="text-align: right; font-size: 16px; font-weight: bold;">
                               RM {item_total:.2f}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

            st.write("---")

        st.markdown(
            f"""
            <div style="text-align: right; font-size: 24px; font-weight: bold;">
                Subtotal: RM {total_price:.2f}
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("")
        st.markdown("")
        st.markdown(f"")
        st.markdown(f"")
        st.markdown(f"")
        st.markdown(f"")
        st.markdown(f"")
        st.markdown(f"")

        coupon_code = st.text_input("Enter Coupon Code (optional)")

        # Get the coupon details based on the entered coupon code
        coupon_details = get_coupon_details(coupon_code)

        if coupon_details:
            if coupon_details["promotion_type"] == "Discount":
                rm_discount = coupon_details.get("rm_discount", 0)
                discount_percentage = coupon_details.get("discount_percentage", 0)
                if rm_discount > 0:
                    # st.write(f"Discount: - RM {rm_discount}")
                    st.markdown(
                        f"""
                        <div style="text-align: right; font-size: 24px; font-weight: bold;">
                            <br><br> Discount: RM {rm_discount:.2f} off
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    coupon_discount = rm_discount
                elif discount_percentage > 0:
                    discount_amount = (discount_percentage / 100) * total_price
                    # st.markdown(f"Discount: {discount_percentage}% off")
                    st.markdown(
                        f"""
                        <div style="text-align: right; font-size: 24px; font-weight: bold;">
                            <br><br> Discount: {discount_percentage}% off
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    coupon_discount = discount_amount
            else:
                st.write("No discount available for this coupon.")
        else:
            st.write("Invalid coupon code.")

        final_price = total_price - coupon_discount - loyalty_points_discount
        total_discount = coupon_discount + loyalty_points_discount

        # st.markdown("")
        # st.markdown("")
        # st.markdown("")
        # st.markdown("")
        # st.markdown("")
        st.markdown(
            f"""
            <div style="text-align: right; font-size: 24px; font-weight: bold;">
                Total Price: RM {final_price:.2f}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("")

        # Create three columns for layout
        clear_col = st.columns([5.9,1])
        payment_col= st.columns([3.1,1])

        # Second column: Item details
        with payment_col[1]:
            # Button for Proceed to Payment
            if st.button("Proceed to Payment"):
                ordered_time_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Generate the next order ID
                order_id = get_next_order_id()
                invoice_id = get_next_invoice_id()

                cart_ref = db.collection("cart").where("email", "==", email).where("status", "==", "In Cart")
                cart_items = [{"id": doc.id, **doc.to_dict()} for doc in cart_ref.get()]

                # Preprocess cart_items to replace empty addons with "None"
                for item in cart_items:
                    item_total = item['price'] * item['quantity']

                    # Proportional discount for each item
                    proportionate_discount = (item_total / total_price) * total_discount
                    discounted_price = item_total - proportionate_discount
                    
                    # Ensure Stripe-compatible unit amount in cents
                    item['discounted_price'] = max(int(discounted_price * 100), 0)

                    if not item.get('addons'):  # Check if 'addons' is empty or missing
                        item['addons'] = "None"

                if final_price > 0:
                    new_loyalty_points = update_loyalty_points(email, final_price)
                    if new_loyalty_points is not None:
                        st.success(f"Payment successful! You have earned {final_price} loyalty points. Your new balance is {new_loyalty_points} points.")
                    else:
                        st.error("Error updating loyalty points. Please try again.")

                    try:
                        # Create Stripe checkout session
                        line_items = [
                            {
                                "price_data": {
                                    "currency": "myr",
                                    "product_data": {
                                        "name": item['name'],
                                        "description": f"Size: {item['size']}, Add-on: {', '.join(item['addons'])}, Temperature: {item['temperature']}"
                                    },
                                    "unit_amount": item['discounted_price'],
                                },
                                "quantity":  item['quantity'],
                            } for item in cart_items
                        ]

                        metadata = {
                            "invoice_id": invoice_id,
                            "order_id": order_id,
                            "email": email,
                            "loyalty_points_used": loyalty_points_discount * 100,  # Convert back to points
                            "total_discount": total_discount,
                            "final_price": final_price,
                        }

                        session = stripe.checkout.Session.create(
                            line_items=line_items,
                            mode="payment",
                            success_url="https://pybeancoffee.streamlit.app/success",
                            cancel_url="https://pybeancoffee.streamlit.app/customer",
                            metadata=metadata, 
                            payment_method_types=[
                                "card",
                                "grabpay",
                            ],
                        )

                        # Redirect to Stripe checkout
                        st.success("Checkout session created successfully!")
                        st.markdown(f"[Proceed to Payment]({session.url})")
                        # webbrowser.open(session.url)

                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")

                    # Update Cart with new order_id and other details
                    for item in cart_items:
                        db.collection("cart").document(item['id']).set({
                            "invoice_id": invoice_id,
                            "order_id": order_id,
                            "status": "Preparing",
                            "ordered_time_date": ordered_time_date,
                            "coupon_used": coupon_code,
                            "coupon_discount": coupon_discount,
                            "loyalty_points_discount": loyalty_points_discount,
                            "total_price": total_price,
                            "final_price": final_price,
                            "price_after_discount": round(item['discounted_price'] / 100, 2)
                        }, merge=True)
                    
                    cookies.set("invoice_id", invoice_id)
                        
                else:
                    st.warning("Your cart is empty. Please add items to proceed.")
                
                sleep(30)
                st.rerun()

        with clear_col[1]:
            # Button for Clear Cart
            if st.button("Clear Cart"):
                clear_cart(cookies.get("email"), status="In Cart")
                st.rerun()
    else:
        st.info("Your cart is empty!")

def get_next_order_id():
    """
    Retrieve the next cart order ID by querying the cart collection and finding the last created ID.
    """
    try:
        # Reference to the cart collection
        cart_ref = db.collection("cart")
        
        # Query to find the last cart by order_id in descending order
        last_cart = cart_ref.order_by("order_id", direction=firestore.Query.DESCENDING).limit(1).stream()

        # Iterate over the results to extract the last order_id
        for doc in last_cart:
            last_id = doc.to_dict().get("order_id", "")
            if last_id.startswith("ORD"):
                last_number = int(last_id[4:])  # Extract the numeric part after "CART"
                return f"ORD{last_number + 1:03d}"  # Increment and format as CART###
        
        # If no documents exist or no valid order_id, start from CART001
        return "ORD001"

    except Exception as e:
        print(f"An error occurred while retrieving the next cart ID: {e}")
        return "ORD001"  # Default value in case of errors
    
def get_next_invoice_id():
    """
    Retrieve the next cart order ID by querying the cart collection and finding the last created ID.
    """
    try:
        # Reference to the cart collection
        cart_ref = db.collection("cart")
        
        # Query to find the last cart by order_id in descending order
        last_cart = cart_ref.order_by("invoice_id", direction=firestore.Query.DESCENDING).limit(1).stream()

        # Iterate over the results to extract the last order_id
        for doc in last_cart:
            last_id = doc.to_dict().get("invoice_id", "")
            if last_id.startswith("INV"):
                last_number = int(last_id[3:])  # Extract the numeric part after "CART"
                return f"INV{last_number + 1:03d}"  # Increment and format as CART###
        
        # If no documents exist or no valid order_id, start from CART001
        return "INV001"

    except Exception as e:
        print(f"An error occurred while retrieving the next invoice ID: {e}")
        return "INV001"  # Default value in case of errors

def fetch_cart_items(email, status=None):
    """
    Fetch cart items from Firestore based on email and optionally a status filter.

    Parameters:
        email (str): The customer's email address.
        status (str, optional): The order status to filter by. Fetches all statuses if None.

    Returns:
        list: List of cart items matching the filters.
    """
    cart_ref = db.collection("cart")
    
    if status:
        # Query items by email and specific status
        query = cart_ref.where("email", "==", email).where("status", "==", status)
    else:
        # Query items by email only (fetch all statuses)
        query = cart_ref.where("email", "==", email)
    
    results = query.stream()
    cart_items = [{"id": doc.id, **doc.to_dict()} for doc in results]
    return cart_items

def clear_cart(email, status):
    """
    Clear all cart items from Firestore for a specific email and status.
    """
    cart_ref = db.collection("cart")
    query = cart_ref.where("email", "==", email).where("status", "==", status)
    results = query.stream()
    for doc in results:
        doc.reference.delete()

def display_order_status(branches):
    st.title("Order Status")
    
    email = cookies.get("email")  # Retrieve the email from cookies
    if not email:
        st.error("User email not found. Please log in.")
        return
    
    # Organize the order statuses into tabs
    tab_preparing, tab_completed, tab_history = st.tabs(["Preparing", "Completed", "All Orders"])
    
    # Preparing Orders
    with tab_preparing:
        st.subheader("Your Orders are Being Prepared by the Barista")
        cart_items = fetch_cart_items(email=email, status="Preparing")
        if cart_items:
            display_orders(cart_items, branches)
        else:
            st.info("No orders are currently being prepared.")

    
    # Completed Orders
    with tab_completed:
        st.subheader("Your Orders are Ready for Pickup")
        cart_items = fetch_cart_items(email=email, status="Done")
        if cart_items:
            display_orders(cart_items, branches)
        else:
            st.info("You have no completed orders at the moment.")
    
    # All Orders
    with tab_history:
        st.subheader("Your Order History")
        statuses = ["Preparing", "Done"]
        cart_items = []
        for status in statuses:
            cart_items.extend(fetch_cart_items(email=email, status=status))
        if cart_items:
            display_orders(cart_items, branches)
        else:
            st.info("No order history found!")

def display_orders(cart_items, branches):
    """
    Display the cart items with branch names and improved formatting.

    Parameters:
        cart_items (list): List of cart items fetched from the database.
        branches (dict): Dictionary mapping branch IDs to branch names.
    """
    if not cart_items:
        st.info("No orders available.")
        return

    # Map branch_id to branch_name
    for item in cart_items:
        item["branch_name"] = branches.get(item["branch_id"], "Unknown Branch")

    # Convert the list of cart items to a DataFrame
    df = pd.DataFrame(cart_items)

    # Rename and reorder columns for better readability
    column_mapping = {
        "branch_name": "Branch",
        "invoice_id": "Invoice ID",
        "cart_id": "Cart ID",
        "name": "Product Name",
        "size": "Size",
        "temperature": "Temperature",
        "sugar_level": "Sugar Level",
        "milk_type": "Milk Type",
        "status": "Status",
        "price_after_discount": "Price (RM)",
        "quantity": "Quantity",
        "email": "Customer Email",
        "category": "Category",
        "addons": "Add-Ons"
    }
    df.rename(columns=column_mapping, inplace=True)

    # Format 'Price (RM)' column to 2 decimal places for display
    df['Price (RM)'] = df['Price (RM)'].apply(lambda x: f"{x:.2f}")

    # Columns to display
    display_columns = [
        "Branch", "Invoice ID", "Cart ID", "Product Name", "Category", "Size", "Temperature",
        "Sugar Level", "Milk Type", "Add-Ons", "Quantity", "Price (RM)", "Status"
    ]

    # Display the DataFrame with selected columns and color-coded status
    def color_status(val):
        if val == 'Preparing':
            return 'background-color: #FFA500;'  # Red for "Preparing"
        elif val == 'Done':
            return 'background-color: #008000;'  # Green for "Done"
        return ''

    styled_df = df[display_columns].style.applymap(
        lambda val: color_status(val) if val in ['Preparing', 'Done'] else ''
    )
    st.dataframe(styled_df)

def display_loyalty_program(email):
    st.title("🎉 Loyalty Program")

    # Fetch current loyalty points
    def fetch_loyalty_points():
        return get_loyalty_points(email)

    loyalty_points = fetch_loyalty_points()
    points_to_next_voucher = 100 - (loyalty_points % 100)

    # Section: Loyalty Points Summary
    st.subheader("✨ Your Points Summary")
    points_display = st.empty()  # Placeholder for points metric
    points_display.metric("Loyalty Points", f"{loyalty_points} points")
    st.write("---")

    # Section: Redeem Merchandise
    st.subheader("🎁 Redeem Merchandise")

    # Fetch merchandise options from Firebase
    merchandise_ref = store.collection("merchandise")
    merchandise_docs = merchandise_ref.get()
    merchandise_options = [
        {
            "id": doc.id,
            "name": doc.get("merch_name"),
            "points_required": doc.get("points"),
            "image_url": doc.get("image_url")
        }
        for doc in merchandise_docs
    ]

    if merchandise_options:
        selected_merchandise = st.selectbox(
            "Choose a merchandise to redeem:",
            options=[item["name"] for item in merchandise_options]
        )

        selected_item = next(item for item in merchandise_options if item["name"] == selected_merchandise)
        required_points = selected_item["points_required"]

        # Resize and display merchandise image
        def resize_image(image_url, size=(200, 200)):  # Adjust size as needed
            response = requests.get(image_url)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                img = img.resize(size)  # Resize image
                return img
            else:
                st.error("Image could not be loaded.")
                return None

        resized_image = resize_image(selected_item["image_url"])
        if resized_image:
            # Display the image at the center using markdown
            st.markdown(
                f"""
                <div style="text-align: center;">
                    <img src="data:image/png;base64,{resized_image_to_base64(resized_image)}" alt="{selected_item['name']}" style="border-radius: 10px;">
                    <p><b>{selected_item['name']}</b></p>
                    <p><b>{selected_item['points_required']} points</b></p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if loyalty_points >= required_points:
            if st.button(f"Redeem {selected_merchandise}"):
                # Deduct points and update Firebase
                new_points_balance = deduct_loyalty_points(email, required_points)

                if new_points_balance is not None:
                    # Fetch and display updated loyalty points
                    loyalty_points = fetch_loyalty_points()  # Refetch updated points
                    points_display.metric("Loyalty Points", f"{loyalty_points} points")

                    # Success message
                    st.success(f"🎉 Successfully redeemed {selected_merchandise}! Your new balance of loyalty points is {loyalty_points} points.")
        else:
            st.info(f"🚀 Earn {required_points - loyalty_points} more points to redeem {selected_merchandise}!")
    else:
        st.warning("⚠️ No merchandise available for redemption at the moment.")

    st.write("---")

    # Section: How to Earn Points
    st.subheader("🛒 How to Earn Points")
    st.write("""
    - 💵 Spend RM1 to earn 1 loyalty point.
    - 🎂 Celebrate your birthday with bonus points!
    - 🏆 Participate in special promotions to earn extra rewards.
    """)

def deduct_loyalty_points(email, points_to_deduct):
    try:
        # Fetch the current loyalty points of the user
        customer_ref = store.collection("customer").document(email)
        customer = customer_ref.get()

        if customer.exists:
            # Fetch current points
            current_points = customer.to_dict().get("loyalty_points", 0)

            if current_points >= points_to_deduct:
                # Deduct points
                new_balance = current_points - points_to_deduct

                # Update the database
                customer_ref.update({"loyalty_points": new_balance})

                # Return the updated balance
                return new_balance
            else:
                st.warning("⚠️ You don't have enough loyalty points to redeem this item.")
                return None
        else:
            st.error(f"Customer with email {email} not found.")
            return None
    except Exception as e:
        st.error(f"Error deducting loyalty points: {e}")
        return None


def get_next_feedback_id():
    #try:
    email = cookies.get('email')
    branch_id = cookies.get('branch_id')
    cart_ref = db.collection("cart").where("email", "==", email).where("branch_id", "==", branch_id)
    
    st.write(cart_ref)
    
    # Query to find the last cart by order_id in descending order
    last_cart = cart_ref.order_by("order_id", direction=firestore.Query.DESCENDING).limit(1).stream()

    # Check if any order exists
    last_order = None
    for doc in last_cart:
        last_order = doc.to_dict()
        break  # We only need the first result
    
    if last_order:
        last_order_id = last_order.get("order_id", "")
        if last_order_id.startswith("ORD"):
            # Extract the numeric part after "ORD" and format it as FEED###
            last_number = int(last_order_id[3:])  # Extract numeric part of order ID
            return f"ORD{last_number:03d}"  # Create feedback ID with the same number
    else:
        # No previous orders exist
        return None  # Indicate no feedback ID can be generated

    #except Exception as e:
        #print(f"An error occurred while retrieving the feedback ID: {e}")
        #return None  # Indicate no feedback ID in case of errors

def display_feedback(email):
    st.title("📋 Share Your Feedback")
    st.write("We value your feedback to improve our service. Please take a moment to rate your experience! 🙏")
    
    # Check if a previous order exists
    feedback_id = get_next_feedback_id()
    if feedback_id is None:
        st.warning("⚠️ You have not placed any orders yet. Feedback can only be provided after placing an order.")
        return  # Exit the function if no orders exist

    # Feedback form
    with st.form("feedback_form"):
        st.subheader("⭐ Rate Your Experience")
        
        coffee_rating = st.slider("☕ Rate the coffee", 1, 5, help="How was your coffee?")
        service_rating = st.slider("🛎️ Rate the service", 1, 5, help="How was the service provided?")
        time_rating = st.slider("⏳ Rate the waiting time", 1, 5, help="Was the waiting time reasonable?")
        environment_rating = st.slider("🌿 Rate the environment", 1, 5, help="How did you find the ambiance?")
        sanitary_rating = st.slider("🧼 Rate the sanitary conditions", 1, 5, help="Was everything clean and hygienic?")

        # Submit button
        submit_feedback = st.form_submit_button("Submit Feedback")

    if submit_feedback:
        # Prepare feedback data
        feedback_data = {
            "order_id": feedback_id,
            "rate_coffee": coffee_rating,
            "rate_service": service_rating,
            "rate_wait_time": time_rating,
            "rate_environment": environment_rating,
            "rate_sanitary": sanitary_rating,
            "email": email,
            "date" : datetime.now(),
            "branch_id" : cookies.get('branch_id')
        }

        try:
            # Save feedback data to Firestore
            db.collection("feedback").document(feedback_id).set(feedback_data)
            st.success("🎉 Thank you for your feedback!")
            st.balloons()
            st.info("Your feedback has been recorded. Please redeem a small Americano from our counter as a token of our appreciation! 🥤")
        except Exception as e:
            st.error(f"❌ An error occurred while recording your feedback: {e}")

    # Motivational Footer
    st.write("---")
    st.info("Your opinions help us grow! Thank you for taking the time to share your thoughts. ❤️")

# Sidebar navigation
def display_sidebar(branches, products, sizes):
    # Center-aligning the text in the sidebar
    st.sidebar.markdown(
        f"<h3 style='text-align: center;'> <br><br>Welcome <br><br> {cookies.get('fullname')} <br><br><br></h3>", 
        unsafe_allow_html=True
    )

    page = st.sidebar.selectbox("Navigate to", ("Menu", "Cart", "Order Status", "Loyalty Program", "Feedback"))
    if page == "Menu":
        st.subheader("Select Your Drinks")
        display_branch_and_menu(branches, products, sizes)
    elif page == "Cart":
        display_cart(cookies.get("email"))
    elif page == "Order Status":
        display_order_status(branches)
    elif page == "Loyalty Program":
        display_loyalty_program(cookies.get("email"))
    elif page == "Feedback":
        display_feedback(cookies.get("email"))

branches, products, sizes, milks, addons = fetch_data_from_firestore()
sizes, add_ons, temperatures, sugar_levels, milk_types = get_product_details()

# Display app content
display_sidebar(branches, products, sizes)

st.sidebar.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True)
if st.sidebar.button("Log out"):
    logout()
