import streamlit as st
from streamlit_javascript import st_javascript

def set_item(variable_name, value):
    """
    Set an item in browser localStorage.
    
    :param variable_name: The key/name of the variable to store.
    :param value: The value to store.
    """
    st_javascript(f"""
    localStorage.setItem("{variable_name}", JSON.stringify("{value}"));
    console.log("Saved to localStorage: {variable_name} = {value}");
    """)

def get_item(variable_name):
    """
    Get an item from browser localStorage.
    
    :param variable_name: The key/name of the variable to retrieve.
    :return: The value retrieved from localStorage.
    """
    result = st_javascript(f"""
    JSON.parse(localStorage.getItem("{variable_name}"));
    """)
    return result

st.title("Browser Local Storage Example")

# Save a value to localStorage
if st.button("Save to Local Storage"):
    set_item("username", "StreamlitUser")
    st.success("Value saved to localStorage!")

# Retrieve a value from localStorage
if st.button("Get from Local Storage"):
    username = get_item("username")
    if username:
        st.write(f"Retrieved value: {username}")
    else:
        st.warning("No value found in localStorage!")

