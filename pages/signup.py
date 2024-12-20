import streamlit as st
import pandas as pd
from time import sleep
from datetime import datetime
from navigation import make_sidebar, logout
from functions import add_entry, get_entries, is_valid_email, is_valid_password, email_exists, fetch_user, cookies, is_valid_name

make_sidebar()

st.header("Sign Up")
st.write("Enter a username, email, and password to register:")

fullname = st.text_input("Full Name", help="Enter your full legal name.").upper()
username = st.text_input("Username")
email = st.text_input("Email")
password = st.text_input("Password", type='password')
birthday = st.date_input("Birthday", help="Enter your date of birth")
gender = st.radio("Gender", options=["Male", "Female"]) 
datejoin = datetime.now().strftime("%Y-%m-%d")
loyalty_point = 0

if st.button("Sign Up"):
    if username and email and password and birthday and gender and fullname:
        # Check if the full name is valid
        valid_fullname = is_valid_name(fullname)
        if not valid_fullname:
            st.error("❌ Full Name must contain only alphabets and spaces.")
        elif not is_valid_email(email):
            st.error("Invalid email format.")
        elif email_exists(email):
            st.error("This email is already taken. Please use a different email.")
        elif not is_valid_password(password):
            st.error("Password must be at least 8 characters long, contain at least one uppercase letter, one number, and one special character.")
        else:
            # Proceed with sign-up if all fields are valid
            add_entry(valid_fullname, username, email, password, birthday.strftime("%Y-%m-%d"), gender, datejoin, loyalty_point)
            st.success("Sign up successful! You can now log in.")
            sleep(0.5)
            st.switch_page("app.py")
    else:
        st.error("Please fill in all fields.")

st.sidebar.markdown("<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>", unsafe_allow_html=True)
if st.sidebar.button("Back"):
    logout()

# st.write(cookies.getAll())
