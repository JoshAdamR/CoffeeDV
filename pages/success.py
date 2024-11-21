import streamlit as st
from time import sleep
import streamlit.components.v1 as components
from navigation import make_sidebar
from functions import add_entry, get_entries, is_valid_email, is_valid_password, email_exists, fetch_user, cookies, getCookies


make_sidebar()

# Set the title of the app
st.title("Payment Successful")

# Display the message
st.markdown("""
## Thank you for your payment!
You can now safely close this page.
""")

st.write(cookies.getAll())
