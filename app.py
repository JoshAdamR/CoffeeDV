import streamlit as st
from time import sleep
import pandas as pd
from navigation import make_sidebar, clearCookies, about_page
from functions import add_entry, get_entries, is_valid_email, is_valid_password, email_exists, fetch_user, cookies, getCookies


make_sidebar()
# clearCookies()

page = st.sidebar.selectbox("Navigate to", ["Login", "About Us"])

if page == "Login":
    st.markdown("""
    <div style="text-align: center; font-size: 36px; font-weight: bold; line-height: 1.5;">
        ✨ Welcome to Login Page ✨
        <br><br>
    </div>
    """, unsafe_allow_html=True)

    email = st.text_input("Email")
    password = st.text_input("Password", type='password')

    st.markdown("""<br>""", unsafe_allow_html=True)

    if st.button("Log In"):
        if (email and password):
            user = fetch_user(email, password)
            if user:
                getCookies(email)
                st.success(f"Welcome back, {user['username']}!")
                # role = user.get("role", "customer")
                while cookies.get("role") == 'admin' and cookies.get("status") == 'true':
                    # st.write("You are logged in as an **Admin**.")
                    # st.session_state.logged_in_admin = True
                    st.success("Logged in successfully!")
                    sleep(0.5)
                    st.switch_page("pages/admin.py")
                    st.balloons()
                    
                    
                while cookies.get("role") == 'customer' and cookies.get("status") == 'true':
                    # st.write("You are logged in as a **Customer**.")
                    # st.session_state.logged_in_cust = True
                    st.success("Logged in successfully!")
                    sleep(0.5)
                    st.switch_page("pages/customer.py")
                    st.balloons()

                while cookies.get("role") == 'branch' and cookies.get("status") == 'true':
                    # st.write("You are logged in as a **Customer**.")
                    # st.session_state.logged_in_cust = True
                    st.success("Logged in successfully!")
                    sleep(0.5)
                    st.switch_page("pages/branch.py")
                    st.balloons()
                    

            else:
                st.error("Invalid email or password. Please try again.")
                
        else:
            st.error("Please fill in all fields.")

    if st.button("Sign Up"):
        # st.session_state.signup = True
        st.success("Directing to Signup Page!")
        sleep(0.5)
        st.switch_page("pages/signup.py")

elif page == "About Us":
    about_page()

st.write(cookies.getAll())

# st.write(cookies.get("birthday"))





