import streamlit as st
from inventory_page import inventory
from coupon_page import coupon
from navigation import make_sidebar, logout
from functions import cookies

make_sidebar()

page = st.sidebar.selectbox("Navigate to", ["Inventory Management", "Coupon Management"])

if page == "Inventory Management":
    inventory()
elif page == "Coupon Management":
    coupon()

st.sidebar.markdown("<br><br><br><br><br><br><br><br><br><br><br>", unsafe_allow_html=True)

if st.sidebar.button("Log out"):
    logout()
