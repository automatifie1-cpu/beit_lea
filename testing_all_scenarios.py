import json
import time
from firebase_admin import firestore
# ייבוא הפונקציות מהקבצים שלך
from lambda_function import lambda_handler
from google_sheets_utils import initialize_firebase, COLLECTION_NAME

# ==========================================
# 1. הגדרת נתוני בדיקה (Test Cases)
# ==========================================
TEST_USERS = [
    {
        "phone": "972500000001", 
        "name": "ישראל ישראלי", 
        "language": "he", 
        "msg": "בדיקה בעברית",
        "desc": "משתמש רשום - עברית"
    },
    {
        "phone": "15551234567",  
        "name": "John Doe", 
        "language": "en", 
        "msg": "Testing in English",
        "desc": "משתמש רשום - אנגלית"
    },
    {
        "phone": "33612345678",  
        "name": "Pierre Cohen", 
        "language": "fr", 
        "msg": "Test en Français",
        "desc": "משתמש רשום - צרפתית"
    }
]

UNKNOWN_USER = {
    "phone": "99999999999", 
    "msg": "מי אני?", 
    "desc": "משתמש לא רשום (אמור לקבל הודעת שגיאה)"
}

# ==========================================
# 2. פונקציות עזר לבדיקה
# ==========================================

def seed_database():
    """
    מכניס את המשתמשים הרשומים ל-Firestore כדי שהבדיקה תעבוד
    """
    print("\n🌱 --- מזין נתונים ל-Firestore (Seeding) ---")
    initialize_firebase()
    db = firestore.client()
    
    for user in TEST_USERS:
        doc_ref = db.collection(COLLECTION_NAME).document(user['phone'])
        doc_ref.set({
            'name': user['name'],
            'language': user['language'],
            'created_at': firestore.SERVER_TIMESTAMP
        })
        print(f"✅ נוצר/עודכן משתמש: {user['name']} ({user['language']}) - {user['phone']}")
    print("--- סיום הזנת נתונים ---\n")

def create_mock_whatsapp_event(phone, message_text):
    """
    יוצר את מבנה ה-JSON שוואטסאפ שולחים
    """
    body_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "contacts": [{"profile": {"name": "Tester"}, "wa_id": phone}],
                    "messages": [{
                        "from": phone,
                        "id": "wamid.TEST",
                        "text": {"body": message_text},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    return {
        "httpMethod": "POST",
        "body": json.dumps(body_payload)
    }

# ==========================================
# 3. הרצת הבדיקות
# ==========================================

def run_tests():
    # קודם כל - מכניסים נתונים למסד
    seed_database()
    
    print("🚀 --- מתחיל הרצת תרחישים ---")
    
    # בדיקת כל המשתמשים הרשומים
    for user in TEST_USERS:
        print(f"\n🧪 בודק תרחיש: {user['desc']}")
        event = create_mock_whatsapp_event(user['phone'], user['msg'])
        
        # הרצת הלמבדה
        response = lambda_handler(event, None)
        
        # הדפסת התוצאה
        print(f"📩 הודעה נשלחה: '{user['msg']}'")
        print(f"⚙️ סטטוס למבדה: {response['statusCode']}")
        print(f"📄 גוף תגובה: {response['body']}")
        
        # השהייה קטנה כדי לא להעמיס על הלוגים
        time.sleep(1)

    # בדיקת משתמש לא רשום
    print(f"\n🧪 בודק תרחיש: {UNKNOWN_USER['desc']}")
    event = create_mock_whatsapp_event(UNKNOWN_USER['phone'], UNKNOWN_USER['msg'])
    response = lambda_handler(event, None)
    print(f"📩 הודעה נשלחה: '{UNKNOWN_USER['msg']}'")
    print(f"⚙️ סטטוס למבדה: {response['statusCode']}")
    
    print("\n🏁 --- סיום כל הבדיקות ---")

if __name__ == "__main__":
    run_tests()