import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

# Check if the Firebase app is already initialized
if not firebase_admin._apps:
    # Initialize Firebase Admin SDK
    cred = credentials.Certificate(r"c:\Users\user\Downloads\coffeeshop-54872-firebase-adminsdk-if85u-f0eabc8124.json")
    firebase_admin.initialize_app(cred)

# Create Firestore client
store = firestore.client()

# Functions to interact with Firestore
def get_branches():
    branches_ref = store.collection('branch')
    return pd.DataFrame([doc.to_dict() for doc in branches_ref.stream()])

def get_inventory():
    inventory_ref = store.collection('inventory')
    return pd.DataFrame([doc.to_dict() for doc in inventory_ref.stream()])

def get_offers():
    offers_ref = store.collection('coupon')
    return pd.DataFrame([doc.to_dict() for doc in offers_ref.stream()])

def update_stock(item_name, quantity, action):
    """Update stock based on sales or restock."""
    inventory_ref = store.collection('inventory').where('inventory_name', '==', item_name)
    docs = inventory_ref.stream()
    for doc in docs:    
        current_quantity = doc.to_dict()['quantity_on_hand']
        if action == "sell":
            new_quantity = current_quantity - quantity
        elif action == "restock":
            new_quantity = current_quantity + quantity
        else:
            st.error("Invalid action. Use 'sell' or 'restock'.")
            return
        store.collection('inventory').document(doc.id).update({'quantity_on_hand': new_quantity})

def remove_offer(coupon_code):
    """Remove an offer based on the coupon code."""
    offers_ref = store.collection('coupon').where('coupon_code', '==', coupon_code)
    docs = offers_ref.stream()
    for doc in docs:
        store.collection('coupon').document(doc.id).delete()

def add_offer(coupon_code, promotion_type, discount, start_date, expiry_date):
    """Add a new special offer to Firestore."""
    offers_ref = store.collection('coupon')
    offer_data = {
        'coupon_code': coupon_code,
        'promotion_type': promotion_type,
        'discount_percentage': discount,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'expiry_date': expiry_date.strftime('%Y-%m-%d')
    }
    offers_ref.add(offer_data)

# Load data from Firestore
branches = get_branches()
inventory = get_inventory()
offers = get_offers()

# Streamlit App Layout
st.title("Inventory Management System")
st.sidebar.header("Inventory Management")

# Multi-Branch Support
selected_branch_id = st.sidebar.selectbox("Select Branch", branches['branch_name'].tolist())
selected_branch = branches[branches['branch_name'] == selected_branch_id]

# Display branch details
st.subheader(f"Branch Details: {selected_branch['branch_name'].values[0]}")
st.write(f"Location: {selected_branch['location'].values[0]}")
st.write(f"Operating Cost: ${selected_branch['operating_cost'].values[0]}")

# Display inventory for the selected branch
st.subheader(f"Inventory for {selected_branch_id}")
branch_inventory = inventory[inventory['branch_id'] == selected_branch['branch_id'].values[0]] # Adjust this line to filter by branch if needed
inventory_display = st.dataframe(branch_inventory)  # Store initial display

# Update stock based on sales or restock
action = st.sidebar.radio("Select Action", ["Sell Items", "Restock Items"])
selected_items = st.sidebar.multiselect("Select Items", branch_inventory['inventory_name'].tolist())
quantity = st.sidebar.number_input("Quantity", min_value=1, value=1, step=1)

if st.sidebar.button("Update Stock"):
    for item in selected_items:
        if action == "Sell Items":
            update_stock(item, quantity, "sell")  # Reduce quantity by specified amount
        elif action == "Restock Items":
            update_stock(item, quantity, "restock")  # Increase quantity by specified amount
    st.success(f"{action} updated!")

    # Refresh the inventory data from Firestore after update
    inventory = get_inventory()  # Reload inventory data after update
    branch_inventory = inventory#[inventory['branch_id'] == selected_branch['branch_id'].values[0]] # Ensure the branch inventory is updated

    # Update the existing display instead of creating a new one
    inventory_display.empty()  # Clear the previous display
    inventory_display.dataframe(branch_inventory)  # Show the updated inventory

# Notifications for low stock
low_stock_items = branch_inventory[branch_inventory['quantity_on_hand'] < branch_inventory['minimum_stock_level']]
if not low_stock_items.empty:
    st.warning("Low stock for the following items:")
    st.write(low_stock_items)

# Manage Offers Section
st.sidebar.subheader("Manage Special Offers")

# Display daily special offers
st.subheader("Current Special Offers")
st.write(offers)

# Admin options to add special offers
with st.sidebar.form(key='offer_form'):
    offer_code = st.text_input("Coupon Code")
    promotion_type = st.selectbox("Promotion Type", ['Percentage', 'Flat Rate'])
    discount = st.number_input("Discount Amount", min_value=0, max_value=100)
    start_date = st.date_input("Start Date", pd.to_datetime('today'))
    expiry_date = st.date_input("Expiry Date", pd.to_datetime('today'))
    if st.form_submit_button("Add Offer"):
        add_offer(offer_code, promotion_type, discount, start_date, expiry_date)
        st.success("Special offer added!")

# Remove Offer Section
st.sidebar.subheader("Remove Offer")
remove_offer_code = st.sidebar.text_input("Enter Coupon Code to Remove")
if st.sidebar.button("Remove Offer"):
    remove_offer(remove_offer_code)
    st.success(f"Offer with coupon code '{remove_offer_code}' has been removed.")
    # Refresh offers after removal
    offers = get_offers()  # Reload offers data after removal
    st.write(offers)  # Show the updated offers
