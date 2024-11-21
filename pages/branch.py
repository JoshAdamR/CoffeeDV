import streamlit as st

# Set session state for branch login
if "logged_in_branch" not in st.session_state:
    st.session_state.logged_in_branch = None

# App navigation
if st.session_state.logged_in_branch:
    st.sidebar.success(f"Logged in as: {st.session_state.logged_in_branch}")
    page = st.sidebar.selectbox("Navigate to", ["Inventory Management", "Coupon Management"])
    if page == "Inventory Management":
        from pages import inventory_page
        inventory_page.run()
    elif page == "Coupon Management":
        from pages import coupon_page
        coupon_page.run()
else:
    from pages import branch_login
    branch_login.run()
