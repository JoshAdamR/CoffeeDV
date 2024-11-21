import streamlit as st
import pandas as pd
from firebase_config import store  # Import Firestore client from config
from datetime import datetime

def run():
    # Function to get all offers from the Firestore coupon collection
    def get_offers():
        offers_ref = store.collection('coupon')
        return pd.DataFrame([doc.to_dict() for doc in offers_ref.stream()])

    # Function to check if a coupon with the same code already exists
    def coupon_exists(offer_code):
        offer_ref = store.collection('coupon').where('coupon_code', '==', offer_code)
        docs = offer_ref.stream()
        return len(list(docs)) > 0  # Return True if coupon exists

    # Function to add a new offer to the Firestore coupon collection
    def add_offer(offer_code, promotion_type, discount, start_date, expiry_date):
        if coupon_exists(offer_code):  # Check if coupon already exists
            st.error(f"Coupon with code '{offer_code}' already exists. Please choose a different code.")
            return False
        
        # Convert start_date and expiry_date to datetime
        start_date = datetime.combine(start_date, datetime.min.time())
        expiry_date = datetime.combine(expiry_date, datetime.min.time())
        
        # Prepare the data to be added
        offer_data = {
            'coupon_code': offer_code,
            'promotion_type': promotion_type,
            'discount_percentage': discount if promotion_type == 'Percentage' else 0,
            'rm_discount': discount if promotion_type == 'Flat Rate' else 0,
            'start_date': start_date,
            'expiry_date': expiry_date
        }
        
        # Add the offer data to the 'coupon' collection in Firestore
        store.collection('coupon').add(offer_data)
        
        st.success(f"Offer with Coupon Code '{offer_code}' added successfully!")  # Success message
        return True  # Return True indicating the offer was added

    # Function to remove an offer from the Firestore coupon collection
    def remove_offer(offer_code):
        # Query to find the offer by coupon_code
        offer_ref = store.collection('coupon').where('coupon_code', '==', offer_code)
        docs = offer_ref.stream()
        
        # If offer is found, remove it
        for doc in docs:
            store.collection('coupon').document(doc.id).delete()
        
        st.success(f"Offer with coupon code '{offer_code}' has been removed.")

    # Streamlit App Layout
    st.title("Coupon Management")

    # Fetch current offers to display and store in session state
    if 'offers' not in st.session_state:
        st.session_state.offers = get_offers()  # Load offers only once when the app is first loaded

    # Display current special offers - dynamically updated
    st.subheader("Current Special Offers")
    st.write(st.session_state.offers)  # Display the offers stored in session state

    # Admin options to add special offers
    with st.form(key='offer_form'):
        offer_code = st.text_input("Coupon Code")
        promotion_type = st.selectbox("Promotion Type", ['Percentage', 'Flat Rate'])
        discount = st.number_input("Discount Amount", min_value=0, max_value=100)
        start_date = st.date_input("Start Date", pd.to_datetime('today'))
        expiry_date = st.date_input("Expiry Date", pd.to_datetime('today'))
        
        if st.form_submit_button("Add Offer"):
            # Add offer only if it's not a duplicate
            if add_offer(offer_code, promotion_type, discount, start_date, expiry_date):
                # Update the session state with the new list of offers after adding
                st.session_state.offers = get_offers()  # Refresh the offers data
                # Update the displayed table with the new data
                st.rerun()  # This will refresh the entire app and update the table immediately

    # Remove Offer Section
    st.subheader("Remove Offer")
    remove_offer_code = st.text_input("Enter Coupon Code to Remove")
    if st.button("Remove Offer"):
        remove_offer(remove_offer_code)
        # Update the session state with the new list of offers after removal
        st.session_state.offers = get_offers()  # Refresh the offers data
        # Update the displayed table with the new data
        st.rerun()  # This will refresh the entire app and update the table immediately

    # Visualization Section