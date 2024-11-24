import streamlit as st
# from inventory_page import inventory
# from coupon_page import coupon
from navigation import make_sidebar, logout
from functions import cookies
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from graph_function import gf
from firebase_config import store 


make_sidebar()

#st.write(cookies.getAll())
branch_id = cookies.get("customer_id")

def get_ref(table):
        ref = store.collection(table)
        return pd.DataFrame([doc.to_dict() for doc in ref.stream()])

def notification_low(branch_inventory):
    low_stock_items = branch_inventory[branch_inventory['quantity_on_hand'] < branch_inventory['minimum_stock_level']]
    if not low_stock_items.empty:
        st.warning("Low stock for the following items:")
        # Combine quantity_on_hand and metric into a single column
        low_stock_items['Quantity'] = low_stock_items['quantity_on_hand'].astype(str) + " " + low_stock_items['metric']
        low_stock_items['Inventory ID'] = low_stock_items['inventory_id']
        low_stock_items['Item'] = low_stock_items['inventory_name']
        low_stock_items['Minimum'] = low_stock_items['minimum_stock_level'].astype(str) + " " + low_stock_items['metric']
        # Select only the required columns
        columns_to_display = ['Inventory ID', 'Item', 'Quantity', 'Minimum']
        low_stock_items_display = low_stock_items[columns_to_display]
        low_stock_items_display.index = pd.RangeIndex(start=1, stop=len(low_stock_items_display) + 1, step=1)
        # Write the modified DataFrame to the app
        st.dataframe(low_stock_items_display, use_container_width = True)

def inventory(branch_id):
    st.title("Inventory Management")

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
    
    # Multi-Branch Support
    selected_branch = branches[branches['branch_id'] == branch_id]
    branch_name = selected_branch['branch_name'].values[0]
    branch_inventory = inventory[inventory['branch_id'] == branch_id]
    notification_low(branch_inventory)

    st.subheader(f"Welcome, {branch_name}!")

    # Display branch details
    st.subheader(f"Branch Details: {branch_name}")
    st.write(f"Location: {selected_branch['location'].values[0]}")
    st.write(f"Operating Cost: ${selected_branch['operating_cost'].values[0]}")

    # Display inventory for the selected branch
    st.subheader(f"Inventory for {branch_name}")

    branch_inventory['Inventory ID'] = branch_inventory['inventory_id']
    branch_inventory['Item'] = branch_inventory['inventory_name']
    branch_inventory['Quantity'] = branch_inventory['quantity_on_hand'].astype(str) + " " + branch_inventory['metric']
    branch_inventory['Minimum'] = branch_inventory['minimum_stock_level']
    branch_inventory['Unit Price'] = branch_inventory['unit_price']
    columns_to_display = ['Inventory ID', 'Item', 'Quantity', 'Minimum', 'Unit Price']
    branch_inventory_display = branch_inventory[columns_to_display]
    branch_inventory_display.index = pd.RangeIndex(start=1, stop=len(branch_inventory_display) + 1, step=1)
    # Write the modified DataFrame to the app
    st.dataframe(branch_inventory_display, use_container_width = True)

    # Update stock based on sales or restock
    action = st.radio("Select Action", ["Remove Items", "Restock Items"])
    selected_items = st.multiselect("Select Items", branch_inventory['inventory_name'].tolist())
    quantity = st.number_input("Quantity", min_value=1, value=1, step=1)

    if st.button("Update Stock"):
        for item in selected_items:
            if action == "Remove Items":
                update_stock(item, quantity, "remove", branch_id)  # Reduce quantity by specified amount for the selected branch
            elif action == "Restock Items":
                update_stock(item, quantity, "restock", branch_id)  # Increase quantity by specified amount for the selected branch
        st.success(f"{action} updated!")

        st.rerun()

    # Visualization Section

def coupon():
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
    offer_df = pd.DataFrame()
    offer_df['Type'] = st.session_state.offers['promotion_type']
    offer_df['Code'] = st.session_state.offers['coupon_code']
    offer_df['Start Date'] = st.session_state.offers['start_date']
    offer_df['Discount'] = st.session_state.offers.apply(
        lambda row: f"{row['discount_percentage']} %" if row['promotion_type'] == 'Percentage' else f"RM {row['rm_discount']}",
        axis=1
    )
    offer_df['Expiry Date'] = st.session_state.offers['expiry_date']
    columns_to_display = ['Type', 'Code', 'Start Date', 'Discount', 'Expiry Date']
    offer_df_display = offer_df[columns_to_display]
    offer_df_display.index = pd.RangeIndex(start=1, stop=len(offer_df_display) + 1, step=1)
    st.dataframe(offer_df_display, use_container_width = True)  # Display the offers stored in session state

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

    # Visualization Section

def branch_order(branch_id):
    def get_ref(table):
        ref = store.collection(table)
        return ref, pd.DataFrame([doc.to_dict() for doc in ref.stream()])
        
    size_ref, size_table = get_ref('size')
    inv_usage_ref, inv_usage = get_ref('inv_usage')
    inventory_data_ref, inventory_data = get_ref('inventory')
    inv_quantity_branch_ref, inv_quantity = get_ref('inv_quantity_branch')
    inv_quantity_branch = inv_quantity[inv_quantity['branch_id'] == branch_id]
    inventory_comb = pd.merge(inventory_data, inv_quantity_branch, on='inventory_id', how='inner')
    branch_inventory = inventory_comb[inventory_comb['branch_id'] == branch_id]
        
    #['name', 'size', 'category', 'sugar_level', 'addons', 'milk_type', 'quantity', 'temperature']
    def update_inventory(order_list):
        # Deduct usage for each item in the order list
        for order in order_list:
            # Deduct quantity for the product 
            def inventory_to_update(name):
                usage_quantity_list = inv_usage[inv_usage['item_name'] == name]['usage']
                for usage_quantity in usage_quantity_list:
                    inventory_id = inv_usage[inv_usage['item_name'] == name]['inventory_id'].values[0]
                    update_inventory_quantity(inv_quantity_branch_ref, inventory_id, inv_quantity_branch, usage_quantity, size)
                
            product_name = order.get('name')
            size = order.get('size')  
            if product_name:
                inventory_to_update(product_name)

            # Deduct quantity for add-ons
            addons = order.get('addons', []) 
            for addon_name in addons:
                inventory_to_update(addon_name)

            # Deduct quantity for milk option
            milk_name = order.get('milk_type') 
            if milk_name:
                inventory_to_update(milk_name)

            # Deduct quantity for temperature
            temp_name = order.get('temperature') 
            if temp_name:
                inventory_to_update(temp_name)

            # Deduct quantity for sugar level
            sugar_name = order.get('sugar_level')
            if sugar_name:
                inventory_to_update(sugar_name)
        
    def update_inventory_quantity(inv_quantity_branch_ref, inventory_id, inv_quantity_branch, usage_quantity, size):
        # Filter for the specific inventory_id
        filtered_quantity = inv_quantity_branch[inv_quantity_branch['inventory_id'] == inventory_id]

        # Check if the filtered DataFrame is empty
        if filtered_quantity.empty:
            st.error(f"Inventory ID {inventory_id} not found in branch inventory.")   
            return  # Exit the function if no matching inventory is found

        # Get the old quantity
        old_quantity = filtered_quantity['quantity_on_hand'].values[0]

        # Get the size multiplier
        size_multiplier = size_table[size_table['size_name'] == size]['recipe_multiplier'].values
        if len(size_multiplier) == 0:
            st.error(f"Size '{size}' not found in size table.")
            return  # Exit if size is invalid
        size_multiplier = size_multiplier[0]

        # Calculate the new quantity
        used = usage_quantity * size_multiplier
        new_quantity = max(old_quantity - used, 0)

        # Update Firestore only if there's a change
        if new_quantity != old_quantity:
            inv_branch_id = filtered_quantity['inv_branch_id'].values[0]
            inv_quantity_branch_ref.document(inv_branch_id).update({'quantity_on_hand': new_quantity})
            
            if used != 0:
                store.collection('usage_history').add({
                    'inventory_id': inventory_id,
                    'quantity': used,
                    'branch_id': branch_id
                })

    cart_ref = store.collection('cart')

    # Function to load orders with status 'Preparing'
    def load_orders():
        query = cart_ref.where('status', '==', 'Preparing').where('branch_id', '==', branch_id)
        orders = query.stream()
        order_list = []
        for order in orders:
            order_data = order.to_dict()
            order_data['id'] = order.id
            order_list.append(order_data)
        return order_list

    # Function to complete orders by order_id
    def complete_order_by_id(selected_order_id, orders):
        # Filter the orders list for the selected order_id
        filtered_orders = [order for order in orders if order['order_id'] == selected_order_id]

        # Update the status of each matching order to 'Done'
        for order in filtered_orders:
            cart_ref.document(order['id']).update({'status': 'Done'})


    # Streamlit layout
    st.title("Branch Order Management")
    
    notification_low(branch_inventory)

    # Refresh button
    if st.button("Refresh"):
        st.rerun()  # Refresh the app

    # Load orders with status 'Preparing'
    orders = load_orders()

    if orders:
        # Convert to DataFrame
        order_df = pd.DataFrame(orders)

        # Calculate total pending orders
        total_pending_orders = order_df['order_id'].nunique()  # Unique order IDs
        st.subheader(f"Total Pending Orders: {total_pending_orders}")

        # Group orders by order_id and compute total_quantity, including ordered_time_date
        grouped_df = (
            order_df.groupby(['order_id', 'email', 'status', 'ordered_time_date'], as_index=False)
            .agg(total_quantity=('quantity', 'sum'))
        )

        grouped_df['Inventory ID'] = grouped_df['order_id']
        grouped_df['Email'] = grouped_df['email']
        grouped_df['Total Item'] = grouped_df['total_quantity']
        grouped_df['Order Date & Time'] = grouped_df['ordered_time_date']
        grouped_df['Status'] = grouped_df['status']
        columns_to_display = ['Inventory ID', 'Email', 'Total Item', 'Order Date & Time', 'Status']
        grouped_df_display = grouped_df[columns_to_display]
        grouped_df_display.index = pd.RangeIndex(start=1, stop=len(grouped_df_display) + 1, step=1)

        # Display grouped orders
        st.subheader("Preparing Orders")
        st.dataframe(grouped_df_display, use_container_width = True)
        #st.write(order_df)

        # Dropdown to select an order_id
        order_ids = grouped_df['order_id'].tolist()
        selected_order_id = st.selectbox("Select an Order ID to View Details", order_ids)

        if selected_order_id:
            # Filter and display items for the selected order_id
            selected_items = order_df[order_df['order_id'] == selected_order_id]

            # Select required columns
            filtered_items = selected_items[
                ['name', 'size', 'category', 'sugar_level', 'addons', 'milk_type', 'quantity', 'temperature']
            ]

            st.subheader(f"Items in Order ID: {selected_order_id}")
        
            for index, row in filtered_items.iterrows():
                with st.expander(f"Item : {row['name']} (Quantity: {row['quantity']})"):
                    st.markdown(f"**Size**: {row['size']}")
                    st.markdown(f"**Category**: {row['category']}")
                    st.markdown(f"**Sugar Level**: {row['sugar_level']}")
                    
                    # Handle Add-Ons as a numbered list
                    if isinstance(row['addons'], list) and row['addons']:
                        st.markdown("**Add-Ons:**")
                        for idx, addon in enumerate(row['addons'], start=1):
                            st.markdown(
                                        f"""
                                        <div style="margin-left: 20px;">
                                            {idx}. {addon}
                                        </div>
                                        """,
                                        unsafe_allow_html=True,
                                    )
                        st.markdown("")
                        st.markdown("")
                    else:
                        st.markdown("**Add-Ons**: None")
                    st.markdown(f"**Milk Type**: {row['milk_type']}")
                    st.markdown(f"**Temperature**: {row['temperature']}")

            # Button to complete the selected order
            if st.button("Complete Order"):
                complete_order_by_id(selected_order_id, orders)
                st.success(f"Order ID {selected_order_id} has been marked as Done!")
                update_inventory(orders)
                st.rerun()  # Refresh the page after completing the order
    else:
        st.subheader("Total Pending Orders: 0")
        st.write("No orders are currently in the 'Preparing' status.")

def dashboard():
    # Assuming store.collection is iterable and get_ref is a callable function
    data = {}  # Initialize an empty list to store the references
        
    collections = store.collections()  # Returns an iterable of collection references

    for collection in collections:
        # Assuming you want to store each collection's reference in the dictionary with the collection's id as the key
        data[collection.id] = get_ref(collection.id)  # Use collection.id as the key # Append the reference to the data list
            
    st.write(data)
    selection = st.sidebar.selectbox("Select View", ["Dataset Summary",
                                                     "Sales Analytics Dashboard",
                                                     "Customer Analytics Dashboard",
                                                     "Inventory Analytics Dashboard",
                                                     "Promotion and Discount Analytics",
                                                     "Financial Analytics",
                                                     "Operational Analytics",
                                                     "Order Monitoring Dashboard"])
    st.write(data['cart']['ordered_time_date'])
    # Convert sale_date to datetime if it's not already
    data['cart']['ordered_time_date'] = pd.to_datetime(data['cart']['ordered_time_date'])
        
    # Sidebar Filters: Branch, Time Period, and Date Range
    with st.sidebar:
        # Container with Border for Filters
        with st.container():
            st.subheader("Filter Data")

            # Branch Filter
            #branches = ['All'] + list(data['cart']['branch_id'].unique())  # Assuming 'branch_id' is in data['sale']
            selected_branch = branch_id #st.selectbox('Select Branch:', branches)

            # Time Period Filter
            period = st.selectbox('Select Time Period:', ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Yearly'])

            # Date Range Filter
            min_date = data['cart']['ordered_time_date'].min()  # Minimum date in your dataset (using 'sale_date' here)
            max_date = data['cart']['ordered_time_date'].max()  # Maximum date in your dataset
            start_date, end_date = st.date_input('Select Date Range:', [min_date, max_date])


    # Apply the selected filters to sale_data
    sale_data_filtered = data['cart'][
        (data['cart']['ordered_time_date'] >= pd.to_datetime(start_date)) & 
        (data['cart']['ordered_time_date'] < pd.to_datetime(end_date) + pd.Timedelta(days=1))
    ]

    # Apply the selected branch filter
    if selected_branch != 'All':
        sale_data_filtered = sale_data_filtered[sale_data_filtered['branch_id'] == selected_branch]

    # Merge the filtered sale data with order data based on sale_id
    order_data_filtered = data['cart']#.merge(sale_data_filtered[['cart_id']], on='cart_id', how='inner')
    
    # Filter the feedback data based on sale_id from the filtered sale data
    #filtered_feedback_data = data['feedback'][data['feedback']['cart_id'].isin(sale_data_filtered['cart_id'])]

    # Assuming you have the operatingcost data in data['operatingcost']
    operatingcost_data = data['operatingcost']

    # Create a filtered version of operatingcost_data based on branch and time period filters
    operatingcost_data_filtered = operatingcost_data.copy()

    # Apply the selected branch filter
    if selected_branch != 'All':
        operatingcost_data_filtered = operatingcost_data_filtered[operatingcost_data_filtered['branch_id'] == selected_branch]
    # Apply the time period filter (Monthly or Yearly)
    if period == 'Monthly':
        # Group by year and month (we'll extract these from the start_date and end_date)
        operatingcost_data_filtered['year'] = pd.to_datetime(start_date).year
        operatingcost_data_filtered['month'] = pd.to_datetime(start_date).month
        operatingcost_data_filtered = operatingcost_data_filtered.groupby(['branch_id', 'year', 'month']).sum().reset_index()
    elif period == 'Yearly':
        # Group by year
        operatingcost_data_filtered['year'] = pd.to_datetime(start_date).year
        operatingcost_data_filtered = operatingcost_data_filtered.groupby(['branch_id', 'year']).sum().reset_index()
    

    # Now handle the different views based on user selection
    if selection == "Dataset Summary":
        st.title("Data Overview")
        gf.display_dataset_summary(data)

    elif selection == "Sales Analytics Dashboard":
        st.title("Sales Analytics Dashboard")
        st.markdown("<hr>", unsafe_allow_html=True)
        gf.plot_best_worst_sellers(order_data_filtered, data['product'])
        st.markdown("<hr>", unsafe_allow_html=True)
        gf.plot_total_sales(sale_data_filtered, order_data_filtered, period)
        st.markdown("<hr>", unsafe_allow_html=True)
        gf.plot_sales_by_product(order_data_filtered, data['product'])
        st.markdown("<hr>", unsafe_allow_html=True)
        gf.plot_sales_by_time_of_day(sale_data_filtered)
        st.markdown("<hr>", unsafe_allow_html=True)
        gf.calculate_profit(sale_data_filtered, order_data_filtered, data['product'], data['addon'], period)

    elif selection == "Customer Analytics Dashboard":
        st.title("Customer Analytics Dashboard")
        # Filter customers using the filtered sales data
        filtered_customers = data['customer'][data['customer']['customer_id'].isin(sale_data_filtered['customer_id'])]
        # Pass the filtered data to the plotting functions
        st.markdown("<hr>", unsafe_allow_html=True)
        gf.plot_customer_demographics(filtered_customers)
        st.markdown("<hr>", unsafe_allow_html=True)
        gf.plot_order_frequency_history(order_data_filtered, sale_data_filtered)

    elif selection == "Inventory Analytics Dashboard":
        st.title("Inventory Analytics Dashboard")
        gf.display_low_stock_products(data['inventory'], selected_branch)
        st.markdown("<hr>", unsafe_allow_html=True)
        gf.calculate_inventory_turnover(data, selected_branch)
        #plot_inventory_turnover(data['sale'], data['inventory'])
        #plot_stock_levels(data['sale'], data['order'], data['inventory'])
        #display_low_stock_alerts(data['inventory'])
        #plot_inventory_cost_analysis(data['product'])


    elif selection == "Promotion and Discount Analytics":
        st.title("Promotion and Discount Analytics")
        # Use the already filtered `sale_data_filtered`
        # Add a radio button to toggle between Sales or Orders for Promotion Performance Chart
        metric = st.radio("Select Metric for Promotion Performance", ["Sales", "Orders"])
        # Plot Promotion Performance based on selected metric
        gf.plot_promotion_performance(sale_data_filtered, metric)
        st.markdown("<hr>", unsafe_allow_html=True)
        # Plot Coupon Usage Over Time
        gf.plot_coupon_usage_over_time(sale_data_filtered)

    elif selection == "Financial Analytics":
        st.title("Financial Analytics")
        st.markdown("<hr>", unsafe_allow_html=True)
        gf.profit_margin_analysis(order_data_filtered, sale_data_filtered, data['product'])
        st.markdown("<hr>", unsafe_allow_html=True)
        gf.cost_analysis(data['operatingcost'], operatingcost_data_filtered)
        st.markdown("<hr>", unsafe_allow_html=True)
        gf.revenue_streams_analysis(order_data_filtered, data['product'])

    elif selection == "Operational Analytics":
        st.title("Operational Analytics")
        st.markdown("<hr>", unsafe_allow_html=True)
        gf.customer_feedback_ratings(data, sale_data_filtered, period)
        st.markdown("<hr>", unsafe_allow_html=True)
        gf.order_processing_times(sale_data_filtered)

    elif selection == "Order Monitoring Dashboard":
        gf.order_monitoring_dashboard(sale_data_filtered)
    

    
page = st.sidebar.selectbox("Navigate to", ["Order Management", "Inventory Management", "Coupon Management", "Dashboards"])

if page == "Inventory Management":
    inventory(branch_id)
elif page == "Coupon Management":
    coupon()
elif page == "Order Management":
    branch_order(branch_id)
elif page == "Dashboards":
    dashboard()

st.sidebar.markdown("<br><br><br><br><br><br><br><br><br><br>", unsafe_allow_html=True)
if st.sidebar.button("Log out"):
    logout()
