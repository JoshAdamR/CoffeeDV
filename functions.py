import streamlit as st
import pandas as pd
import re
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from streamlit_cookies_controller import CookieController, RemoveEmptyElementContainer

cookies = CookieController()
cartItems = CookieController()

# Initialize Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_credentials.json")
    firebase_admin.initialize_app(cred)

# Create Firestore client
store = firestore.client()

def generate_id(prefix, collection_name, id_field):
    """
    Generate a new ID for a specified collection and ID field with a given prefix.

    Args:
        prefix (str): The prefix for the ID (e.g., "USER" or "CUST").
        collection_name (str): The Firestore collection name.
        id_field (str): The name of the field to look for IDs.

    Returns:
        str: The newly generated ID with the specified prefix.
    """
    collection_ref = store.collection(collection_name)
    documents = collection_ref.order_by(id_field).stream()
    max_id = 0
    for doc in documents:
        current_id = doc.to_dict().get(id_field, "")
        if current_id.startswith(prefix):
            num = int(current_id[len(prefix):])
            max_id = max(max_id, num)
    new_id = max_id + 1
    return f"{prefix}{new_id:03}"

# Example usage
# def generate_user_id():
#     return generate_id("USER", "useracc", "user_id")

def generate_customer_id():
    return generate_id("CUST", "useracc", "customer_id")    

def calculate_age(birthday):
    today = datetime.today()
    birth_date = datetime.strptime(birthday, "%Y-%m-%d")
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def add_entry(fullname, username, email, password, birthday, gender, datejoin, loyalty_point):
    # user_id = generate_user_id()
    customer_id = generate_customer_id()
    age = calculate_age(birthday)
    user_entry = {
        # "user_id": user_id,
        "username": username,
        "email": email,
        "password": password,  # Consider hashing the password before storing
        "role": "customer",
        "customer_id": customer_id
    }
    cust_entry = {
        # "user_id": user_id,
        "birthday": birthday,
        "gender": gender,
        "age": age,
        "customer_id": customer_id,
        "customer_name": fullname,
        "join_date": datejoin,
        "loyalty_point": loyalty_point
    }
    store.collection("useracc").document(email).set(user_entry)
    store.collection("customer").document(email).set(cust_entry)

# Function to fetch all entries from Firestore
def get_entries(table):
    users_ref = store.collection(table)
    docs = users_ref.stream()
    return [doc.to_dict() for doc in docs]

# Function to check if email is valid
def is_valid_email(email):
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(regex, email) is not None and email.endswith('.com')

# Function to check if password is valid
def is_valid_password(password):
    return (len(password) >= 8 and
            any(char.isupper() for char in password) and
            any(char.isdigit() for char in password) and
            any(not char.isalnum() for char in password))

# Function to check for duplicate emails in Firestore
def email_exists(email):
    user_ref = store.collection("useracc").document(email)
    return user_ref.get().exists

# Function to fetch user by email and password from Firestore
def fetch_user(email, password):
    users_ref = store.collection("useracc")
    query = users_ref.where("email", "==", email).where("password", "==", password).limit(1)
    user = query.get()
    return user[0].to_dict() if user else None

def fetch_user_by_id(table, email):
    user_ref = store.collection(table).document(email)
    user = user_ref.get()
    if user.exists:
        return user.to_dict()
    else:
        return None

def storeCookies(username,email,password,birthday,gender,age):
    cookies.set("email", email)
    cookies.set("password", password)
    cookies.set("username", username)
    cookies.set("birthday", birthday)
    cookies.set("gender", gender)
    cookies.set("age", age)
    cookies.set("role", "customer")

    RemoveEmptyElementContainer()

def getCookies(email_input):
    """
    Fetch cookies for the user with the provided email. If logged in successfully, store user data in cookies.

    Args:
        email_input (str): The email entered in the email input box.

    Returns:
        dict or None: The user data if found, or None if not found.
    """
    # Fetch user by email from Firestore
    user_data = fetch_user_by_id("useracc",email_input)
    cust_data = fetch_user_by_id("customer",email_input)

    if user_data:
        # Store user data in cookies
        cookies.set("status", 'true')
        cookies.set("email", user_data.get("email"))
        cookies.set("username", user_data.get("username"))
        cookies.set("birthday", cust_data.get("birthday"))
        cookies.set("gender", cust_data.get("gender"))
        cookies.set("age", cust_data.get("age"))
        cookies.set("role", user_data.get("role"))
        cookies.set("password", user_data.get("password"))
        
        return user_data
    else:
        return None
