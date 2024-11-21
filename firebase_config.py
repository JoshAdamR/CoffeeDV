import firebase_admin
from firebase_admin import credentials, firestore
import toml

# Initialize Firebase Admin SDK with the credentials from the .toml file
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase)
    firebase_admin.initialize_app(cred)
    
# Get Firestore client
store = firestore.client() 
