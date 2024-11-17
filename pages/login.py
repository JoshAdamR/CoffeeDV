import streamlit as st
import pandas as pd
from firebase_admin import credentials, firestore
from time import sleep
from navigation import make_sidebar
from functions import add_entry, get_entries, is_valid_email, is_valid_password, email_exists, fetch_user

make_sidebar()


st.header("Login")
st.write("Please enter your email and password to log in:")

email = st.text_input("Email")
password = st.text_input("Password", type='password')

if st.button("Log In"):
    if email and password:
        user = fetch_user(email, password)
        if user:
            st.success(f"Welcome back, {user['username']}!")
            role = user.get("role", "customer")
            if role == 'admin':
                st.write("You are logged in as an **Admin**.")
            else:
                st.write("You are logged in as a **Customer**.")
                st.balloons()
        else:
            st.error("Invalid email or password. Please try again.")
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