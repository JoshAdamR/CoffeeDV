import streamlit as st
from firebase_config import store  # Import Firestore client from config

def run():
    st.title("Branch Login")

    # Fetch branch data
    branches_ref = store.collection('branch')
    branches = {doc.to_dict()['branch_name']: doc.id for doc in branches_ref.stream()}

    branch_name = st.selectbox("Select Branch", list(branches.keys()))
    branch_password = st.text_input("Password", type="password")

    if st.button("Login"):
        branch_doc = store.collection('branch').document(branches[branch_name]).get()
        branch_data = branch_doc.to_dict()
        if branch_data.get('password') == branch_password:
            st.session_state.logged_in_branch = branch_name
            st.success(f"Successfully logged in as {branch_name}")
            st.rerun()
        else:
            st.error("Invalid password")
