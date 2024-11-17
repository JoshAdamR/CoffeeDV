import streamlit as st
import pandas as pd
from firebase_admin import credentials, firestore
from time import sleep
from navigation import make_sidebar, logout
from functions import add_entry, get_entries, is_valid_email, is_valid_password, email_exists, fetch_user

make_sidebar()

st.header("Sign Up")
st.write("Enter a username, email, and password to register:")

username = st.text_input("Username")
email = st.text_input("Email")
password = st.text_input("Password", type='password')

if st.button("Sign Up"):
    if username and email and password:
        if not is_valid_email(email):
            st.error("Invalid email format.")
        elif email_exists(email):
            st.error("This email is already taken. Please use a different email.")
        elif not is_valid_password(password):
            st.error("Password must be at least 8 characters long, contain at least one uppercase letter, one number, and one special character.")
        else:
            add_entry(username, email, password)
            st.success("Sign up successful! You can now log in.")
            logout()
    else:
        st.error("Please fill in all fields.")

# Display all entries from Firestore in a DataFrame, including roles
st.subheader("Current Users in the Database")
entries = get_entries()
if entries:
    df = pd.DataFrame(entries)
    st.dataframe(df)
else:
    st.write("No entries found.")