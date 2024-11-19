import streamlit as st
from time import sleep
import streamlit.components.v1 as components
from navigation import make_sidebar

make_sidebar()

# Set the title of the app
st.title("Payment Successful")

# Display the message
st.markdown("""
## Thank you for your payment!
You can now safely close this page.
""")
