import streamlit as st
# from inventory_page import inventory
# from coupon_page import coupon
from navigation import make_sidebar, logout
from functions import cookies
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from firebase_config import store
import plotly.express as px
import plotly.graph_objects as go
import time

make_sidebar()

#st.write(cookies.getAll())
if cookies.get('email'):
    pass
else:
    logout()

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
                    'branch_id': branch_id,
                    'date' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            elif action == "restock":
                new_quantity = current_quantity + quantity
                # Add to restock_history collection
                store.collection('restock_history').add({
                    'inventory_id': inventory_id,
                    'quantity': quantity,
                    'branch_id': branch_id,
                    'date' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
            'start_date': start_date.strftime("%Y-%m-%d"),
            'expiry_date': expiry_date.strftime("%Y-%m-%d")
        }
        
        # Add the offer data to the 'coupon' collection in Firestore
        store.collection('coupon').document(offer_code).set(offer_data)
        
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
    try:
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
    except:
        st.write('No coupon created yet')

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
                    'branch_id': branch_id,
                    'date' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Update the status of each matching order to 'Done'
        for order in filtered_orders:
            cart_ref.document(order['id']).update({'status': 'Done', 'complete_date': date_now})


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
        
    def plot_best_worst_sellers(sale):
        # Group by product and sum the quantity sold for each product
        sales_by_product = sale.groupby('name')['quantity'].sum().reset_index()
        # Rename columns for clarity
        sales_by_product.rename(columns={'name': 'Product', 'quantity': 'Quantity Sold'}, inplace=True)
        # Sort the products by total quantity sold to identify best and worst sellers
        sales_by_product_sorted = sales_by_product.sort_values(by='Quantity Sold', ascending=False)
        # Get top 3 best sellers based on quantity sold
        best_sellers = sales_by_product_sorted.head(3)
        # Get bottom 3 worst sellers based on quantity sold
        worst_sellers = sales_by_product_sorted.tail(3)
        # Create two columns for displaying Best and Worst Sellers side by side
        col1, col2 = st.columns(2)
        # Display Best Sellers in the first column
        with col1:
            st.subheader("Top 3 Best Sellers")
            for _, row in best_sellers.iterrows():
                st.success(f"**{row['Product']}**  \nQuantity Sold: {row['Quantity Sold']}")
        # Display Worst Sellers in the second column
        with col2:
            st.subheader("Bottom 3 Worst Sellers")
            for _, row in worst_sellers.iterrows():
                st.error(f"**{row['Product']}**  \nQuantity Sold: {row['Quantity Sold']}")

    def plot_total_sales(sale_data, order_data, period):
        st.header("A. Total Sales Overview")
    
        # Convert `sale_date` to datetime
        sale_data['ordered_time_date'] = pd.to_datetime(sale_data['ordered_time_date'], errors='coerce')
    
        # Summarize quantity sold per `sale_id` from `order_data`
        order_quantity = order_data.groupby('cart_id')['quantity'].sum().reset_index()
        order_quantity.rename(columns={'quantity': 'quantity_sold'}, inplace=True)
    
        # Merge quantity data with sales data
        sale_data = sale_data.merge(order_quantity, on='cart_id', how='left')
    
        # Define period mapping for aggregation
        period_mapping = {
            'Daily': ('%Y-%m-%d', sale_data['ordered_time_date'].dt.date),
            'Weekly': ('%Y-%m-%d', sale_data['ordered_time_date'].dt.to_period('W').dt.start_time),
            'Monthly': ('%Y-%m', sale_data['ordered_time_date'].dt.to_period('M').dt.start_time),
            'Quarterly': ('%Y-Q%q', sale_data['ordered_time_date'].dt.to_period('Q').dt.start_time),
            'Yearly': ('%Y', sale_data['ordered_time_date'].dt.to_period('Y').dt.start_time),
        }
    
        x_axis_format, sale_data['period'] = period_mapping.get(period, ('%Y-%m-%d', sale_data['ordered_time_date'].dt.date))
    
        # Aggregate sales data
        total_sales = sale_data.groupby('period').agg(
            total_revenue=('price_after_discount', 'sum'),
            quantity_sold=('quantity', 'sum')
        ).reset_index()
    
        # Find the max and min values for revenue and quantity sold directly from the aggregated data
        max_revenue_day = total_sales.loc[total_sales['total_revenue'].idxmax()]
        max_revenue_value = max_revenue_day['total_revenue']
        max_revenue_date = max_revenue_day['period']
    
        min_revenue_day = total_sales.loc[total_sales['total_revenue'].idxmin()]
        min_revenue_value = min_revenue_day['total_revenue']
        min_revenue_date = min_revenue_day['period']
    
        max_quantity_day = total_sales.loc[total_sales['quantity_sold'].idxmax()]
        max_quantity_value = max_quantity_day['quantity_sold']
        max_quantity_date = max_quantity_day['period']
    
        min_quantity_day = total_sales.loc[total_sales['quantity_sold'].idxmin()]
        min_quantity_value = min_quantity_day['quantity_sold']
        min_quantity_date = min_quantity_day['period']
    
        summary_stats = {
            "Total Revenue": sale_data['price_after_discount'].sum(),
            "Average Revenue": sale_data['price_after_discount'].mean(),
            "Max Revenue (Day)": max_revenue_value,
            "Max Revenue Date": max_revenue_date,
            "Min Revenue (Day)": min_revenue_value,
            "Min Revenue Date": min_revenue_date,
            "Total Quantity Sold": sale_data['quantity_sold'].sum(),
            "Average Quantity Sold": sale_data['quantity_sold'].mean(),
            "Max Quantity Sold (Day)": max_quantity_value,
            "Max Quantity Date": max_quantity_date,
            "Min Quantity Sold (Day)": min_quantity_value,
            "Min Quantity Date": min_quantity_date
        }
    
        # Display summary statistics in metric cards
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Revenue", f"${summary_stats['Total Revenue']:.2f}")
            st.metric("Average Revenue", f"${summary_stats['Average Revenue']:.2f}")
            st.metric("Max Revenue (Day)", f"${summary_stats['Max Revenue (Day)']:.2f}", f"Date: {summary_stats['Max Revenue Date']:%Y-%m-%d}")
            st.metric("Min Revenue (Day)", f"${summary_stats['Min Revenue (Day)']:.2f}", f"Date: {summary_stats['Min Revenue Date']:%Y-%m-%d}")
        with col2:
            st.metric("Total Quantity Sold", f"{summary_stats['Total Quantity Sold']:.0f}")
            st.metric("Average Quantity Sold", f"{summary_stats['Average Quantity Sold']:.2f}")
            st.metric("Max Quantity Sold (Day)", f"{summary_stats['Max Quantity Sold (Day)']:.0f}", f"Date: {summary_stats['Max Quantity Date']:%Y-%m-%d}")
            st.metric("Min Quantity Sold (Day)", f"{summary_stats['Min Quantity Sold (Day)']:.0f}", f"Date: {summary_stats['Min Quantity Date']:%Y-%m-%d}")
    
        # Plot Total Revenue
        st.subheader("⦁ Total Revenue")
        graph_type_revenue = st.selectbox("Select Graph Type for Revenue", ["Line Graph", "Bar Chart"], key="revenue_graph_select")
    
        if graph_type_revenue == "Line Graph":
            fig_revenue = px.line(total_sales, x='period', y='total_revenue', title='Total Revenue Over Time', markers=True)
        else:
            fig_revenue = px.bar(total_sales, x='period', y='total_revenue', title='Total Revenue Over Time', text='total_revenue', color='total_revenue', color_continuous_scale='Blues')
            fig_revenue.update_traces(texttemplate='%{text:.2f}')
    
        fig_revenue.update_layout(
            xaxis_title='Time Period',
            yaxis_title='Total Revenue',
            xaxis=dict(tickangle=45),
            autosize=True,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        st.plotly_chart(fig_revenue)
    
        # Plot Quantity Sold
        st.subheader("⦁ Quantity Sold")
        graph_type_quantity = st.selectbox("Select Graph Type for Quantity", ["Line Graph", "Bar Chart"], key="quantity_graph_select")
    
        if graph_type_quantity == "Line Graph":
            fig_quantity = px.line(total_sales, x='period', y='quantity_sold', title='Quantity Sold Over Time', markers=True)
        else:
            fig_quantity = px.bar(total_sales, x='period', y='quantity_sold', title='Quantity Sold Over Time', text='quantity_sold', color='quantity_sold', color_continuous_scale='Blues')
            fig_quantity.update_traces(texttemplate='%{text:.0f}')
    
        fig_quantity.update_layout(
            xaxis_title='Time Period',
            yaxis_title='Quantity Sold',
            xaxis=dict(tickangle=45),
            autosize=True,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        st.plotly_chart(fig_quantity)

    def plot_sales_by_product(order_data):
        st.header("B. Sales Breakdown by Product")

        # Merge the order data with the product data to get product details
        merged_data = order_data

        # Ensure the quantity column is numeric
        merged_data['quantity'] = pd.to_numeric(merged_data['quantity'], errors='coerce')

        # Select the drill level (Category or Product)
        drill_level = st.radio(
            "Choose Drill Level:",
            options=["By Product Category", "By Individual Product"],
            index=0
        )

        if drill_level == "By Product Category":
            # Group by product category and calculate total quantity sold
            sales_data = merged_data.groupby('category')['quantity'].sum().reset_index()
            sales_data.rename(columns={'category': 'Category', 'quantity': 'Quantity Sold'}, inplace=True)

            # Find the highest and lowest sales categories (handling ties)
            max_sales = sales_data['Quantity Sold'].max()
            min_sales = sales_data['Quantity Sold'].min()

            # Filter to get all categories with the highest and lowest sales
            highest_sales_categories = sales_data[sales_data['Quantity Sold'] == max_sales]
            lowest_sales_categories = sales_data[sales_data['Quantity Sold'] == min_sales]

            # Create a bar chart for product category sales
            fig = px.bar(
                sales_data, 
                x='Category', 
                y='Quantity Sold', 
                title="Sales Breakdown by Product Category",
                color='Quantity Sold',
                color_continuous_scale='Blues',
                labels={'Quantity Sold': 'Quantity Sold', 'Category': 'Product Category'},
            )

            # Display cards for highest and lowest sales categories
            st.subheader("Highest and Lowest Sales Categories")
            col1, col2 = st.columns(2)

            with col1:
                # Display highest sales categories
                st.markdown("<h4 style='font-size:18px;'>Highest Sales</h4>", unsafe_allow_html=True)
                for _, row in highest_sales_categories.iterrows():
                    st.success(f"**{row['Category']}**  \nQuantity Sold: {row['Quantity Sold']}")

            with col2:
                # Display lowest sales categories
                st.markdown("<h4 style='font-size:18px;'>Lowest Sales</h4>", unsafe_allow_html=True)
                for _, row in lowest_sales_categories.iterrows():
                    st.error(f"**{row['Category']}**  \nQuantity Sold: {row['Quantity Sold']}")

        else:  # Drill down to individual products
            category_filter = st.selectbox(
                "Choose a Product Category (or 'All' for all products):",
                options=['All'] + merged_data['category'].unique().tolist(),
                index=0
            )

            # Filter the data based on the selected category
            if category_filter != 'All':
                filtered_data = merged_data[merged_data['category'] == category_filter]
            else:
                filtered_data = merged_data

            # Group by product name and calculate total quantity sold
            sales_data = filtered_data.groupby('name')['quantity'].sum().reset_index()
            sales_data.rename(columns={'name': 'Product', 'quantity': 'Quantity Sold'}, inplace=True)

            # Find the highest and lowest sales products (handling ties)
            max_sales = sales_data['Quantity Sold'].max()
            min_sales = sales_data['Quantity Sold'].min()

            # Filter to get all products with the highest and lowest sales
            highest_sales_products = sales_data[sales_data['Quantity Sold'] == max_sales]
            lowest_sales_products = sales_data[sales_data['Quantity Sold'] == min_sales]

            # Create a bar chart for individual product sales
            fig = px.bar(
                sales_data, 
                x='Product', 
                y='Quantity Sold', 
                title=f"Sales Breakdown by Individual Product ({category_filter})",
                color='Quantity Sold',
                color_continuous_scale='Blues',
                labels={'Quantity Sold': 'Quantity Sold', 'Product': 'Product Name'},
            )

            # Display cards for highest and lowest sales products
            st.subheader("Highest and Lowest Sales Products")
            col1, col2 = st.columns(2)

            with col1:
                # Display highest sales products
                st.markdown("<h4 style='font-size:18px;'>Highest Sales</h4>", unsafe_allow_html=True)
                for _, row in highest_sales_products.iterrows():
                    st.success(f"**{row['Product']}**  \nQuantity Sold: {row['Quantity Sold']}")

            with col2:
                # Display lowest sales products
                st.markdown("<h4 style='font-size:18px;'>Lowest Sales</h4>", unsafe_allow_html=True)
                for _, row in lowest_sales_products.iterrows():
                    st.error(f"**{row['Product']}**  \nQuantity Sold: {row['Quantity Sold']}")

        # Render the Plotly chart in Streamlit
        st.plotly_chart(fig)

    def plot_sales_by_time_of_day(sale_data):
        st.header("C. Sales by Time of Day")

        # Ensure the 'sale_date' is in datetime format
        sale_data['ordered_time_date'] = pd.to_datetime(sale_data['ordered_time_date'], errors='coerce')
        
        # Create a new column for the hour of the day
        sale_data['hour'] = sale_data['ordered_time_date'].dt.hour

        # Group the sales data by hour and calculate the total sales
        sales_by_hour = sale_data.groupby('hour')['price_after_discount'].sum().reset_index()

        # Find the best and worst times based on the total sales
        max_sales = sales_by_hour['price_after_discount'].max()
        min_sales = sales_by_hour['price_after_discount'].min()

        # Filter to get all hours with the best and worst sales
        best_times = sales_by_hour[sales_by_hour['price_after_discount'] == max_sales]
        worst_times = sales_by_hour[sales_by_hour['price_after_discount'] == min_sales]

        # Create an interactive line chart for total sales by hour of the day
        fig = px.line(sales_by_hour, x='hour', y='price_after_discount', markers=True)
        fig.update_layout(
            title='Total Sales by Hour of Day (Overall)',
            xaxis_title="Hour of Day",
            yaxis_title="Total Sales"
        )

        # Display cards for best and worst times
        st.subheader("Best and Worst Times for Sales")
        col1, col2 = st.columns(2)

        with col1:
            # Display best time cards (for multiple best times)
            st.markdown("<h4 style='font-size:18px;'>Best Time(s)</h4>", unsafe_allow_html=True)
            for _, row in best_times.iterrows():
                st.success(f"**{row['hour']:.2f} Hours**  \nTotal Sales: ${row['price_after_discount']:.2f}", icon=None)

        with col2:
            # Display worst time cards (for multiple worst times)
            st.markdown("<h4 style='font-size:18px;'>Worst Time(s)</h4>", unsafe_allow_html=True)
            for _, row in worst_times.iterrows():
                st.error(f"**{row['hour']} Hours**  \nTotal Sales: ${row['price_after_discount']:.2f}", icon=None)

        # Render the Plotly chart in Streamlit
        st.plotly_chart(fig)

    def calculate_profit(sale, inventory_df, inv_usage_df, time_period):
        st.header("D. Profit Calculation")

        # Group by the selected time period
        if time_period == "Daily":
            # Aggregate profit by day
            sale['date'] = sale['ordered_time_date'].dt.date

        elif time_period == "Weekly":
            # Aggregate profit by week
            sale['date'] = sale['ordered_time_date'].dt.to_period('W').dt.start_time

        elif time_period == "Monthly":
            # Aggregate profit by month
            sale['date'] = sale['ordered_time_date'].dt.to_period('M').dt.start_time
            
        elif time_period == "Quarterly":
            # Aggregate profit by month
            sale['date'] = sale['ordered_time_date'].dt.to_period('Q').dt.start_time

        elif time_period == "Yearly":
            # Aggregate profit by month
            sale['date'] = sale['ordered_time_date'].dt.to_period('Y').dt.start_time

        
        sale['revenue'] = sale['quantity']*sale['price_after_discount']        
        inv_usage_df = pd.merge(inv_usage_df, inventory_df, on='inventory_id', how='left')
        inv_usage_df['ingredient_cost'] = inv_usage_df['usage'] * inv_usage_df['unit_price']

        # Map inv_usage to cart
        def calculate_cart_cost(row):
            base_cost = inv_usage_df[inv_usage_df['item_name'] == row['name']]['ingredient_cost'].sum()
            milk_cost = inv_usage_df[inv_usage_df['item_name'] == row['milk_type']]['ingredient_cost'].sum()
            sugar_cost = inv_usage_df[inv_usage_df['item_name'] == row['sugar_level']]['ingredient_cost'].sum()
            temp_cost = inv_usage_df[inv_usage_df['item_name'] == row['temperature']]['ingredient_cost'].sum()
            addons_cost = 0
            for addon in row['addons']:
                addons_cost += inv_usage_df[inv_usage_df['item_name'] == addon]['ingredient_cost'].sum()
            total_cost = (base_cost + milk_cost + sugar_cost + temp_cost + addons_cost) * row['quantity']
            return total_cost

        sale['total_cost'] = sale.apply(calculate_cart_cost, axis=1)
        sale['profit'] = sale['revenue'] - sale['total_cost']

        profit_aggregated = sale.groupby('date')['profit'].sum().reset_index()

        # Plot the profit based on the selected time period
        st.subheader(f"⦁ Profit ({time_period})")
        graph_type_profit = st.selectbox(f"Select Graph Type for Profit ({time_period})", ["Line Graph", "Bar Chart"], key=f"profit_graph_{time_period}")
        
        if graph_type_profit == "Line Graph":
            fig_profit = px.line(profit_aggregated, x='date', y='profit', title=f'{time_period} Profit Over Time', markers=True)
            fig_profit.update_layout(
                xaxis_title=f'{time_period} Period',
                yaxis_title='Profit'
            )
            st.plotly_chart(fig_profit)
        else:
            fig_profit = px.bar(profit_aggregated, x='date', y='profit', title=f'{time_period} Profit Over Time', text='profit', color='profit', color_continuous_scale='Blues')
            fig_profit.update_traces(texttemplate='%{text:.2f}')
            fig_profit.update_layout(
                xaxis_title=f'{time_period} Period',
                yaxis_title='Profit'
            )
            st.plotly_chart(fig_profit)

    def plot_customer_demographics(customer_data):
        st.subheader("A. Customer Demographics")

        # Create age groups for categorization
        age_group = pd.cut(customer_data['age'], bins=[0, 18, 30, 40, 50, float('inf')], 
                        labels=['<18', '18-30', '30-40', '40-50', '50+'])
        
        # Count number of customers by age group
        age_group_counts = age_group.value_counts().reset_index()
        age_group_counts.columns = ['Age Group', 'Number of Customers']
        
        # Select graph type from the user
        demographic_graph_type = st.selectbox("Select Graph Type", ["Bar Chart", "Pie Chart"])

        # Plot the demographic categories
        if demographic_graph_type == "Bar Chart":
            fig = px.bar(age_group_counts, x='Age Group', y='Number of Customers',
                        title='Customer Age Demographics',
                        labels={'Number of Customers': 'Number of Customers'},
                        hover_data=['Number of Customers'])
            # Ensure the bar chart is sorted by age group
            fig.update_xaxes(categoryorder='array', categoryarray=['<18', '18-30', '30-40', '40-50', '50+'])
            st.plotly_chart(fig)
        elif demographic_graph_type == "Pie Chart":
            fig = px.pie(age_group_counts, values='Number of Customers', names='Age Group',
                        title='Customer Age Demographics',
                        hover_data=['Number of Customers'])
            st.plotly_chart(fig)

    def plot_order_frequency_history(sale_data):
        st.subheader("B. Order Frequency and History")

        # Group by order date and count orders
        order_frequency = sale_data.groupby('ordered_time_date').size().reset_index(name='Number of Orders')

        # Line chart for order frequency over time
        fig = px.line(order_frequency, x='ordered_time_date', y='Number of Orders',
                    title="Order Frequency Over Time",
                    labels={'sale_date': 'Date', 'Number of Orders': 'Number of Orders'})
        st.plotly_chart(fig)

    def display_low_stock_products(inventory_filtered, selected_branch):

        st.subheader("Low Stock Products")
        st.write("Selected Branch:", selected_branch)

        # Filter inventory by branch
        if selected_branch != 'All':
            inventory_filtered = inventory_filtered[inventory_filtered['branch_id'] == selected_branch]

        # Identify low stock items
        low_stock = inventory_filtered[
            inventory_filtered['quantity_on_hand'] < inventory_filtered['minimum_stock_level']
        ]

        # Display low stock items
        if not low_stock.empty:
            for _, row in low_stock.iterrows():
                st.markdown(f"""
                <div style="border: 1px solid #ddd; border-radius: 5px; padding: 10px; margin-bottom: 10px;">
                    <h4>{row['inventory_name']}</h4>
                    <p>Current Amount: {row['quantity_on_hand']}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("No low stock items found.")
    
    def calculate_inventory_turnover(inventory, usage, selected_branch, time_period):

        st.subheader("Inventory Turnover")
        # Filter data for the selected branch and time period
        inventory_branch = inventory[inventory['branch_id'] == selected_branch]
        usage_branch = usage[usage['branch_id'] == selected_branch]
        usage_branch['date'] = pd.to_datetime(usage_branch['date'])
        inventory_branch = pd.merge(usage_branch, inventory_branch.drop(columns='branch_id'), on='inventory_id', how='outer')
        inventory_branch['date'] = inventory_branch['date'].fillna(datetime.now().strftime('%Y-%m-%d %H:%M:%S')) 

        # Calculate total_inventory and used_inventory as numeric types
        inventory_branch['total_inventory'] = pd.to_numeric(inventory_branch['quantity_on_hand'], errors='coerce') * pd.to_numeric(inventory_branch['unit_price'], errors='coerce')
        inventory_branch['used_inventory'] = pd.to_numeric(inventory_branch['quantity'], errors='coerce') * pd.to_numeric(inventory_branch['unit_price'], errors='coerce')
        
        # Now calculate turnover rate (usage / total_inventory)
        inventory_branch['turnover'] = inventory_branch['used_inventory'] / inventory_branch['total_inventory']
        inventory_branch['turnover'] = inventory_branch['turnover'].fillna(0)

        # Apply time period aggregation
        if time_period == 'Weekly':
            inventory_branch['period'] = inventory_branch['date'].dt.to_period('W')
        elif time_period == 'Monthly':
            inventory_branch['period'] = inventory_branch['date'].dt.to_period('M')
        elif time_period == 'Quarterly':
            inventory_branch['period'] = inventory_branch['date'].dt.to_period('Q')
        elif time_period == 'Yearly':
            inventory_branch['period'] = inventory_branch['date'].dt.to_period('Y')
        else:  # Daily
            inventory_branch['period'] = inventory_branch['date'].dt.date
        
        # Ensure 'period' is a string or datetime
        inventory_branch['period'] = inventory_branch['period'].astype(str)

        inventory_branch = inventory_branch.sort_values(by='period', ascending=True)

        fig = go.Figure()

        # Add the turnover rate line (Light Blue)
        fig.add_trace(go.Scatter(
            x=inventory_branch['period'],
            y=inventory_branch['turnover'],
            mode='lines',
            name='Inventory Turnover',
            line=dict(color='lightblue')
        ))

        # Customize the layout
        fig.update_layout(
            title=f'Inventory Turnover - {selected_branch} ({time_period})',
            xaxis_title='Date',
            yaxis_title='Turnover Rate',
            template='plotly_white',
            legend=dict(orientation='h', x=0.5, xanchor='center')
        )

        # Show the graph
        st.plotly_chart(fig)


    def plot_promotion_performance(sale_data, metric):
        st.header("A. Promotion Performance")
        
        # Add a promotion type column based on coupon_code presence
        sale_data['promotion_type'] = sale_data['coupon_used'].fillna("").apply(lambda x: 'Promotion' if x != '' else 'Non-Promotion')

        if metric == "Sales":
            # Group by promotion type and calculate total sales
            promotion_sales_df = sale_data.groupby('promotion_type')['price_after_discount'].sum().reset_index()
            # Display total sales amounts as metrics
            promotion_sales = promotion_sales_df.set_index('promotion_type')['price_after_discount']
            col1, col2 = st.columns(2)  # Create two columns for metrics
            col1.metric("Total Sales (Promotion)", round(promotion_sales.get('Promotion', 0), 2))
            col2.metric("Total Sales (Non-Promotion)", round(promotion_sales.get('Non-Promotion', 0), 2))
            values = promotion_sales_df['price_after_discount']
            labels = promotion_sales_df['promotion_type']
        elif metric == "Orders":
            # Group by promotion type and calculate total orders
            promotion_sales_df = sale_data.groupby('promotion_type').size().reset_index(name='order_count')
            promotion_sales_df.rename(columns={'order_count': 'price_after_discount'}, inplace=True)
            # Display total number of orders as metrics
            promotion_orders = promotion_sales_df.set_index('promotion_type')['price_after_discount']
            col1, col2 = st.columns(2)  # Create two columns for metrics
            col1.metric("Total Orders (Promotion)", promotion_orders.get('Promotion', 0))
            col2.metric("Total Orders (Non-Promotion)", promotion_orders.get('Non-Promotion', 0))
            values = promotion_sales_df['price_after_discount']
            labels = promotion_sales_df['promotion_type']
        
        # Plot promotion performance as a pie chart
        fig1 = go.Figure()
        fig1.add_trace(go.Pie(labels=labels, values=values, name='Impact'))
        fig1.update_layout(
            title=f'Impact During Promotional vs Non-Promotional Periods ({metric})'
        )

        # Display the pie chart in Streamlit
        st.plotly_chart(fig1)

    # Function to plot Coupon Usage Over Time Chart
    def plot_coupon_usage_over_time(sale_data):
        st.header("B. Coupon Usage Over Time")

        # Filter sales with coupons and group by date for coupon-based sales
        coupon_sales = sale_data[sale_data['coupon_used'] != 'None']
        coupon_sales_by_date = coupon_sales.groupby('ordered_time_date')['price_after_discount'].sum()

        # Plot coupon usage over time as a line chart
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=coupon_sales_by_date.index, y=coupon_sales_by_date.values, mode='lines+markers', name='Coupon Sales'))
        fig2.update_layout(
            title='Sales Generated from Coupons Over Time',
            xaxis_title='Date',
            yaxis_title='Coupon-Related Sales Amount'
        )

        # Display the chart in Streamlit
        st.plotly_chart(fig2)

    # Financial Analytics

    # Function to perform Profit Margin Analysis
    def profit_margin_analysis(cart_df, inventory_df, inv_usage_df, time_period):
        st.header("A. Profit Margin Analysis")
        inv_usage_df = pd.merge(inv_usage_df, inventory_df, on='inventory_id', how='left')
        inv_usage_df['ingredient_cost'] = inv_usage_df['usage'] * inv_usage_df['unit_price']

        # Map inv_usage to cart
        def calculate_cart_cost(row):
            base_cost = inv_usage_df[inv_usage_df['item_name'] == row['name']]['ingredient_cost'].sum()
            milk_cost = inv_usage_df[inv_usage_df['item_name'] == row['milk_type']]['ingredient_cost'].sum()
            sugar_cost = inv_usage_df[inv_usage_df['item_name'] == row['sugar_level']]['ingredient_cost'].sum()
            temp_cost = inv_usage_df[inv_usage_df['item_name'] == row['temperature']]['ingredient_cost'].sum()
            addons_cost = 0
            for addon in row['addons']:
                addons_cost += inv_usage_df[inv_usage_df['item_name'] == addon]['ingredient_cost'].sum()
            total_cost = (base_cost + milk_cost + sugar_cost + temp_cost + addons_cost) * row['quantity']
            return total_cost

        cart_df['cart_cost'] = cart_df.apply(calculate_cart_cost, axis=1)

        cart_df['Profit Margin'] = (cart_df['price_after_discount'] - cart_df['cart_cost'])/cart_df['price_after_discount']
        
        profit_margin_data = cart_df.groupby('name')['Profit Margin'].mean().reset_index()
        
        # Create three columns layout for the cards
        col1, col2, col3 = st.columns(3)
        
        # Card 1: Average Profit Margin
        avg_profit_margin = cart_df['Profit Margin'].mean()
        col1.metric("Average Profit Margin", f"{avg_profit_margin:.2f}%")
        
        # Card 2: Product with Highest Profit Margin
        highest_margin_product = profit_margin_data.loc[profit_margin_data['Profit Margin'].idxmax()]
        col2.metric(f"Highest Profit Margin Product: {highest_margin_product['name']}", 
                    f"{highest_margin_product['Profit Margin']:.2f}%")
        
        # Card 3: Product with Lowest Profit Margin
        lowest_margin_product = profit_margin_data.loc[profit_margin_data['Profit Margin'].idxmin()]
        col3.metric(f"Lowest Profit Margin Product: {lowest_margin_product['name']}", 
                    f"{lowest_margin_product['Profit Margin']:.2f}%")
        
        # Create bar chart for profit margin analysis
        fig_profit_margin = px.bar(profit_margin_data, x='name', y='Profit Margin',
                                title='Profit Margin Analysis',
                                labels={'Profit Margin': 'Profit Margin (%)'},
                                text='Profit Margin')
        st.plotly_chart(fig_profit_margin)


    def cost_analysis(operatingcost_data, operatingcost_data_filtered):
        st.header("B. Cost Analysis")
        
        # Calculate total cost and reshape data for visualization
        operatingcost_data_filtered['Total Cost'] = operatingcost_data_filtered[['rent', 'utilities', 'salaries', 'other_expenses']].sum(axis=1)
        cost_data = operatingcost_data_filtered[['branch_id', 'rent', 'utilities', 'salaries', 'other_expenses']]
        cost_data = cost_data.melt(id_vars='branch_id', var_name='Cost Category', value_name='Amount')
        
        # Create bar chart for cost analysis
        fig_cost_analysis = px.bar(cost_data, x='branch_id', y='Amount', color='Cost Category',
                                title='Cost Analysis',
                                labels={'Amount': 'Cost Amount'},
                                text='Amount')
        st.plotly_chart(fig_cost_analysis)

    # Function to analyze Revenue Streams
    def revenue_streams_analysis(order_data_filtered, product_data):
        st.header("C. Revenue Streams")
        
        # Merge order data with product data on 'product_id'
        product_data['name'] = product_data['product_name']
        merged_data = pd.merge(order_data_filtered, product_data, on='name')

        # Ensure 'total_price' is numeric, coercing errors to NaN
        merged_data['price_after_discount'] = pd.to_numeric(merged_data['price_after_discount'], errors='coerce')
        
        # Radio button selection to choose revenue view by product category or individual product
        revenue_view = st.radio(
            "Choose Revenue View",
            ("By Product Category", "By Individual Product")
        )
        
        # Conditional display based on radio button selection
        if revenue_view == "By Product Category":
            # Calculate total revenue per product category
            revenue_streams = merged_data.groupby('category')['price_after_discount'].sum().reset_index()

            # Calculate total revenue
            total_revenue = revenue_streams['price_after_discount'].sum()
            
            # Find the product category that contributes the most and least
            most_contrib_category = revenue_streams.loc[revenue_streams['price_after_discount'].idxmax()]
            least_contrib_category = revenue_streams.loc[revenue_streams['price_after_discount'].idxmin()]
            
            # Create three columns layout for the cards
            col1, col2, col3 = st.columns(3)

            # Display the Total Revenue Card in the first column
            col1.metric("Total Revenue", f"${total_revenue:.2f}")

            # Display the Product Category that contributes the most in the second column
            col2.metric(f"Top Product Category: {most_contrib_category['category']}", 
                        f"${most_contrib_category['price_after_discount']:.2f}")
            
            # Display the Product Category that contributes the least in the third column
            col3.metric(f"Least Product Category: {least_contrib_category['category']}", 
                        f"${least_contrib_category['price_after_discount']:.2f}")
            
            # Create pie chart for revenue streams distribution by product category
            fig_revenue_streams = px.pie(revenue_streams, values='price_after_discount', names='category',
                                        title='Revenue Streams Distribution',
                                        labels={'price_after_discount': 'Total Revenue'},
                                        hole=0.3)
            st.plotly_chart(fig_revenue_streams)

        elif revenue_view == "By Individual Product":
            # Dropdown for selecting product category or 'All'
            selected_category = st.selectbox(
                "Select a Product Category", 
                ["All"] + merged_data['category'].unique().tolist()
            )
            
            # Filter data based on the selected category or 'All'
            if selected_category == "All":
                category_data = merged_data
            else:
                category_data = merged_data[merged_data['category'] == selected_category]
            
            # Calculate total revenue
            total_revenue = category_data['price_after_discount'].sum()

            # Find the product that contributes the most and least
            most_contrib_product = category_data.groupby('name')['price_after_discount'].sum().idxmax()
            least_contrib_product = category_data.groupby('name')['price_after_discount'].sum().idxmin()

            # Calculate the total revenue per product
            product_revenue = category_data.groupby('name')['price_after_discount'].sum().reset_index()

            # Sort products by revenue in descending order
            product_revenue_sorted = product_revenue.sort_values(by='price_after_discount', ascending=False)

            # Create three columns layout for the cards
            col1, col2, col3 = st.columns(3)

            # Display the Total Revenue Card in the first column
            col1.metric("Total Revenue", f"${total_revenue:.2f}")

            # Display the Product that contributes the most in the second column
            col2.metric(f"Top Product: {most_contrib_product}", 
                        f"${product_revenue[product_revenue['name'] == most_contrib_product]['price_after_discount'].values[0]:.2f}")
            
            # Display the Product that contributes the least in the third column
            col3.metric(f"Least Product: {least_contrib_product}", 
                        f"${product_revenue[product_revenue['name'] == least_contrib_product]['price_after_discount'].values[0]:.2f}")
            
            # Create pie chart for individual products in the selected category or 'All'
            fig_product_revenue = px.pie(product_revenue_sorted, values='price_after_discount', names='name',
                                        title=f'Revenue Distribution for {selected_category} Products' if selected_category != "All" else 'Revenue Distribution for All Products',
                                        labels={'price_after_discount': 'Total Revenue'},
                                        hole=0.3)
            st.plotly_chart(fig_product_revenue)

    # ==============================================================================================

    # Operational Analytics

    # Function to parse date with multiple formats
    def parse_date(date_str):
        # If the input is already a datetime object (Timestamp)
        if isinstance(date_str, pd.Timestamp):
            return date_str

        try:
            # Try parsing in AM/PM format
            return datetime.strptime(date_str, "%m/%d/%y %I:%M %p")  # AM/PM format
        except ValueError:
            # Try parsing in 24-hour format if AM/PM format fails
            return datetime.strptime(date_str, "%m/%d/%y %H:%M")  # 24-hour format

    def customer_feedback_ratings(feedback, period, branch_id):
        st.header("A. Customer Feedback Ratings")
        try:
            filtered_feedback_data = feedback[feedback['branch_id'] == branch_id]
            filtered_feedback_data['date'] = pd.to_datetime(filtered_feedback_data['date'])
            # Apply time period aggregation
            if period == 'Weekly':
                filtered_feedback_data['period'] = filtered_feedback_data['date'].dt.to_period('W')
            elif period == 'Monthly':
                filtered_feedback_data['period'] = filtered_feedback_data['date'].dt.to_period('M')
            elif period == 'Quarterly':
                filtered_feedback_data['period'] = filtered_feedback_data['date'].dt.to_period('Q')
            elif period == 'Yearly':
                filtered_feedback_data['period'] = filtered_feedback_data['date'].dt.to_period('Y')
            else:  # Daily
                filtered_feedback_data['period'] = filtered_feedback_data['date'].dt.date

            # Rating dimensions
            rating_dimensions = ['rate_coffee', 'rate_service', 'rate_wait_time', 'rate_environment', 'rate_sanitary']

            # Calculate and display average rating across all dimensions
            overall_avg_rating = filtered_feedback_data[rating_dimensions].mean().mean()
            st.metric("Average Rating Across All Dimensions", round(overall_avg_rating, 2))

            # Create a layout with 3 columns for individual average ratings
            cols = st.columns(3)

            # Calculate and display average rating for each individual dimension in 3 columns
            for i, rating in enumerate(rating_dimensions):
                avg_rating = filtered_feedback_data[rating].mean()
                cols[i % 3].metric(f"Avg {rating.replace('_', ' ').title()}", round(avg_rating, 2))

            # Now aggregate the ratings by the selected period and create charts
            for rating in rating_dimensions:
                # Group by the selected period and calculate the mean of each rating dimension
                feedback_by_period = filtered_feedback_data.groupby('period')[rating].mean().reset_index()

                # Create the chart
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=feedback_by_period['period'].astype(str),  # Convert period to string for x-axis
                    y=feedback_by_period[rating],
                    mode='lines+markers',
                    name=rating
                ))

                fig.update_layout(
                    title=f'Average {rating.replace("_", " ").title()} Over Time',
                    xaxis_title='Period',
                    yaxis_title='Average Rating',
                    hovermode="closest"
                )

                # Display the chart inside an expander
                with st.expander(f"Average {rating.replace('_', ' ').title()} Rating"):
                    st.plotly_chart(fig)
        except:
            st.warning('No feedback yet')

    
                
    # Function to calculate and display order processing times
    def order_processing_times(sale_data):
        st.header("B. Order Processing Times")

        sale_date = 'ordered_time_date'
        order_completion_date = 'complete_date'

        # Ensure columns exist before calculation
        if sale_date in sale_data.columns and order_completion_date in sale_data.columns:
            # Calculate processing times in minutes
            processing_times = [
                (parse_date(completion) - parse_date(start)).total_seconds() / 60
                for start, completion in zip(sale_data[sale_date], sale_data[order_completion_date])
            ]

            # Create the interactive box plot
            fig_processing_time = go.Figure(
                go.Box(y=processing_times, name="Order Processing Time", boxmean="sd")
            )
            fig_processing_time.update_layout(
                title="Order Processing Times",
                yaxis_title="Processing Time (minutes)",
                hovermode="closest"
            )

            # Display in Streamlit
            st.plotly_chart(fig_processing_time)
        else:
            st.warning("Required columns ('sale_date', 'order_completion_date') are missing.")



    # ==============================================================================================

    def order_monitoring_dashboard(sale_data): 
        # Ensure time and datetime are imported
        st.title("PyBean Coffee Shop")
        st.subheader("Order Status Dashboard")

        # Live Time Section
        live_time_container = st.empty()  # Create an empty container for live updates

        # Convert sale_date to datetime and sort the data by the most recent sale
        sale_data['ordered_time_date'] = pd.to_datetime(sale_data['ordered_time_date'], format='%m/%d/%y %H:%M')  # Convert to datetime
        sale_data = sale_data.sort_values(by='ordered_time_date', ascending=False)  # Sort by newest first

        # Create two columns for "Preparing Orders" and "Ready for Collection"
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Preparing Orders")
            preparing_orders = sale_data[sale_data['status'] == 'Preparing']['cart_id']
            if not preparing_orders.empty:
                for order in preparing_orders:
                    st.write(order)
            else:
                st.write("No Preparing Orders")

        with col2:
            st.subheader("Ready for Collection")
            ready_orders = sale_data[sale_data['status'] == 'Done']['cart_id']
            if not ready_orders.empty:
                for order in ready_orders:
                    st.write(order)
            else:
                st.write("No Ready Orders")

        # Continuously update live time
        #while True:
        live_time_container.markdown(
            f"Live Date and Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
            #time.sleep(1)  # Wait for 1 second before updating again

        if st.button('Refresh'):
            st.rerun()

    selection = st.sidebar.selectbox("Select View", ["Sales Analytics Dashboard",
                                                     "Customer Analytics Dashboard",
                                                     "Inventory Analytics Dashboard",
                                                     "Promotion and Discount Analytics",
                                                     "Financial Analytics",
                                                     "Operational Analytics",
                                                     "Order Monitoring Dashboard"])
        
        
    # Sidebar Filters: Branch, Time Period, and Date Range
    with st.sidebar:
        # Container with Border for Filters
        with st.container():
            st.subheader("Filter Data")
            period = st.selectbox('Select Time Period:', ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Yearly'])

            if not get_ref('cart').empty: 
                cart_table = get_ref('cart')
                sale = cart_table[cart_table['status'] == 'Done']
                order = cart_table[cart_table['status'] != 'In Cart']
                # Date Range Filter
                sale['ordered_time_date'] = pd.to_datetime(sale['ordered_time_date'])
                min_date = sale['ordered_time_date'].min()  # Minimum date in your dataset (using 'sale_date' here)
                max_date = sale['ordered_time_date'].max()  # Maximum date in your dataset
                try:
                    start_date, end_date = st.date_input('Select Date Range:', [min_date, max_date])
                    sale_data_filtered = sale[
                        (sale['ordered_time_date'] >= pd.to_datetime(start_date)) & 
                        (sale['ordered_time_date'] < pd.to_datetime(end_date) + pd.Timedelta(days=1))
                    ]
                except:
                    st.warning('Please select end date as well')
                    
            product = get_ref('product')
            addon = get_ref('addon')
            customer = get_ref('customer')
            inventory = get_ref('inventory')
            usage_history = get_ref('usage_history')
            inv_quantity_branch = get_ref('inv_quantity_branch')
            inventory_full = pd.merge(inventory, inv_quantity_branch, on='inventory_id', how='inner')
            restock_history = get_ref('restock_history')  # Access the restock table
            inv_usage = get_ref('inv_usage')
            feedback = get_ref('feedback')
            # Create a filtered version of operatingcost_data based on branch and time period filters
            operatingcost = get_ref('operatingcost')
            operatingcost_data_filtered = operatingcost#[operatingcost['branch_id'] == branch_id]
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
            
                
    if selection == "Sales Analytics Dashboard":
        st.title("Sales Analytics Dashboard")
        try:
            st.markdown("<hr>", unsafe_allow_html=True)
            plot_best_worst_sellers(sale)
            st.markdown("<hr>", unsafe_allow_html=True)
            plot_total_sales(sale, order, period)
            st.markdown("<hr>", unsafe_allow_html=True)
            plot_sales_by_product(order)
            st.markdown("<hr>", unsafe_allow_html=True)
            plot_sales_by_time_of_day(sale_data_filtered)
            st.markdown("<hr>", unsafe_allow_html=True)
            calculate_profit(sale, inventory, inv_usage, period)
        except:
            st.warning('No sales data')
        

    elif selection == "Customer Analytics Dashboard":
        st.title("Customer Analytics Dashboard")
        try:
            # Filter customers using the filtered sales data
            filtered_customers = customer[customer['email'].isin(sale_data_filtered['email'])]
            # Pass the filtered data to the plotting functions
            st.markdown("<hr>", unsafe_allow_html=True)
            plot_customer_demographics(filtered_customers)
            st.markdown("<hr>", unsafe_allow_html=True)
            plot_order_frequency_history(sale_data_filtered)
        except:
            st.warning('No sales data')

    elif selection == "Inventory Analytics Dashboard":
        st.title("Inventory Analytics Dashboard")
        display_low_stock_products(inventory_full, branch_id)
        st.markdown("<hr>", unsafe_allow_html=True)
        calculate_inventory_turnover(inventory_full, usage_history, branch_id, period)


    elif selection == "Promotion and Discount Analytics":
        st.title("Promotion and Discount Analytics")
        # Use the already filtered sale_data_filtered
        # Add a radio button to toggle between Sales or Orders for Promotion Performance Chart
        metric = st.radio("Select Metric for Promotion Performance", ["Sales", "Orders"])
        try:
            # Plot Promotion Performance based on selected metric
            plot_promotion_performance(sale_data_filtered, metric)
            st.markdown("<hr>", unsafe_allow_html=True)
            # Plot Coupon Usage Over Time
            plot_coupon_usage_over_time(sale_data_filtered)
        except:
            st.warning('No sales data')

    elif selection == "Financial Analytics":
        st.title("Financial Analytics")
        try:
            st.markdown("<hr>", unsafe_allow_html=True)
            profit_margin_analysis(sale_data_filtered, inventory, inv_usage, period)
            st.markdown("<hr>", unsafe_allow_html=True)
            cost_analysis(operatingcost, operatingcost_data_filtered)
            st.markdown("<hr>", unsafe_allow_html=True)
            revenue_streams_analysis(sale_data_filtered, product)
        except:
            st.warning('No sales data')

    elif selection == "Operational Analytics":
        st.title("Operational Analytics")
        try:
            st.markdown("<hr>", unsafe_allow_html=True)
            customer_feedback_ratings(feedback, period, branch_id)
            st.markdown("<hr>", unsafe_allow_html=True)
            
        except:
            st.warning('No sales data')
        order_processing_times(sale_data_filtered)
    elif selection == "Order Monitoring Dashboard":
        try:
            order_monitoring_dashboard(sale)
        except:
            st.warning('No sales data')

    
try:
    branch = get_ref('branch')
    st.sidebar.title(branch[branch['branch_id'] == cookies.get('customer_id')]['branch_name'].values[0])
except:
    pass
    
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
