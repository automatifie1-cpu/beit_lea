from config import APPS_SCRIPT_URL
import requests
import json
# הגדרות
COLLECTION_NAME = 'users'



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


def check_user_in_sheets(phone_number):
    """
    שולח בקשה ל-Apps Script לבדוק אם המשתמש קיים
    ומחזיר את נתוני המשתמש (שם ושפה) אם נמצא.
    """
    url = getattr(config, 'APPS_SCRIPT_URL', None)
    if not url:
        print("ERROR: APPS_SCRIPT_URL אינו מוגדר.")
        return False, None

    # Payload לקריאת נתונים
    payload = {
        "action": "read_user", # פעולה חדשה שנצטרך להוסיף ב-Apps Script
        "phone": phone_number
    }
    
    print(f"INFO: מנסה לקרוא נתונים למספר {phone_number} מגיליון")

    try:
        # שליחת בקשת POST עם הגדרת Timeout בטוחה
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status() # יזרוק שגיאה אם הסטטוס אינו 200
        
        # המידע המוחזר מה-Apps Script
        sheet_data = response.json() 
        
        if sheet_data.get("status") == "not_found":
            return False, None # המשתמש לא נמצא
        
        # אם קיבלנו שם ושפה, המשתמש קיים
        return True, sheet_data

    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: כשל בקריאה מ-Apps Script: {e}")
        return False, None


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
    
    exists, user_data = check_user_in_sheets(incoming_phone)
    
    if exists:
        print(f"משתמש מאומת! שם: {user_data['name']}, שפה: {user_data['language']}")
        # כאן הבוט ימשיך לעבוד בשפה של המשתמש
    else:
        print("משתמש לא רשום. נא להעביר לתהליך הרשמה.")