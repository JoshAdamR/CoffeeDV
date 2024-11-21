import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st

# Retrieve Firebase credentials from Streamlit secrets
firebase_secret = st.secrets['firebase']

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_secret['secrets'])
    firebase_admin.initialize_app(cred)

# Get Firestore client
store = firestore.client()
