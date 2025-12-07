from config import APPS_SCRIPT_URL,KEY_PATH
import requests
import json
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# הגדרות
COLLECTION_NAME = 'users'

def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(KEY_PATH)
        firebase_admin.initialize_app(cred)


def send_structured_data(name: str, inquiry: str, phone: str):
    """
    שולח נתונים מובנים (שם, פנייה, טלפון) ל-Apps Script.
    """
    if not APPS_SCRIPT_URL:
        print("ERROR: APPS_SCRIPT_URL אינו מוגדר.")
        return

    # בניית ה-Payload עם הנתונים המובנים
    payload = {
        "action": "write_structured", # פעולה חדשה שתציין ב-Apps Script
        "name": name,
        "inquiry": inquiry,
        "phone": phone
    }
    
    print(f"INFO: מנסה לשלוח נתונים לגיליון: {json.dumps(payload)}")

    try:
        response = requests.post(APPS_SCRIPT_URL, json=payload, timeout=10)
        print(f"SUCCESS: סטטוס תגובה: {response.status_code}")
        print(f"SUCCESS: גוף תגובה: {response.text}")
        
        if response.status_code == 200:
            print("✅ הכתיבה הושלמה בהצלחה (מנקודת מבט השרת).")
        else:
            print("❌ שגיאת שרת: ה-Apps Script החזיר קוד שאינו 200.")

    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: כשל שליחה ל-Apps Script: {e}")


def check_if_phone_number_exists(phone_number):

    initialize_firebase()
    db = firestore.client()
    
    # גישה ישירה למסמך לפי מספר הטלפון - הכי מהיר שיש
    doc_ref = db.collection(COLLECTION_NAME).document(phone_number)
    doc = doc_ref.get()
    
    if doc.exists:
        # המסמך קיים, נחזיר את המידע כ-Dictionary
        user_info = doc.to_dict()
        return True, user_info
    else:
        # המסמך לא קיים
        return False, None




def add_phone_number(phone_number, name, language):
    """
    יוצר משתמש חדש כאשר ה-ID של המסמך הוא מספר הטלפון.
    מתאים לשלב הרישום או הקמת המאגר.
    """
    initialize_firebase()
    db = firestore.client()
    
    # שימוש בטלפון בתור ה-ID של המסמך
    doc_ref = db.collection(COLLECTION_NAME).document(phone_number)
    
    # הנתונים שנשמור
    user_data = {
        'name': name,
        'language': language,
        'created_at': firestore.SERVER_TIMESTAMP # מומלץ לשמור תאריך יצירה
    }
    
    # set שומר או דורס את המידע הקיים
    doc_ref.set(user_data)
    print(f"המשתמש {name} עם טלפון {phone_number} נשמר בהצלחה.")



def new_request(phone_number, message_data):
    pass

if __name__ == "__main__":
    
    # 1. נניח שזה שלב הרישום - אנחנו מכניסים מידע למאגר
    # חשוב: וואטסאפ שולח מספרים בפורמט בינלאומי ללא פלוס (למשל 972)
    my_phone = "972501234567" 
    
    # הוספת משתמש לדוגמה (תריץ את זה פעם אחת כדי שיהיה מידע)
    add_phone_number(my_phone, "דני דניאל", "he")
    
    # 2. נניח שזה הקוד שרץ ב-AWS Lambda כשמתקבלת הודעה
    incoming_phone = "972501234567" # המספר שהגיע מה-Webhook
    
    exists, user_data = check_if_phone_number_exists(incoming_phone)
    
    if exists:
        print(f"משתמש מאומת! שם: {user_data['name']}, שפה: {user_data['language']}")
        # כאן הבוט ימשיך לעבוד בשפה של המשתמש
    else:
        print("משתמש לא רשום. נא להעביר לתהליך הרשמה.")