import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import matplotlib.pyplot as plt
import seaborn as sns

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.Certificate('firebase_credentials.json')
    firebase_admin.initialize_app(cred)

# Create Firestore client
store = firestore.client()

# Functions to interact with Firestore
def get_branches():
    branches_ref = store.collection('branch')
    return pd.DataFrame([doc.to_dict() for doc in branches_ref.stream()])

def get_inventory():
    inventory_ref = store.collection('inventory')
    return pd.DataFrame([doc.to_dict() for doc in inventory_ref.stream()])

def get_inventory_quantity():
    inv_quantity_branch_ref = store.collection('inv_quantity_branch')
    return pd.DataFrame([doc.to_dict() for doc in inv_quantity_branch_ref.stream()])

def get_offers():
    offers_ref = store.collection('coupon')
    return pd.DataFrame([doc.to_dict() for doc in offers_ref.stream()])

def get_usage_history():
    usage_history_ref = store.collection('usage_history')
    return pd.DataFrame([doc.to_dict() for doc in usage_history_ref.stream()])

def get_restock_history():
    restock_history_ref = store.collection('restock_history')
    return pd.DataFrame([doc.to_dict() for doc in restock_history_ref.stream()])

def update_stock(item_name, quantity, action, branch_id):
    """Update stock based on sales or restock for the selected branch."""
    
    # Step 1: Get the inventory_id from the inventory collection based on the item_name
    inventory_ref = store.collection('inventory').where('inventory_name', '==', item_name)
    docs = inventory_ref.stream()
    
    # Step 2: Get the inventory_id from the found document (assumes one match)
    for doc in docs:
        inventory_id = doc.id  # This is the inventory_id

    # Step 3: Get the corresponding quantity_on_hand from inv_quantity_branch collection using inventory_id and branch_id
    inv_quantity_ref = store.collection('inv_quantity_branch').where('inventory_id', '==', inventory_id).where('branch_id', '==', branch_id)
    quantity_docs = inv_quantity_ref.stream()

    # Step 4: Update the quantity_on_hand for the specific inventory_id in inv_quantity_branch collection
    for quantity_doc in quantity_docs:
        current_quantity = quantity_doc.to_dict()['quantity_on_hand']
        
        # Check the action (remove or restock)
        if action == "remove":
            new_quantity = current_quantity - quantity
            # Add to usage_history collection
            store.collection('usage_history').add({
                'inventory_id': inventory_id,
                'quantity': quantity,
                'branch_id': branch_id
            })
        elif action == "restock":
            new_quantity = current_quantity + quantity
            # Add to restock_history collection
            store.collection('restock_history').add({
                'inventory_id': inventory_id,
                'quantity': quantity,
                'branch_id': branch_id
            })
        else:
            st.error("Invalid action. Use 'remove' or 'restock'.")
            return
        
        # Step 5: Update the stock in the inv_quantity_branch collection
        store.collection('inv_quantity_branch').document(quantity_doc.id).update({'quantity_on_hand': new_quantity})

        # Notify the user that the stock has been updated
        st.success(f"Stock updated! New quantity: {new_quantity}")

# Load data from Firestore
def readdb():
    branches = get_branches()
    inventory_data = get_inventory()
    inventory_quantity = get_inventory_quantity()
    inventory = pd.merge(inventory_data, inventory_quantity, on='inventory_id', how='inner')
    offers = get_offers()
    usage_history = get_usage_history()
    restock_history = get_restock_history()
    
    return branches, inventory, offers, usage_history, restock_history

branches, inventory, offers, usage_history, restock_history = readdb()

# Streamlit App Layout
st.title("Inventory Management System")
st.sidebar.header("Select a Section")

# Dropdown for selecting between Inventory Management and Coupon Management
section = st.sidebar.selectbox("Select a Section", ["Inventory Management", "Coupon Management"])

# Inventory Management Section
if section == "Inventory Management":
    st.header("Inventory Management")

    # Multi-Branch Support
    selected_branch_id = st.selectbox("Select Branch", branches['branch_name'].tolist())
    selected_branch = branches[branches['branch_name'] == selected_branch_id]
    selected_branch_id_value = selected_branch['branch_id'].values[0]

    # Display branch details
    st.subheader(f"Branch Details: {selected_branch['branch_name'].values[0]}")
    st.write(f"Location: {selected_branch['location'].values[0]}")
    st.write(f"Operating Cost: ${selected_branch['operating_cost'].values[0]}")

    # Display inventory for the selected branch
    st.subheader(f"Inventory for {selected_branch_id}")
    branch_inventory = inventory[inventory['branch_id'] == selected_branch_id_value]
    inventory_display = st.dataframe(branch_inventory.drop(columns=['inventory_id', 'inv_branch_id', 'branch_id']))  # Store initial display

    # Update stock based on sales or restock
    action = st.radio("Select Action", ["Remove Items", "Restock Items"])
    selected_items = st.multiselect("Select Items", branch_inventory['inventory_name'].tolist())
    quantity = st.number_input("Quantity", min_value=1, value=1, step=1)

    if st.button("Update Stock"):
        for item in selected_items:
            if action == "Remove Items":
                update_stock(item, quantity, "remove", selected_branch_id_value)  # Reduce quantity by specified amount for the selected branch
            elif action == "Restock Items":
                update_stock(item, quantity, "restock", selected_branch_id_value)  # Increase quantity by specified amount for the selected branch
        st.success(f"{action} updated!")

        st.rerun()

    # Notifications for low stock (specific to the selected branch)
    low_stock_items = branch_inventory[branch_inventory['quantity_on_hand'] < branch_inventory['minimum_stock_level']]
    if not low_stock_items.empty:
        st.warning("Low stock for the following items:")
        st.write(low_stock_items)

    # Visualization Section
    st.subheader("Inventory Data, Restock History, and Usage History")

    # Filter usage and restock history by branch ID
    branch_usage_history = usage_history[usage_history['branch_id'] == selected_branch_id_value]
    branch_restock_history = restock_history[restock_history['branch_id'] == selected_branch_id_value]

    # Create plots for inventory, restock, and usage history
    fig, axs = plt.subplots(3, 1, figsize=(10, 15))

    # Inventory plot (Quantity on hand per item) - Horizontal Bar Chart
    sns.barplot(x='quantity_on_hand', y='inventory_name', data=branch_inventory, ax=axs[0])
    axs[0].set_title('Inventory Data - Quantity on Hand')
    axs[0].set_xlabel('Quantity')

    # Add text annotations on bars for inventory data
    for p in axs[0].patches:
        axs[0].text(p.get_width() + 0.1, p.get_y() + p.get_height() / 2, f'{int(p.get_width())}', 
                    ha='left', va='center')

    # Restock history plot - Horizontal Bar Chart
    if not branch_restock_history.empty:
        restock_history_agg = branch_restock_history.groupby('inventory_id')['quantity'].sum().reset_index()
        restock_history_agg = restock_history_agg.merge(inventory[['inventory_id', 'inventory_name']], on='inventory_id')
        sns.barplot(x='quantity', y='inventory_name', data=restock_history_agg, ax=axs[1])
        axs[1].set_title('Restock History')
        axs[1].set_xlabel('Restocked Quantity')

        # Add text annotations on bars for restock history
        for p in axs[1].patches:
            axs[1].text(p.get_width() + 0.1, p.get_y() + p.get_height() / 2, f'{int(p.get_width())}', 
                        ha='left', va='center')
    else:
        axs[1].text(0.5, 0.5, 'No Restock History', ha='center', va='center')

    # Usage history plot - Horizontal Bar Chart
    if not branch_usage_history.empty:
        usage_history_agg = branch_usage_history.groupby('inventory_id')['quantity'].sum().reset_index()
        usage_history_agg = usage_history_agg.merge(inventory[['inventory_id', 'inventory_name']], on='inventory_id')
        sns.barplot(x='quantity', y='inventory_name', data=usage_history_agg, ax=axs[2])
        axs[2].set_title('Usage History')
        axs[2].set_xlabel('Used Quantity')

        # Add text annotations on bars for usage history
        for p in axs[2].patches:
            axs[2].text(p.get_width() + 0.1, p.get_y() + p.get_height() / 2, f'{int(p.get_width())}', 
                        ha='left', va='center')
    else:
        axs[2].text(0.5, 0.5, 'No Usage History', ha='center', va='center')

    plt.tight_layout()
    st.pyplot(fig)

# Coupon Management Section
elif section == "Coupon Management":
    from datetime import datetime

    # Function to get all offers from the Firestore coupon collection
    def get_offers():
        offers_ref = store.collection('coupon')
        return pd.DataFrame([doc.to_dict() for doc in offers_ref.stream()])

    # Function to check if a coupon with the same code already exists
    def coupon_exists(offer_code):
        offer_ref = store.collection('coupon').where('coupon_code', '==', offer_code)
        docs = offer_ref.stream()
        return len(list(docs)) > 0  # Return True if coupon exists

    # Function to add a new offer to the Firestore coupon collection
    def add_offer(offer_code, promotion_type, discount, start_date, expiry_date):
        if coupon_exists(offer_code):  # Check if coupon already exists
            st.error(f"Coupon with code '{offer_code}' already exists. Please choose a different code.")
            return False
        
        # Convert start_date and expiry_date to datetime
        start_date = datetime.combine(start_date, datetime.min.time())
        expiry_date = datetime.combine(expiry_date, datetime.min.time())
        
        # Prepare the data to be added
        offer_data = {
            'coupon_code': offer_code,
            'promotion_type': promotion_type,
            'discount_percentage': discount if promotion_type == 'Percentage' else 0,
            'rm_discount': discount if promotion_type == 'Flat Rate' else 0,
            'start_date': start_date,
            'expiry_date': expiry_date
        }
        
        # Add the offer data to the 'coupon' collection in Firestore
        store.collection('coupon').add(offer_data)
        
        st.success(f"Offer with Coupon Code '{offer_code}' added successfully!")  # Success message
        return True  # Return True indicating the offer was added

    # Function to remove an offer from the Firestore coupon collection
    def remove_offer(offer_code):
        # Query to find the offer by coupon_code
        offer_ref = store.collection('coupon').where('coupon_code', '==', offer_code)
        docs = offer_ref.stream()
        
        # If offer is found, remove it
        for doc in docs:
            store.collection('coupon').document(doc.id).delete()
        
        st.success(f"Offer with coupon code '{offer_code}' has been removed.")

    # Streamlit App Layout
    st.title("Coupon Management")

    # Fetch current offers to display and store in session state
    if 'offers' not in st.session_state:
        st.session_state.offers = get_offers()  # Load offers only once when the app is first loaded

    # Display current special offers - dynamically updated
    st.subheader("Current Special Offers")
    st.write(st.session_state.offers)  # Display the offers stored in session state

    # Admin options to add special offers
    with st.form(key='offer_form'):
        offer_code = st.text_input("Coupon Code")
        promotion_type = st.selectbox("Promotion Type", ['Percentage', 'Flat Rate'])
        discount = st.number_input("Discount Amount", min_value=0, max_value=100)
        start_date = st.date_input("Start Date", pd.to_datetime('today'))
        expiry_date = st.date_input("Expiry Date", pd.to_datetime('today'))
        
        if st.form_submit_button("Add Offer"):
            # Add offer only if it's not a duplicate
            if add_offer(offer_code, promotion_type, discount, start_date, expiry_date):
                # Update the session state with the new list of offers after adding
                st.session_state.offers = get_offers()  # Refresh the offers data
                # Update the displayed table with the new data
                st.rerun()  # This will refresh the entire app and update the table immediately

    # Remove Offer Section
    st.subheader("Remove Offer")
    remove_offer_code = st.text_input("Enter Coupon Code to Remove")
    if st.button("Remove Offer"):
        remove_offer(remove_offer_code)
        # Update the session state with the new list of offers after removal
        st.session_state.offers = get_offers()  # Refresh the offers data
        # Update the displayed table with the new data
        st.rerun()  # This will refresh the entire app and update the table immediately
