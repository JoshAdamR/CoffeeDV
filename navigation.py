import streamlit as st
from time import sleep
from streamlit.runtime.scriptrunner import get_script_run_ctx
from streamlit.source_util import get_pages
from functions import add_entry, get_entries, is_valid_email, is_valid_password, email_exists, fetch_user, cookies, getCookies


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
    cookies.remove("status")
    cookies.remove("email")
    cookies.remove("username")
    cookies.remove("birthday")
    cookies.remove("gender")
    cookies.remove("age")
    cookies.remove("role")
    cookies.remove("password")
    cookies.remove("invoice_id")

def logout():
    # st.session_state.logged_in_cust = False
    # st.session_state.logged_in_admin = False
    # st.session_state.signup = False
    #st.info("Logged out successfully!")
    sleep(0.5)

    st.write(cookies.getAll())

    if cookies.get("status") == "true":
        clearCookies()
    
    st.switch_page("app.py")
    st.success("Successfully Logout!")
