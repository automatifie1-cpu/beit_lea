import json
import os

USERS_DB = {}

def load_users():
    global USERS_DB
    try:
        # קבלת הנתיב המוחלט של התיקייה שבה הקובץ הזה נמצא
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'users.json')
        
        print(f"📂 מנסה לטעון את הקובץ מ: {json_path}") # הדפסה לדיבאג

        if not os.path.exists(json_path):
            print(f"❌ הקובץ users.json לא נמצא בנתיב המצופה!")
            USERS_DB = {}
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            USERS_DB = json.load(f)
        print(f"✅ Users loaded successfully. Total: {len(USERS_DB)}")
        
    except Exception as e:
        print(f"❌ Error loading users.json: {e}")
        USERS_DB = {}

# טעינה ראשונית
load_users()

def check_user_local(phone_number):
    if not USERS_DB:
        load_users()
    
    user_data = USERS_DB.get(phone_number)
    
    if user_data:
        print(f"✅ User found locally: {user_data.get('name')}")
        return True, user_data
    else:
        print(f"❌ User {phone_number} not found in local JSON.")
        return False, None