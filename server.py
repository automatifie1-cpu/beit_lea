import firebase_admin
from firebase_admin import credentials, firestore
from typing import Dict, Any, Tuple, Optional
import os
import time

# ⚠️ שם קובץ מפתח השירות שלך
SERVICE_ACCOUNT_KEY_FILE = "beit-leah-soldiers-firebase-adminsdk-fbsvc-6f3f1f15fb.json"
db: Optional[firestore.client] = None 

# ==========================================================
# 1. אתחול חיבור ל-Firebase (חסין ריצה חוזרת)
# ==========================================================

try:
    if not os.path.exists(SERVICE_ACCOUNT_KEY_FILE):
        raise FileNotFoundError(f"קובץ המפתח חסר: {SERVICE_ACCOUNT_KEY_FILE}.")

    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_FILE)
    
    # 💥 התיקון: בדיקה אם האפליקציה כבר קיימת
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, name='user_ops_app')
        print("✅ Firebase initialized successfully (New session).")
    else:
        print("✅ Firebase connection already active. Reusing existing DB instance.")
    
    db = firestore.client()
    
except FileNotFoundError as fnfe:
    print(f"❌ שגיאת קובץ: {fnfe}")
except Exception as e:
    print(f"❌ שגיאת אתחול Firebase קריטית: {str(e)}")
    db = None 

# ==========================================================
# 2. פונקציית הכתיבה לדאטאבייס
# ==========================================================
def add_new_user_to_firebase(
    phone_number: str, 
    name: str, 
    country: str, 
    language: str
) -> Tuple[bool, str]:
    
    if db is None:
        return False, "שגיאה: חיבור ה-Firestore אינו פעיל."

    if not phone_number or not name:
        return False, "מספר טלפון ושם הם שדות חובה."
    
    normalized_phone = phone_number.strip().replace(" ", "")
    if not normalized_phone.startswith('+'):
         return False, "מספר הטלפון חייב להיות בפורמט בינלאומי (E.164)."

    user_data = {
        "name": name,
        "country": country,
        "language": language,
        "first_contact": firestore.SERVER_TIMESTAMP,
        "last_activity": firestore.SERVER_TIMESTAMP,
        "phone_number": normalized_phone
    }

    try:
        user_ref = db.collection('users').document(normalized_phone)
        user_ref.set(user_data) 
        return True, f"משתמש {name} נוסף/עודכן בהצלחה ב-Firestore."
        
    except Exception as e:
        return False, f"❌ כשל בכתיבה ל-Firestore: {str(e)}"

# ==========================================================
# 3. פונקציית הקריאה/חיפוש לפי שם
# ==========================================================
def get_phone_by_name(user_name: str) -> Optional[str]:
    """
    מחפש משתמש לפי שם ב-Firestore ומחזיר את מספר הטלפון שלו.
    """
    if db is None:
        print("ERROR: Firestore connection is not initialized.")
        return None

    if not user_name:
        return None

    try:
        # יצירת שאילתה: חפש במסמכים שבהם השדה 'name' שווה ל-user_name
        users_ref = db.collection('users')
        query = users_ref.where('name', '==', user_name).limit(1)

        results = query.get()

        if results:
            doc = results[0]
            if doc.exists:
                data = doc.to_dict()
                return data.get('phone_number')
        
        return None
        
    except Exception as e:
        print(f"ERROR: כשל בביצוע שאילתת Firestore: {str(e)}")
        return None

# ==========================================================
# 🧪 4. דוגמת שימוש (כולל קריאה בסוף)
# ==========================================================
if __name__ == '__main__':
    
    USER_TO_SEARCH = "משה כהן"
    
    print("-" * 50)
    print(f"--- בדיקת כתיבה וקריאה ל-Firestore: {time.strftime('%H:%M:%S')} ---")
    
    # 4.1. כתיבה: יצירה או עדכון של משתמש
    print(f"\n--- כתיבה: הוספת {USER_TO_SEARCH} ---")
    success, msg = add_new_user_to_firebase(
        phone_number="+972541234567",
        name=USER_TO_SEARCH,
        country="ישראל",
        language="he"
    )
    print(f"תוצאת כתיבה: {msg}")

    # 4.2. המתנה קצרה לוודא שהכתיבה התבצעה (לא תמיד נחוץ)
    # time.sleep(1)
    
    # 4.3. קריאה: ניסיון לקבל את המספר של המשתמש שיצרנו
    print(f"\n--- קריאה: חיפוש מספר טלפון של {USER_TO_SEARCH} ---")
    retrieved_phone = get_phone_by_name(USER_TO_SEARCH)
    
    if retrieved_phone:
        print(f"✅ הצלחה! מספר הטלפון של {USER_TO_SEARCH} הוא: {retrieved_phone}")
    else:
        print(f"❌ כישלון: לא נמצא מספר טלפון עבור {USER_TO_SEARCH}")
        
    print("-" * 50)