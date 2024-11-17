import streamlit as st
import pandas as pd
import re
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate("coffeeshop-54872-firebase-adminsdk-if85u-f0eabc8124.json")
    firebase_admin.initialize_app(cred)

# Create Firestore client
store = firestore.client()

# Function to add a new entry to Firestore
def add_entry(username, email, password):
    user_ref = store.collection("users").document(email)
    user_ref.set({
        "username": username,
        "email": email,
        "password": password,
        "role": "customer"
    })

# Function to fetch all entries from Firestore
def get_entries():
    users_ref = store.collection("users")
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
    user_ref = store.collection("users").document(email)
    return user_ref.get().exists

# Function to fetch user by email and password from Firestore
def fetch_user(email, password):
    users_ref = store.collection("users")
    query = users_ref.where("email", "==", email).where("password", "==", password).limit(1)
    user = query.get()
    return user[0].to_dict() if user else None