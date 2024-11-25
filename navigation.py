import streamlit as st
from time import sleep
from streamlit.runtime.scriptrunner import get_script_run_ctx
from streamlit.source_util import get_pages
import pandas as pd
from functions import add_entry, get_entries, is_valid_email, is_valid_password, email_exists, fetch_user, cookies, getCookies
from streamlit_cookies_controller import CookieController, RemoveEmptyElementContainer


def get_current_page_name():
    ctx = get_script_run_ctx()
    if ctx is None:
        raise RuntimeError("Couldn't get script context")

    pages = get_pages("")

    return pages[ctx.page_script_hash]["page_name"]


def make_sidebar():
    with st.sidebar:
        st.title("🫘 PyBean")
        # st.write("")
        # st.write("")

        # if st.session_state.get("logged_in_cust", False):
        #     st.page_link("pages/customer.py", label = "")
        #     #st.page_link("pages/login.py", label="Secret Company Stuff", icon="🔒")
        #     #st.page_link("pages/signup.py", label="More Secret Stuff", icon="🕵️")


        #     #st.markdown("", unsafe_allow_html=True)

        #     # if st.button("Log out"):
        #     #     logout()
        
        # elif st.session_state.get("logged_in_admin", False):
        #     st.page_link("pages/admin.py", label = "")
        #     #st.page_link("pages/login.py", label="Secret Company Stuff", icon="🔒")
        #     #st.page_link("pages/signup.py", label="More Secret Stuff", icon="🕵️")

        #     #st.markdown("<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>", unsafe_allow_html=True)

        #     #if st.button("Log out"):
        #     #    logout()

        # elif st.session_state.get("signup", False):
        #     #st.page_link("pages/login.py", label="Secret Company Stuff", icon="🔒")
        #     st.page_link("pages/signup.py", label="")
            
        #     st.markdown("<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>", unsafe_allow_html=True)


        #     if st.button("Back"):
        #         logout()

        # elif get_current_page_name() != "app":
        #     # If anyone tries to access a secret page without being logged in,
        #     # redirect them to the login page
        #     st.switch_page("app.py")

def clearCookies():
    if cookies.get("email") is not None:
        cookies.remove("email")
    if cookies.get("email") is not None:
        cookies.remove("email")
    if cookies.get("username") is not None:
        cookies.remove("username")
    if cookies.get("birthday") is not None:
        cookies.remove("birthday")
    if cookies.get("gender") is not None:
        cookies.remove("gender")
    if cookies.get("age") is not None:
        cookies.remove("age")
    if cookies.get("role") is not None:
        cookies.remove("role")
    if cookies.get("password") is not None:
        cookies.remove("password")
    if cookies.get("invoice_id") is not None:
        cookies.remove("invoice_id")
    if cookies.get("status") is not None:
        cookies.remove("status")
    if cookies.get("fullname") is not None:
        cookies.remove("fullname")
    if cookies.get("customer_id") is not None:
        cookies.remove("customer_id")

    RemoveEmptyElementContainer()

def logout():
    # st.session_state.logged_in_cust = False
    # st.session_state.logged_in_admin = False
    # st.session_state.signup = False
    #st.info("Logged out successfully!")
    sleep(0.5)

    #st.write(cookies.getAll())
    clearCookies()
    
    st.switch_page("app.py")

def about_page():
    # Page Title
    st.markdown("<h1 style='font-family:Arial; font-weight:bold;'>📘 About This Application 📘</h1>", unsafe_allow_html=True)
    
    # Course Information
    st.markdown("<h2 style='font-family:Arial; font-weight:bold;'> <br>📚 Course Information 📚</h2>", unsafe_allow_html=True)
    st.markdown("""
    <p style='font-family:Arial;'>
    <br>
    Course Code: TEB3133/TFB3133<br>
    Course Name: Data Visualization
    </p>
    """, unsafe_allow_html=True)
    
    # Team Members Section
    st.markdown("<h2 style='font-family:Arial; font-weight:bold;'> <br>👨‍💻 Team Members 👨‍💻</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-family:Arial;'>This application was developed by the following team members:</p>", unsafe_allow_html=True)

    # Team members' information in a list of dictionaries
    team_members = [
        {"Name": "Chua Hong Kheng", "Student ID": "20001081", "Course": "Bachelor of Computer Science (Hons)"},
        {"Name": "Jeffery Chia Ching Rong", "Student ID": "20001164", "Course": "Bachelor of Computer Science (Hons)"},
        {"Name": "Chang Yong Qi", "Student ID": "20001305", "Course": "Bachelor of Computer Science (Hons)"},
        {"Name": "Joshua Adampin Rugag", "Student ID": "20001110", "Course": "Bachelor of Computer Science (Hons)"}
    ]
    
    # Add a "No." column to simulate numbering
    for i, member in enumerate(team_members, 1):
        member["No."] = i
    
    # Convert list of dictionaries to DataFrame for tabular display
    df = pd.DataFrame(team_members)
    
    # Reorganize columns to ensure "No." is the first column
    df = df[["No.", "Name", "Student ID", "Course"]]

    # Display the team members' details as a table
    st.markdown("<div style='font-family:Arial;'>", unsafe_allow_html=True)
    st.table(df)
    st.markdown("</div>", unsafe_allow_html=True)

    # Lecturer Information
    st.markdown("<h2 style='font-family:Arial; font-weight:bold;'> <br>🎓 Lecturer 🎓</h2>", unsafe_allow_html=True)
    st.markdown("""
    <p style='font-family:Arial;'>
    Name: Ts. Faizal bin Ahmad Fadzil<br>
    Role: Lecturer
    </p>
    """, unsafe_allow_html=True)

    # Divider
    st.markdown("<hr style='border:1px solid #ddd'>", unsafe_allow_html=True)

    # Application Overview
    st.markdown("<h2 style='font-family:Arial; font-weight:bold;'> <br> 🛠️ Application Overview 🛠️</h2>", unsafe_allow_html=True)
    st.markdown("""
    <p style='font-family:Arial;'>
    This application is designed to assist customers in interacting with a coffee shop ordering system.<br>
    It provides features such as:
    </p>
    <ul style='font-family:Arial;'>
      <li>📋 Browsing the menu with detailed item information.</li>
      <li>🛒 Customizing orders to meet customer preferences.</li>
      <li>📊 Real-time order status and inventory tracking.</li>
    </ul>
    <p style='font-family:Arial;'>Built with Streamlit, the application offers a simple and user-friendly web interface.</p>
    """, unsafe_allow_html=True)

    # Application Goal
    st.markdown("<h2 style='font-family:Arial; font-weight:bold;'> <br> 🎯 Our Goal 🎯</h2>", unsafe_allow_html=True)
    st.markdown("""
    <p style='font-family:Arial;'>
    Our goal is to create an intuitive and interactive platform for customers to:
    </p>
    <ul style='font-family:Arial;'>
      <li>☕ Easily place coffee orders.</li>
      <li>📈 Seamlessly track inventory and sales data in real time.</li>
    </ul>
    """, unsafe_allow_html=True)
