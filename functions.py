import streamlit as st
import pandas as pd
import re
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from streamlit_cookies_controller import CookieController, RemoveEmptyElementContainer
from streamlit_javascript import st_javascript
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle, Image
from io import BytesIO

from dbcoffee import customer_table, cart_table

from firebase_config import store  # Import Firestore client from config

cookies = CookieController()

# Create Firestore client
store = firestore.client()

def generate_id(prefix, collection_name, id_field):
    """
    Generate a new ID for a specified collection and ID field with a given prefix.

    Args:
        prefix (str): The prefix for the ID (e.g., "USER" or "CUST").
        collection_name (str): The Firestore collection name.
        id_field (str): The name of the field to look for IDs.

    Returns:
        str: The newly generated ID with the specified prefix.
    """
    collection_ref = store.collection(collection_name)
    documents = collection_ref.order_by(id_field).stream()
    max_id = 0
    for doc in documents:
        current_id = doc.to_dict().get(id_field, "")
        if current_id.startswith(prefix):
            num = int(current_id[len(prefix):])
            max_id = max(max_id, num)
    new_id = max_id + 1
    return f"{prefix}{new_id:03}"

# Example usage
# def generate_user_id():
#     return generate_id("USER", "useracc", "user_id")

def generate_customer_id():
    return generate_id("CUST", "useracc", "customer_id")    

def calculate_age(birthday):
    today = datetime.today()
    birth_date = datetime.strptime(birthday, "%Y-%m-%d")
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def add_entry(fullname, username, email, password, birthday, gender, datejoin, loyalty_point):
    # user_id = generate_user_id()
    customer_id = generate_customer_id()
    age = calculate_age(birthday)
    user_entry = {
        # "user_id": user_id,
        "username": username,
        "email": email,
        "password": password,  # Consider hashing the password before storing
        "role": "customer",
        "customer_id": customer_id,
        "fullname": fullname
    }
    cust_entry = {
        # "user_id": user_id,
        "birthday": birthday,
        "gender": gender,
        "age": age,
        "customer_id": customer_id,
        "customer_name": fullname,
        "join_date": datejoin,
        "loyalty_points": loyalty_point,
        "email": email,
        "fullname": fullname
    }
    store.collection("useracc").document(email).set(user_entry)
    store.collection("customer").document(email).set(cust_entry)

# Function to fetch all entries from Firestore
def get_entries(table):
    users_ref = store.collection(table)
    docs = users_ref.stream()
    return [doc.to_dict() for doc in docs]

# Function to check if email is valid
def is_valid_email(email):
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(regex, email) is not None and email.endswith('.com')

# Function to check if password is valid
def is_valid_password(password):
    return (len(password) >= 8 and
            any(char.isupper() for char in password) and
            any(char.isdigit() for char in password) and
            any(not char.isalnum() for char in password))

# Function to validate the name
def is_valid_name(name: str) -> bool:
    # Convert to uppercase
    name = name.upper()
    
    # Check if the name contains only alphabets and spaces
    if re.match("^[A-Za-z\s]+$", name):
        return name
    else:
        return None

# Function to check for duplicate emails in Firestore
def email_exists(email):
    user_ref = store.collection("useracc").document(email)
    return user_ref.get().exists

# Function to fetch user by email and password from Firestore
def fetch_user(email, password):
    users_ref = store.collection("useracc")
    query = users_ref.where("email", "==", email).where("password", "==", password).limit(1)
    user = query.get()
    return user[0].to_dict() if user else None

def fetch_user_by_id(table, email):
    user_ref = store.collection(table).document(email)
    user = user_ref.get()
    if user.exists:
        return user.to_dict()
    else:
        return None


def getCookies(email_input):
    """
    Fetch cookies for the user with the provided email. If logged in successfully, store user data in cookies.

    Args:
        email_input (str): The email entered in the email input box.

    Returns:
        dict or None: The user data if found, or None if not found.
    """
    # Fetch user by email from Firestore
    user_data = fetch_user_by_id("useracc",email_input)
    cust_data = fetch_user_by_id("customer",email_input)

    if user_data:
        # Store user data in cookies
        cookies.set("status", 'true')
        cookies.set("email", user_data.get("email"))
        cookies.set("username", user_data.get("username"))
        cookies.set("birthday", cust_data.get("birthday"))
        cookies.set("gender", cust_data.get("gender"))
        cookies.set("age", cust_data.get("age"))
        cookies.set("role", user_data.get("role"))
        cookies.set("password", user_data.get("password"))
        cookies.set("fullname", user_data.get("fullname"))
        cookies.set("customer_id", user_data.get("customer_id"))

        RemoveEmptyElementContainer()
        
        return user_data
    else:
        return None

def create_pdf(entry, cart_data):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    
    # Header Section
    pdf.setFont("Helvetica-Bold", 20)
    pdf.setFillColor(colors.HexColor("#4B6584"))
    pdf.drawString(50, 750, "🫘 PyBean Invoice")
    
    pdf.setFont("Helvetica", 12)
    pdf.setFillColor(colors.black)
    pdf.drawString(50, 730, f"Date: {entry.get('date', 'N/A')}")
    pdf.drawString(475, 730, f"Invoice ID: {entry.get('invoice_id', 'N/A')}")

    # Company Information
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, 700, "PyBean Company")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 685, "Universiti Teknologi PETRONAS")
    pdf.drawString(50, 670, "32610 Seri Iskandar, Perak Darul Ridzuan, Malaysia")
    pdf.drawString(50, 655, "Email: support@pybean.com")

    # User Details
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, 630, "Customer Details:")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 615, f"Customer ID: {entry.get('customer_id')}")
    pdf.drawString(50, 600, f"Name: {entry.get('name', 'N/A')}")
    pdf.drawString(50, 585, f"Email: {entry.get('email', 'N/A')}")  
    
    # Divider Line
    pdf.line(50, 560, 550, 560)

    # Invoice Table
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, 540, "Items:")
    
    # Add table data
    data = [["Item", "Description", "Qty", "Price"]]
    for item in cart_data:
        # Format price to two decimals
        formatted_price = "{:.2f}".format(item["price"])
        # Get addons as a list and display vertically
        formatted_addons = ', '.join(item["addons"]) if item.get("addons") else "None"
        formatted_description = item["description"] + "\n" + formatted_addons
        data.append([item["item"], formatted_description, item["quantity"], formatted_price])
    
    # Calculate total price and format it to two decimals
    total_price = sum(item["quantity"] * item["price"] for item in cart_data)
    formatted_total_price = "{:.2f}".format(total_price)

    # Add total row
    data.append(["", "", "Total (MYR)", formatted_total_price])
    
    # Add table style
    table = Table(data, colWidths=[80, 360, 70, 40])  # Ensure enough width for addons column
    style = TableStyle([ 
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4B6584")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Ensure vertical alignment in cells
    ])
    table.setStyle(style)

    # Calculate the total width of the table (sum of column widths)
    table_width = sum([80, 360, 70, 40])  # The values in colWidths for each column

    # Estimate row height (you can adjust this depending on font size and padding)
    row_height = 20  # Approximate row height for each row (adjust if needed)
    table_height = len(data) * row_height  # Height based on the number of rows

    # Calculate horizontal centering
    x_position = (612 - table_width) / 2  # 612 is the width of the page (letter size)

    # Dynamically adjust y_position based on the number of rows
    initial_y_position = 490  # Starting Y position below "Items:" label
    y_position = initial_y_position - table_height  # Move the table down by its height

    # Place table (centered horizontally and adjusted vertically)
    table.wrapOn(pdf, 50, 200)
    table.drawOn(pdf, x_position, y_position)
    
    # Footer Section (Centered)
    footer_text1 = "Thank you for choosing PyBean!"
    footer_text2 = "For queries, contact us at support@pybean.com."
    
    # Calculate the X position to center the text
    footer_text_width1 = pdf.stringWidth(footer_text1, "Helvetica-Oblique", 10)
    footer_text_width2 = pdf.stringWidth(footer_text2, "Helvetica-Oblique", 10)
    
    # Center both lines horizontally
    x_position1 = (612 - footer_text_width1) / 2
    x_position2 = (612 - footer_text_width2) / 2

    pdf.setFont("Helvetica-Oblique", 10)
    pdf.drawString(x_position1, 50, footer_text1)
    pdf.drawString(x_position2, 35, footer_text2)
    
    pdf.save()
    buffer.seek(0)
    return buffer


def fetch_cart_data(invoice_id):
    # Reference the Firestore collection
    cart_collection = store.collection("cart")

    # Query the collection for the given invoice ID
    query = cart_collection.where("invoice_id", "==", invoice_id).stream()

    # Process the query results
    cart_items = []
    for doc in query:
        data = doc.to_dict()

        # Create a description by combining milk_type, sugar_level, temperature, and addons
        description = (
            f"{data.get('milk_type', 'N/A')}, "
            f"{data.get('sugar_level', 'N/A')}, "
            f"{data.get('temperature', 'N/A')}"
        )

        # Add the processed item to the cart_items list
        cart_items.append({
            "item": data.get("name", "Unknown Item"),
            "description": description,
            "addons": data.get("addons", 0),
            "quantity": data.get("quantity", 0),
            "price": data.get("price_after_discount", 0.0)
        })

    return cart_items