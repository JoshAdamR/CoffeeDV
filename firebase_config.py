import firebase_admin
from firebase_admin import credentials, firestore
import toml

# Initialize Firebase Admin SDK with the credentials from the .toml file
if not firebase_admin._apps:
    cred = credentials.Certificate({
        "type": firebase_secret['type'],
        "project_id": firebase_secret['project_id'],
        "private_key_id": firebase_secret['private_key_id'],
        "private_key": firebase_secret['private_key'],
        "client_email": firebase_secret['client_email'],
        "client_id": firebase_secret['client_id'],
        "auth_uri": firebase_secret['auth_uri'],
        "token_uri": firebase_secret['token_uri'],
        "auth_provider_x509_cert_url": firebase_secret['auth_provider_x509_cert_url'],
        "client_x509_cert_url": firebase_secret['client_x509_cert_url'],
        "universe_domain": firebase_secret['universe_domain']
    })
    firebase_admin.initialize_app(cred)
    
# Get Firestore client
store = firestore.client() 
