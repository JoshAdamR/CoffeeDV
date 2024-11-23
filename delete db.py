from firebase_config import store  # Import Firestore client from config

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

    print("All collections deleted successfully!")

# Call the function
delete_all_collections()