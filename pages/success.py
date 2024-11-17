import streamlit as st
from time import sleep

st.write("Payment Successful!")
sleep(0.5)
st.switch_page("pages/customer.py")