import streamlit as st
import pandas as pd
import time 
import firebase_admin
import stripe
from firebase_admin import credentials, firestore
from navigation import make_sidebar, logout
from functions import cookies

make_sidebar()


st.write(cookies.getAll())
# st.write(f"**Email:** {cookies.get('email')}")
# # st.write(f"**Username:** {st.session_state.username}")
# st.write(f"**Password:** {cookies.get('password')} (stored for session test)")

# Initialize session state for cart and order history
if 'order_history' not in st.session_state:
    st.session_state['order_history'] = []
if 'cart' not in st.session_state:
    st.session_state['cart'] = []
if 'order_number' not in st.session_state:
    st.session_state['order_number'] = 1
if 'loyalty_points' not in st.session_state:
    st.session_state['loyalty_points'] = 0
if 'selected_coffee' not in st.session_state:
    st.session_state['selected_coffee'] = None
if 'notifications' not in st.session_state:
    st.session_state['notifications'] = []
if 'loyalty_points' not in st.session_state:
    st.session_state['loyalty_points'] = 0

LOYALTY_POINTS_PER_RM = 0.1  # 10% of the total price as points

# Function to add items to the cart
def add_to_cart(coffee, size, price):
    item = {
        'coffee': coffee,
        'size': size,
        'price': price
    }
    st.session_state['cart'].append(item)
    st.success(f"{coffee} added to cart!")

# Initialize Firebase
cred_path = "firebase_credentials.json"

# Check if Firebase app is already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

# Initialize Firestore
db = firestore.client()

# Set up Stripe
stripe.api_key = "sk_test_CsnggH3iChIYjrFoue5y6M98"

# Page configuration and styling
#st.set_page_config(page_title="PyBean Coffee Shop", page_icon="☕", layout="wide")

# Notification for order
# low_stock_items = order[order['status'] == 'ready']
# if not low_stock_items.empty:
#     st.success("Order is ready!")
#     st.write(low_stock_items)

# Sidebar for navigation
st.sidebar.title("")
page = st.sidebar.selectbox("Select Option", ("Menu", "Cart", "Order Status", "Order History", "Loyalty Program", "Feedback"))

# Define coffee menu with images and prices
menu = {
    "Americano": {"price": 9.0, "image": "https://mocktail.net/wp-content/uploads/2022/03/homemade-Iced-Americano-recipe_1ig.jpg"},
    "Cappuccino": {"price": 12.5, "image": "https://upload.wikimedia.org/wikipedia/commons/c/c8/Cappuccino_at_Sightglass_Coffee.jpg"},
    "Latte": {"price": 12.5, "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/Caffe_Latte_at_Pulse_Cafe.jpg/640px-Caffe_Latte_at_Pulse_Cafe.jpg"},
    "Caramel Macchiato": {"price": 15.0, "image": "https://www.folgerscoffee.com/folgers/recipes/_Hero%20Images/Detail%20Pages/5596/image-thumb__5596__schema_image/CaramelMacchiato-hero.1fb90577.jpg"},
    "Espresso": {"price": 8.0, "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSbeuOQDfnyYHHX61LrO1iF6fAiBeBDAdy2Dw&s"},
    "Long Black": {"price": 9.0, "image": "https://www.tasteatlas.com/images/ingredients/ede9652f559e4948808c058843c97574.jpg"},
    "Doppio": {"price": 12.0, "image": "https://www.luxcafeclub.com/cdn/shop/articles/Doppio_Coffee_1100x.png?v=1713834822"},
    "Red Eye": {"price": 18.0, "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSdO-3gOk1AgOZlJ_spIChFB5DvzDwZwCQSjA&s"},
    "Lungo": {"price": 12.0, "image": "https://www.wakacoffee.com/cdn/shop/articles/what-is-lungo-espresso-coffee.jpg?v=1593313291"},
    "Mocha": {"price": 12.5, "image": "https://www.allrecipes.com/thmb/U-LzBq7WxRoRg-D8w2i33NpHStE=/1500x0/filters:no_upscale():max_bytes(150000):strip_icc()/23538-mocha-coffee-ddmfs-4x3-1-e3a40f5fe05f40e0abf0faa01293f211.jpg"},
    "Ristretto": {"price": 9.0, "image": "https://www.shutterstock.com/image-photo/cup-italian-ristretto-coffee-small-260nw-430842625.jpg"},
    "Flat White": {"price": 12.0, "image": "https://www.thespruceeats.com/thmb/9S62tUo57EiVNFSi_SiGcj2aypk=/1500x0/filters:no_upscale():max_bytes(150000):strip_icc()/flat-white-recipe-765371-hero-01-d3378484dc6044259ac75c49407097ec.jpg"},
    "Affogato": {"price": 15.0, "image": "https://www.thespruceeats.com/thmb/5PcCBEaUd1U1eFxfcKKPLVnZzfA=/1500x0/filters:no_upscale():max_bytes(150000):strip_icc()/affogato-4776668-hero-08-40d7a68d12ba46f48eaea3c43aba715c.jpg"},
    "Cortado": {"price": 10.0, "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRsD2RKaN-OY-35n37KdqGfpg4CgCgIGvH8VA&s"},
}
sizes = {"Small": 0, "Medium": 0.5, "Large": 1.0}
addons = {"None": 0, "Extra sugar": 0.2, "Milk": 0.3, "Soy milk": 0.5, "Almond milk": 0.7, "Whipped cream": 0.4}
#milk = {"Small": 0, "Medium": 0.5, "Large": 1.0}

# Handle different pages
if page == "Menu":
    st.title("PyBean Coffee Shop")
    st.subheader("Select Your Drinks")

    # Display menu with clickable images and text
    for coffee, details in menu.items():
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button(f"{coffee}", key=f"{coffee}_button"):
                st.session_state['selected_coffee'] = coffee
        with col2:
            st.image(details["image"], width=100)
            st.write(f"**{coffee}** - RM {details['price']:.2f}")

    # Show customization options if a coffee has been selected
    if st.session_state['selected_coffee']:
        selected_coffee = st.session_state['selected_coffee']
        st.write(f"### Customizing: {selected_coffee}")

        size_choice = st.selectbox("Choose your size", list(sizes.keys()), key="size")
        #milk_option = st.selectbox("Choose milk", list(milk.keys()), key="milk")
        addon_choice = st.selectbox("Choose your add-on", list(addons.keys()), key="addon")

        temperature_choice = st.selectbox("Choose temperature", ["Hot", "Ice"], key="temperature")

        if temperature_choice == "Ice":
            ice_level = st.selectbox("Ice level", ["More ice", "Normal", "Less ice"], key="ice_level")
        else:
            ice_level = "N/A"

        # Calculate total price based on selections
        base_price = menu[selected_coffee]["price"]
        size_price = sizes[size_choice]
        #milk_price = milk[milk_option]
        addon_price = addons[addon_choice]
        total_price = base_price + size_price + addon_price

        # Add to cart button
        if st.button("Add to Cart"):
            order = {
                "coffee": selected_coffee,
                "size": size_choice,
                "addon": addon_choice,
                "temperature": temperature_choice,
                "ice_level": ice_level,
                "total_price": total_price,
                "order_number": st.session_state['order_number'],
            }
            st.session_state['cart'].append(order)
            st.success(f"{selected_coffee} added to cart!")
            st.session_state['selected_coffee'] = None  

elif page == "Cart":
    st.title("Your Cart")
    
    # Calculate total price
    total_price = sum(item['total_price'] for item in st.session_state['cart'])  # Use 'total_price'
    
    if st.session_state['cart']:
        for i, item in enumerate(st.session_state['cart'], start=1):
            st.write(f"### Item {i}: {item['coffee']} ({item['size']} - {item['addon']})")
            st.write(f"Temperature: {item['temperature']}, Ice Level: {item['ice_level']}")
            st.write(f"Price: RM {item['total_price']:.2f}")  # Use 'total_price'
        st.write("### Total Price")
        st.write(f"**Total Price:** RM {total_price:.2f}")
        
        if st.button("Place Order"):
            if total_price > 0:
                try:
                    # Create Stripe checkout session with all items in the cart
                    line_items = [
                        {
                            "price_data": {
                                "currency": "myr",  # Stripe uses MYR (Malaysian Ringgit) for Malaysia
                                "product_data": {"name": item['coffee'],
                                                 "description": f"Size: {item['size']}, Add-on: {item['addon']}, Temperature: {item['temperature']}, Ice-level: {item['ice_level']}"},
                                "unit_amount": int(item['total_price'] * 100),  # Stripe expects the amount in cents
                            },
                            "quantity": 1,  # Quantity for the item
                        }   
                        for item in st.session_state['cart']
                    ]

                    #metadata = item['size']

                    # Create the checkout session
                    session = stripe.checkout.Session.create(
                        line_items=line_items,
                        mode="payment",
                        success_url="http://localhost:8501/success",  # Replace with your actual success URL
                        cancel_url="http://localhost:8501/customer",   # Replace with your actual cancel URL
                    )

                    # Save cart to Firestore
                    for item in st.session_state['cart']:
                        new_order = {   
                            'order_number': st.session_state['order_number'],
                            'coffee': item['coffee'],
                            'size': item['size'],
                            'addon': item['addon'],
                            'temperature': item['temperature'],
                            'ice_level': item['ice_level'],
                            'total_price': item['total_price']
                        }
                        db.collection("orders").add(new_order)

                    # Add the new order to the order history
                    st.session_state['order_history'].append(new_order)

                    # Accumulate total price for loyalty points
                    total_order_price = sum(item['total_price'] for item in st.session_state['cart'])
                    loyalty_points_earned = total_order_price * LOYALTY_POINTS_PER_RM
                    st.session_state['loyalty_points'] += loyalty_points_earned

                    # Clear the cart
                    st.session_state['cart'] = []
                    st.session_state['order_number'] += 1  

                    # Redirect the user to Stripe's checkout page
                    st.success("Checkout session created successfully!")
                    st.markdown(f"[Proceed to Payment]({session.url})")

                    #print(session)

                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
            else:
                st.warning("Your cart is empty. Please add items to proceed.")
    else:
        st.write("Your cart is empty.")

    #st.success("Payment successfully!")

elif page == "Order Status":
    st.title("Order Status")

    if st.session_state['order_history']:
        # Display all orders in order history
        st.write("### Your Orders")
        for order in st.session_state['order_history']:
            order_number = order['order_number']
            st.write(f"### Order Number: #{order_number:03}")
            st.write(f"**Coffee:** {order['coffee']}")
            st.write(f"**Size:** {order['size']}")
            st.write(f"**Addon:** {order['addon']}")
            st.write(f"**Temperature:** {order['temperature']}")
            if order['temperature'] == "Ice":
                st.write(f"**Ice Level:** {order['ice_level']}")
            st.write(f"**Total Price:** RM {order['total_price']:.2f}")
            st.write(f"**Status:** {order.get('status', 'Done')}")  # Display status if available
            st.write("---")  # Separator for each order

        # Get the most recent order to update its status
        current_order = st.session_state['order_history'][-1]

        # Update status to Preparing
        current_order['status'] = "Preparing"
        st.write("Your order is being prepared by the barista.")
        time.sleep(3)  # Simulate time for preparation

        # Update status to Ready for pickup
        current_order['status'] = "Ready for pickup"
        st.session_state['notifications'].append(f"Order {current_order['order_number']} is ready for pickup!")
        st.write("Your order is ready for pickup!")
        time.sleep(3)  # Simulate time before pickup notification

        # Update status to Picked up
        current_order['status'] = "Picked up"
        st.write("Successfully picked up.")

        # Check if there are still orders in the history
        if len(st.session_state['order_history']) > 1:
            st.write("You still have pending orders.")
        else:
            st.write("You have no more pending orders.")

    else:
        st.write("You have not ordered anything yet.")

elif page == "Order History":
    st.title("Order History")
    # Display order history
    if st.session_state['order_history']:
        st.write("### Order History")
        for order in st.session_state['order_history']:
            st.write(f"**Order Number:** {order['order_number']}")
            st.write(f"**Coffee:** {order['coffee']}")
            st.write(f"**Size:** {order['size']}")
            st.write(f"**Total Price:** RM {order['total_price']:.2f}")
            st.write("---")  # Separator for each order
    else:
        st.write("No orders placed yet.")

elif page == "Loyalty Program":
    st.title("Loyalty Program")
    st.subheader("Loyalty Program")
    
    points = st.session_state['loyalty_points']
    st.write(f"### You have {points} loyalty points.")
    
    # Define membership levels
    membership_levels = {
        "Silver": 100,
        "Gold": 500,
        "Platinum": 1000,
        "VVVIP": 5000
    }
    
    # Display membership levels with progress bars
    st.write("## Membership Levels")
    for level, threshold in membership_levels.items():
        progress = min(points / threshold, 1.0)
        st.write(f"**{level} Membership**: Requires {threshold} points")
        st.progress(progress)
    
    # Calculate points needed for next level
    next_level = next((level for level, threshold in membership_levels.items() if points < threshold), "Max Level")
    if next_level != "Max Level":
        points_needed = membership_levels[next_level] - points
        st.write(f"### You need {points_needed} points to reach {next_level} Membership.")
    
    # Display redeemable prizes
    st.write("## Enjoy The Biggest Discount!!!")
    st.write("**5% Off One Drink per Bill Daily**: Silver Membership")
    st.write("**10% Off One Drink per Bill Daily**: Gold Membership")
    st.write("**20% Off One Drink per Bill Daily**: Platinum Membership")
    st.write("**20% Off One Bill Daily**: Platinum Membership")
    

elif page == "Feedback":
    st.title("Feedback")
    st.subheader("Rate Your Coffee and Service")
    
    coffee_rating = st.slider("Rate your coffee", 1, 5)
    service_rating = st.slider("Rate the service", 1, 5)
    time_rating = st.slider("Rate the time waiting", 1, 5)
    environment_rating = st.slider("Rate the environment", 1, 5)
    sanitary_rating = st.slider("Rate the sanitary", 1, 5)
    
    if st.button("Submit Feedback"):
        st.success("Thank you for your feedback! Please redeem a small Americano from our counter. Thank YOU!")

        # Preparing feedback data to send to Firestore
        feedback_data = {
            "coffee_rating": coffee_rating,
            "service_rating": service_rating,
            "time_rating": time_rating,
            "environment_rating": environment_rating,
            "sanitary_rating": sanitary_rating
        }
        # Place the order in Firestore
        db.collection("feedback").add(feedback_data)
        st.info("Your feedback has been recorded!")


st.sidebar.markdown("<br><br><br><br><br><br><br><br><br><br>", unsafe_allow_html=True)
if st.sidebar.button("Log out"):
    logout()