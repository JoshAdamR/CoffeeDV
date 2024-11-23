from firebase_config import store  # Import Firestore client from config
import pandas as pd

# Initialize Firestore
db = store 

def get_ref(table):
    ref = db.collection(table)
    return pd.DataFrame([doc.to_dict() for doc in ref.stream()])

# Data loading function
def readdb():
    branch = get_ref('branch')
    product = get_ref('product')
    size = get_ref('size')
    milk_option = get_ref('milk_option')
    addon = get_ref('addon')
    coupon = get_ref('coupon')
    useracc = get_ref('useracc')
    temperature = get_ref('temperature')
    sugar_level = get_ref('sugar_level')
    return branch, product, size, milk_option, addon, coupon, useracc, temperature, sugar_level

branch_table, product_table, size_table, milk_option_table, addon_table, coupon_table, user_table, temperature_table, sugar_level_table = readdb()