import streamlit as st
import pandas as pd
import os
from firebase_config import store  # Import Firestore client from config
from pathlib import Path
from navigation import logout, make_sidebar

make_sidebar()
st.sidebar.markdown("<br>", unsafe_allow_html=True)

# Helper Functions
def get_collections():
    """Fetch all collection names from Firestore."""
    collections = store.collections()
    return [collection.id for collection in collections]

def get_fields_and_types(collection_name):
    """Fetch fields and their types for the first document in a collection to infer field structure."""
    docs = store.collection(collection_name).limit(1).stream()
    for doc in docs:
        return {field: type(value).__name__ for field, value in doc.to_dict().items()}
    return {}

def fetch_data(collection_name):
    """Fetch all documents from a collection."""
    docs = store.collection(collection_name).stream()
    return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

def add_data(collection_name, document_id, data):
    """Add a new document to a collection with the selected document_id."""
    store.collection(collection_name).document(document_id).set(data)

def update_data(collection_name, document_id, updates):
    """Update an existing document."""
    store.collection(collection_name).document(document_id).update(updates)

def delete_data(collection_name, document_id):
    """Delete a document from a collection."""
    store.collection(collection_name).document(document_id).delete()

def delete_all_collections():
    collections = store.collections()
    for collection in collections:
        collection_name = collection.id
        print(f"Deleting collection: {collection_name}")
        
        # Fetch all documents in the collection
        docs = collection.stream()
        for doc in docs:
            print(f"Deleting document: {doc.id} from collection {collection_name}")
            # Delete each document
            store.collection(collection_name).document(doc.id).delete()
            
def generatedb(folder_path):
    delete_all_collections()
    # Loop through all CSV files in the folder
    for filename in os.listdir(folder_path):
        if filename.endswith('.csv'):
            # Read the CSV file into a DataFrame
            csv_path = os.path.join(folder_path, filename)
            df = pd.read_csv(csv_path)

            # Create a new collection name based on the filename (without extension)
            collection_name = os.path.splitext(filename)[0]

            # Loop through each row in the DataFrame and add it to the Firestore collection
            for index, row in df.iterrows():
                # Use the value from the first column as the document ID
                document_id = str(row.iloc[0])  # First column value is used as document ID

                # Convert the row to a dictionary and add it to Firestore
                store.collection(collection_name).document(document_id).set(row.to_dict())

def admin():
    # Streamlit App
    st.title("Firestore Admin Panel")
    
    if st.sidebar.button("Create Database"):
        folder_path = st.sidebar.text_input("Enter the folder path for CSV files", "")
        if folder_path and os.path.exists(folder_path):
            generatedb(folder_path)
            st.success(f"Database created from the CSV files in `{folder_path}`!")
        else:
            st.sidebar.error("Please provide a valid folder path containing CSV files.")
        
    # Fetch all collections dynamically
    collections = get_collections()
    selected_collection = st.sidebar.selectbox("Select a collection", collections)
        
    if selected_collection:
        st.subheader(f"Manage `{selected_collection}` Collection")

        # Fetch and display data from the selected collection, but only once
        if 'data' not in st.session_state or st.session_state.selected_collection != selected_collection:
            data = fetch_data(selected_collection)
            st.session_state.data = data
            st.session_state.selected_collection = selected_collection
        else:
            data = st.session_state.data

        if data:
            df = pd.DataFrame(data)
            st.dataframe(df)
        else:
            st.write("No data available in this collection.")

        # Fetch fields and field types dynamically
        fields_and_types = get_fields_and_types(selected_collection)

        # Add Data Operation
        operation = st.sidebar.radio("Select operation", ["Add", "Update", "Delete"])

        if operation == "Add":
            st.subheader(f"Add a new document to {selected_collection}")
            
            # Ensure the document ID field is preserved in session state
            document_id_field = st.selectbox("Select a field to use as document ID", list(fields_and_types.keys()), key="document_id_field")
            document_id_value = st.text_input(f"Enter value for {document_id_field}", "", key="document_id_value")

            # Create a form for other fields
            new_data = {}
            for field, field_type in fields_and_types.items():
                if field != document_id_field:  # Skip the selected document ID field
                    if field_type == 'str':
                        new_data[field] = st.text_input(f"Enter value for {field} (string)", key=f"str_{field}")
                    elif field_type == 'int':
                        new_data[field] = st.number_input(f"Enter value for {field} (integer)", step=1, key=f"int_{field}")
                    elif field_type == 'float':
                        new_data[field] = st.number_input(f"Enter value for {field} (float)", key=f"float_{field}")
                    elif field_type == 'bool':
                        new_data[field] = st.checkbox(f"Enter value for {field} (boolean)", key=f"bool_{field}")
                    elif field_type == 'datetime':
                        new_data[field] = st.date_input(f"Enter value for {field} (date)", key=f"datetime_{field}")
                    else:
                        new_data[field] = st.text_input(f"Enter value for {field} (other type)", key=f"other_{field}")

            if st.button("Add Document"):
                if document_id_value:
                    # Add new document with the selected document ID field value
                    new_data[document_id_field] = document_id_value
                    add_data(selected_collection, document_id_value, new_data)
                    st.success(f"Document with ID {document_id_value} added successfully!")
                    st.session_state.data = fetch_data(selected_collection)  # Refresh the data
                    st.session_state.selected_collection = selected_collection  # Retain the collection selection
                    st.rerun()
                else:
                    st.error("Please provide a value for the selected document ID field.")

        elif operation == "Update":
            st.subheader(f"Update a document in `{selected_collection}`")
            doc_id = st.text_input("Enter Document ID to update")
            
            if doc_id:  # Only proceed if document ID is provided
                # Fetch the document by its ID
                doc_ref = store.collection(selected_collection).document(doc_id)
                doc = doc_ref.get()
                
                if doc.exists:
                    doc_data = doc.to_dict()  # Get the document data as a dictionary
                    updates = {}  # Dictionary to store the updates
                    
                    # Loop through each field and its type, pre-filling the form with existing data
                    for field, field_type in fields_and_types.items():
                        if field in doc_data:  # Check if the field exists in the document
                            if field_type == 'str':
                                updates[field] = st.text_input(f"Update `{field}` (string)", doc_data.get(field, ""))
                            elif field_type == 'int':
                                updates[field] = st.number_input(f"Update `{field}` (integer)", value=doc_data.get(field, 0))
                            elif field_type == 'float':
                                updates[field] = st.number_input(f"Update `{field}` (float)", value=doc_data.get(field, 0.0))
                            elif field_type == 'bool':
                                updates[field] = st.checkbox(f"Update `{field}` (boolean)", value=doc_data.get(field, False))
                            elif field_type == 'datetime':
                                updates[field] = st.date_input(f"Update `{field}` (date)", value=doc_data.get(field))
                            else:
                                updates[field] = st.text_input(f"Update `{field}` (other type)", doc_data.get(field, ""))
                    
                    # Update the document when the button is pressed
                    if st.button("Update Document"):
                        update_data(selected_collection, doc_id, updates)
                        st.success("Document updated successfully!")
                        st.session_state.data = fetch_data(selected_collection)  # Refresh the data
                        st.rerun()  # Rerun the app to reflect the changes
                else:
                    st.error("Document not found!")


        elif operation == "Delete":
            st.subheader(f"Delete a document from `{selected_collection}`")
            doc_id = st.text_input("Enter Document ID to delete")
            if st.button("Delete Document"):
                delete_data(selected_collection, doc_id)
                st.success("Document deleted successfully!")
                st.session_state.data = fetch_data(selected_collection)  # Refresh the data
                st.rerun()

        # Refresh Button
        if st.button("Refresh Data"):
            st.session_state.data = fetch_data(selected_collection)
            st.rerun()

# Call the admin function to run the Streamlit app
admin()

st.sidebar.markdown("<br><br><br>", unsafe_allow_html=True)
if st.sidebar.button("Log out"):
    logout()
