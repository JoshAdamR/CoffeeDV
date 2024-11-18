import firebase_admin
import google.cloud
from firebase_admin import credentials, firestore
import pandas as pd
import os

# IMPORTANT!!
cred = credentials.Certificate(r"C:\Users\user\Downloads\coffee-shop-b4277-firebase-adminsdk-hqmbz-b9792ddd08.json")
app = firebase_admin.initialize_app(cred)

store = firestore.client()
# IMPORTANT!!

folder_path = r"C:\Users\user\Downloads\Collections"
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
            # Find the column that ends with '_id' (e.g., 'customer_id')
            document_id_column = [col for col in df.columns if col.endswith('_id')]

            if document_id_column:
                document_id = str(row[document_id_column[0]])  # Use the value from the '_id' column
            else:
                document_id = str(index)  # Fallback to using the index if '_id' is not found

            # Convert the row to a dictionary and add it to Firestore
            store.collection(collection_name).document(document_id).set(row.to_dict())

        print(f"Created collection '{collection_name}' with {len(df)} documents.")

print("All collections created successfully!")
