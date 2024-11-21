import streamlit as st
import pandas as pd
from firebase_config import store  # Import Firestore client from config
import matplotlib.pyplot as plt
import seaborn as sns

def run():
    st.title("Inventory Management")

    if not st.session_state.logged_in_branch:
        st.warning("You need to log in first!")
        st.stop()

    def get_ref(table):
        ref = store.collection(table)
        return pd.DataFrame([doc.to_dict() for doc in ref.stream()])

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

    # Data loading function
    def readdb():
        branches = get_ref('branch')
        inventory_data = get_ref('inventory')
        inventory_quantity = get_ref('inv_quantity_branch')
        inventory = pd.merge(inventory_data, inventory_quantity, on='inventory_id', how='inner')
        usage_history = get_ref('usage_history')
        restock_history = get_ref('restock_history')
        return branches, inventory, usage_history, restock_history

    branches, inventory, usage_history, restock_history = readdb()
    
    
    branch_name = st.session_state.logged_in_branch
    st.subheader(f"Welcome, {branch_name}!")

    # Multi-Branch Support
    selected_branch_id = branch_name
    selected_branch = branches[branches['branch_name'] == selected_branch_id]
    selected_branch_id_value = selected_branch['branch_id'].values[0]

    # Display branch details
    st.subheader(f"Branch Details: {selected_branch['branch_name'].values[0]}")
    st.write(f"Location: {selected_branch['location'].values[0]}")
    st.write(f"Operating Cost: ${selected_branch['operating_cost'].values[0]}")

    # Display inventory for the selected branch
    st.subheader(f"Inventory for {selected_branch_id}")
    branch_inventory = inventory[inventory['branch_id'] == selected_branch_id_value]

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