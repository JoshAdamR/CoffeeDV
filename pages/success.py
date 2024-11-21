import streamlit as st
from time import sleep
import streamlit.components.v1 as components
from navigation import make_sidebar
from firebase_config import store  # Import Firestore client from config
from functions import add_entry, get_entries, is_valid_email, is_valid_password, email_exists, fetch_user, cookies, getCookies, create_pdf, fetch_cart_data
from dbcoffee import customer_table, cart_table
from datetime import datetime
import pandas as pd


db = store
invoice_id = cookies.get("invoice_id")



customer_details = customer_table[customer_table['email'] == cookies.get("email")]
cart_details_ref  = db.collection('cart').where("invoice_id", "==", invoice_id)

# Get the query results
cart_details = cart_details_ref.stream()

# Convert the Firestore documents to a list of dictionaries
cart_data = []
for doc in cart_details:
    cart_data.append(doc.to_dict())  # Convert each document to a dictionary

customer_id = customer_details['customer_id'].iloc[0]
date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
email = customer_details['email'].iloc[0]
customer_name = customer_details['customer_name'].iloc[0]

make_sidebar()

# Set the title of the app
st.title("Payment Successful")

# Display the message
st.markdown("""
## Thank you for your payment!
""")

if invoice_id:
    cart_data = fetch_cart_data(invoice_id)
    if cart_data:
        entry = {
            "invoice_id": invoice_id,
            "customer_id": customer_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "email": email,
            "name": customer_name,
        }
        pdf_buffer = create_pdf(entry, cart_data)
        st.download_button(
            label="Download Invoice PDF",
            data=pdf_buffer,
            file_name=f"{invoice_id}_{date}_{customer_name}.pdf",
            mime="application/pdf"
        )
    else:
        st.error("No data found for this Invoice ID.")
else:
    st.error("Please enter a valid Invoice ID.")

# Display the message
st.markdown("""
You can now safely close this page.
""")