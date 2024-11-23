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
