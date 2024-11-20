import time
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from navigation import make_sidebar, logout
from functions import cookies
import pandas as pd
from streamlit_extras.stylable_container import stylable_container
import stripe
import random

make_sidebar()

st.write(cookies.getAll())

# Set up Stripe
stripe.api_key = "sk_test_CsnggH3iChIYjrFoue5y6M98"

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_credentials.json")
    firebase_admin.initialize_app(cred)

# Initialize Firestore
db = firestore.client()

# Fetch data from Firestore
def fetch_data_from_firestore():
    db = firestore.client()

    branches_ref = db.collection('branch')
    products_ref = db.collection('product')
    sizes_ref = db.collection('size')
    milk_ref = db.collection('milk_option')
    addons_ref = db.collection('addon')

    branches = {doc.id: doc.to_dict().get('branch_name', '') for doc in branches_ref.stream()}
    products = [doc.to_dict() for doc in products_ref.stream()]
    sizes = {size.id: size.to_dict()['price'] for size in sizes_ref.stream()}
    milk = {milk.id: milk.to_dict()['price'] for milk in milk_ref.stream()}
    addons = {addon.id: addon.to_dict().get('price', None) for addon in addons_ref.stream()}

    return branches, products, sizes, milk, addons

def get_coupon_details(coupon_code):
    coupon_ref = db.collection('coupon').where('coupon_code', '==', coupon_code)
    coupons = coupon_ref.stream()

    coupon = next(coupons, None) 

    if coupon:
        return coupon.to_dict()
    else:
        return None

def get_customer_id_from_email(email):
    useracc_ref = db.collection('useracc')
    user = useracc_ref.where('email', '==', email).get()

    if user:
        user_data = user[0].to_dict()  
        return user_data.get('customer_id', None) 
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

def get_product_details():
    # Fetch product options from Firebase
    sizes_ref = db.collection('size').get()
    add_ons_ref = db.collection('addon').get()
    temperatures_ref = db.collection('temperature').get()
    milk_types_ref = db.collection('milk_option').get()
    sugar_levels_ref = db.collection('sugar_level').get()
    # ice_levels_ref = db.collection('ice_level').get()  

    # Create mappings for sizes, add-ons, milk types, and ice levels
    sizes = {doc.id: {'name': doc.to_dict().get('size_name', ''), 'price': doc.to_dict().get('price', 0)} for doc in sizes_ref}
    add_ons = {doc.id: {'name': doc.to_dict().get('add_on_name', ''), 'price': doc.to_dict().get('add_on_price', 0)} for doc in add_ons_ref}
    temperatures = {doc.id: {'name': doc.to_dict().get('temp', ''), 'price': doc.to_dict().get('price', 0)} for doc in temperatures_ref} 
    milk_types = {doc.id: {'name': doc.to_dict().get('type_of_milk', ''), 'price': doc.to_dict().get('price', 0)} for doc in milk_types_ref}
    
    sugar_levels = {doc.id: {'name': doc.to_dict().get('level', ''), 'price': doc.to_dict().get('price', 0)} for doc in sugar_levels_ref}

    return sizes, add_ons, temperatures, sugar_levels, milk_types


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

def display_branch_and_menu(branches, products, sizes, add_ons, temperatures, sugar_levels, milk_types):
    # Sidebar Branch Selection
    branch_names = list(branches.values())
    selected_branch_name = st.sidebar.selectbox("📍 Select Branch", branch_names)

    # Get the corresponding branch ID for the selected branch name
    selected_branch_id = next(branch_id for branch_id, branch_name in branches.items() if branch_name == selected_branch_name)

    # Category Selection with Icons
    category_filter = st.sidebar.selectbox("🍽️ Select Category", ["All Drinks", "Coffee", "Tea"], index=0)

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
                    st.image(item.get("image_url", ""), use_column_width=True)
                    st.markdown(f"### {item.get('product_name', 'Unknown Product')}")
                    st.write(f"💲 RM{item.get('base_price', 0):.2f}")
                    
                    # Add Button with Hover Effect and Immediate Feedback
                    add_button_key = f"add_{item['product_id']}"
                    if st.button(f"🛒 Add {item['product_name']}", key=add_button_key):
                        st.session_state["selected_product_id"] = item["product_id"]
                    
                    # Expander for Customization Options
                    if "selected_product_id" in st.session_state and st.session_state["selected_product_id"] == item["product_id"]:
                        with st.expander(f"🔧 Customize your {item['product_name']}"):
                            size = st.selectbox(f"Size for {item['product_name']}", options=[details['name'] for details in sizes.values()], key=f"size_{item['product_id']}")
                            add_on = st.multiselect(f"Add-Ons for {item['product_name']}", options=[details['name'] for details in add_ons.values()], key=f"addons_{item['product_id']}")
                            temperature_options = [details['name'] for details in temperatures.values()]
                            temperature = st.selectbox(f"Select Temperature", options=temperature_options, key=f"temperature_{item['product_id']}")
                            sugar_level = st.selectbox(f"Sugar Level", options=[details['name'] for details in sugar_levels.values()], key=f"sugar_{item['product_id']}")
                            milk_type = st.selectbox(f"Milk Type", options=[details['name'] for details in milk_types.values()], key=f"milk_{item['product_id']}")
                            quantity = st.number_input(f"Quantity", value=1, placeholder="Quantity")

                            # Add to Cart Button with Price Breakdown
                            if st.button(f"🛒 Add to Cart", key=f"add_to_cart_{item['product_id']}"):
                                size_price = sizes.get(size, {}).get("price", 0)
                                add_ons_prices = {addon: add_ons.get(addon, {}).get("price", 0) for addon in add_on}
                                temperature_price = next((item['price'] for key, item in temperatures.items() if item['name'] == temperature), 0)
                                milk_type_price = milk_types.get(milk_type, {}).get("price", 0)

                                total_price = item['base_price'] + size_price + sum(add_ons_prices.values()) + temperature_price + milk_type_price
                                
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
                                    "quantity": 1,
                                    "status": "In Cart",
                                    "email": cookies.get("email"),
                                    "quantity": quantity
                                }

                                # Save to Firebase
                                db.collection("cart").document(cart_id).set(cart_item)
                                
                                # Success Confirmation
                                st.success(f"✔️ Successfully added {item['product_name']} to the cart with Cart ID: {cart_id}!")
                                st.info(f"Total Price: RM{total_price*quantity:.2f}")
                                st.session_state["selected_product_id"] = None

    # Additional UX improvements
    st.write("---")
    st.write("💬 For any questions or assistance, feel free to reach out to our staff!") 

def display_cart(branches, email):
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
        df = pd.DataFrame(cart_items)
        st.dataframe(df)

        total_price = 0
        coupon_discount = 0
        loyalty_points_discount = 0
        final_price = 0

        # Iterate through the items in the cart
        for index, item in enumerate(cart_items):
            branch_id = item.get("branch_id", None)
            branch_name = branches.get(branch_id, "Unknown Branch")
            image_from_products = db.collection('product').where('product_name', '==', item['name'])

            image_query = image_from_products.stream()

            # Loop through the results (although we expect just one result)
            for doc in image_query:
                # Extract image_url field from the document
                product_data = doc.to_dict()
                image_url = product_data.get('image_url', None)

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
                st.markdown(f"**Addon:  {', '.join(item['addons']) if item['addons'] else 'None'}**")
                st.markdown(f"**{item['temperature']} | {item['sugar_level']} | {item['milk_type']}**")
                

            with price_col:
                item['item_total'] = item['price'] * item['quantity']
                total_price += item['item_total']

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
                               RM {item['item_total']:.2f}
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
                    st.write(f"Discount: RM {rm_discount} off")
                    coupon_discount = rm_discount
                elif discount_percentage > 0:
                    discount_amount = (discount_percentage / 100) * total_price
                    st.write(f"Discount: {discount_percentage}% off")
                    coupon_discount = discount_amount
            else:
                st.write("No discount available for this coupon.")
        else:
            st.write("Invalid coupon code.")
        
        if st.button("Use Points"):
            if loyalty_points > 0:
                loyalty_points_discount = min(loyalty_points // 100, total_price)
                points_used = loyalty_points_discount * 100  # Convert back to points

                # Deduct the points used from the total loyalty points
                new_points_balance = update_loyalty_points(email, 0, points_used)

                if new_points_balance is not None:
                    st.success(
                        f"Loyalty Points Discount Applied: -RM {loyalty_points_discount:.2f}\n"
                        f"Points Used: {points_used}\n"
                        f"New Loyalty Points Balance: {new_points_balance}"
                    )
                else:
                    st.error("Error updating loyalty points. Please try again.")
            else:
                st.warning("Not enough loyalty points for a discount!")

        final_price = total_price - coupon_discount - loyalty_points_discount

        st.markdown("")
        st.markdown("")
        st.markdown("")
        st.markdown("")
        st.markdown("")
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

                cart_ref = db.collection("cart").where("email", "==", email).where("status", "==", "In Cart")
                cart_items = [{"id": doc.id, **doc.to_dict()} for doc in cart_ref.get()]

                # Preprocess cart_items to replace empty addons with "None"
                for item in cart_items:
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
                                        "description": f"Size: {item['size']}, Add-on: {item['addons']}, Temperature: {item['temperature']}"
                                    },
                                    "unit_amount": item['price'] * 100,
                                },
                                "quantity": item['quantity'],
                            } for item in cart_items
                        ]

                        session = stripe.checkout.Session.create(
                            line_items=line_items,
                            mode="payment",
                            success_url="http://localhost:8501/success",
                            cancel_url="http://localhost:8501/customer",
                        )

                        # Redirect to Stripe checkout
                        st.success("Checkout session created successfully!")
                        st.markdown(f"[Proceed to Payment]({session.url})")

                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")

                    # Update Cart with new order_id and other details
                    for item in cart_items:
                        db.collection("cart").document(item['id']).update({
                            "order_id": order_id,
                            "status": "Preparing",
                            "ordered_time_date": ordered_time_date,
                        })
                        
                else:
                    st.warning("Your cart is empty. Please add items to proceed.")

        with clear_col[1]:
            # Button for Clear Cart
            if st.button("Clear Cart"):
                clear_cart(cookies.get("email"), status="In Cart")
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
        return "CART001"  # Default value in case of errors

def update_cart(email, ordered_time_date, coupon_code, final_price, total_price, coupon_discount, loyalty_points_discount):
    # Reference to the user's cart
    cart_ref = db.collection("cart").where("email", "==", email).where("status", "==", "In Cart")

    # Fetch the user's cart(s)
    cart_docs = cart_ref.get()

    # If cart exists, update the status to "Preparing" 
    if cart_docs:
        for doc in cart_docs:
            doc_ref = doc.reference
            # Randomly choose status
            status = "Preparing"
            doc_ref.update({
                "status": status,
                "ordered_time_date": ordered_time_date,
                "coupon_code": coupon_code,
                "final_price": final_price,
                "total_price": total_price,
                "coupon_discount": coupon_discount,
                "loyalty_points_discount": loyalty_points_discount
            })
        print(f"Cart status updated to '{status}' for user: {email}")
    else:
        print(f"No cart found for user: {email}")


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

def display_order_status():
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
            display_orders(cart_items)
        else:
            st.info("No orders are currently being prepared.")
    
    # Completed Orders
    with tab_completed:
        st.subheader("Your Orders are Ready for Pickup")
        cart_items = fetch_cart_items(email=email, status="Done")
        if cart_items:
            display_orders(cart_items)
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
            display_orders(cart_items)
        else:
            st.info("No order history found!")

# Helper function to display orders in a user-friendly format
def display_orders(cart_items):
    # Convert the list of cart items to a DataFrame
    df = pd.DataFrame(cart_items)

    # Display the DataFrame as a table with color-coded status
    def color_status(row):
        if row['status'] == 'Preparing':
            return 'background-color: #fff3cd;'
        elif row['status'] == 'Done':
            return 'background-color: #d4edda;'
        return ''

    if not df.empty:
        # Apply color coding for better visualization
        styled_df = df.style.applymap(lambda val: color_status(val) if 'status' in val else '', subset=['status'])
        st.dataframe(styled_df)
    else:
        st.info("No orders available.")

def display_loyalty_program(email):
    st.title("🎉 Loyalty Program")
    
    # Retrieve loyalty points
    loyalty_point = get_loyalty_points(email)
    loyalty_points_discount = loyalty_point // 100
    points_to_next_voucher = 100 - (loyalty_point % 100)
    
    # Section: Loyalty Points Summary
    st.subheader("✨ Your Points Summary")
    st.metric("Loyalty Points", f"{loyalty_point} points")
    
    # Redemption Information
    if loyalty_points_discount > 0:
        st.success(f"💸 You can redeem RM{loyalty_points_discount}. Visit the counter to claim!")
    else:
        st.info(f"🚀 Earn {points_to_next_voucher} more points to redeem RM1 voucher!")
    
    st.write("---")  # Divider for better organization
    
    # Section: How to Earn Points
    st.subheader("🛒 How to Earn Points")
    st.write("""
    - 💵 Spend RM1 to earn 1 loyalty point.
    - 🎂 Celebrate your birthday with bonus points!
    - 🏆 Participate in special promotions to earn extra rewards.
    """)

    # Motivational Footer
    st.write("---")
    st.info("Keep earning points to enjoy more rewards. Thank you for being a valued customer! 🎉")

def get_next_feedback_id():
    try:
        cart_ref = db.collection("cart")
        
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
                return f"FEED{last_number:03d}"  # Create feedback ID with the same number
        else:
            # No previous orders exist
            return None  # Indicate no feedback ID can be generated

    except Exception as e:
        print(f"An error occurred while retrieving the feedback ID: {e}")
        return None  # Indicate no feedback ID in case of errors

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
            "feedback_id": feedback_id,
            "rate_coffee": coffee_rating,
            "rate_service": service_rating,
            "rate_wait_time": time_rating,
            "rate_environment": environment_rating,
            "rate_sanitary": sanitary_rating,
            "email": email,
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
    page = st.sidebar.selectbox("Navigate to", ("Menu", "Cart", "Order Status", "Loyalty Program", "Feedback"))
    if page == "Menu":
        st.title("PyBean Coffee Shop")
        st.subheader("Select Your Drinks")
        display_branch_and_menu(branches, products, sizes, add_ons, temperatures, sugar_levels, milk_types)
    elif page == "Cart":
        display_cart(branches, cookies.get("email"))
    elif page == "Order Status":
        display_order_status()
    elif page == "Loyalty Program":
        display_loyalty_program(cookies.get("email"))
    elif page == "Feedback":
        display_feedback(cookies.get("email"))

branches, products, sizes, milk, addons = fetch_data_from_firestore()
sizes, add_ons, temperatures, sugar_levels, milk_types = get_product_details()

# Initialize session state
if "cart" not in st.session_state:
    st.session_state["cart"] = []
if "order_history" not in st.session_state:
    st.session_state["order_history"] = []
if "loyalty_points" not in st.session_state:
    st.session_state["loyalty_points"] = 0

# Display app content
display_sidebar(branches, products, sizes)

# Query to get "done" and "ongoing" carts
all_cart = db.collection("cart").get()
done = db.collection("cart").where("status", "==", "Done").get()
ongoing = db.collection("cart").where("status", "==", "Preparing").get()

# Convert query results to a list of dictionaries
done_data = [doc.to_dict() for doc in done]
ongoing_data = [doc.to_dict() for doc in ongoing]
all_cart_data = [doc.to_dict() for doc in all_cart]

# Convert the list of dictionaries to DataFrames
done_df = pd.DataFrame(done_data)
ongoing_df = pd.DataFrame(ongoing_data)
all_cart_df = pd.DataFrame(all_cart_data)

# Display the results in Streamlit
#st.title("This is Status Done")
#st.dataframe(done_df)

#st.title("This is Status Ongoing")
#st.dataframe(ongoing_df)

#st.title("This is all cart")
#st.dataframe(all_cart_df)


if st.sidebar.button("Log out"):
    logout()