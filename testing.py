import json
import time
import sys
import os

# הוספת הנתיב הנוכחי כדי שפייתון ימצא את הקבצים שלך
sys.path.append(os.getcwd())

# ייבוא הפונקציות שלך
try:
    from local_storage import check_user_local, USERS_DB
    from lambda_function import lambda_handler
    import config
    print("✅ כל הספריות נטענו בהצלחה.\n")
except ImportError as e:
    print(f"❌ שגיאה בטעינת ספריות: {e}")
    print("ודא שכל הקבצים (local_storage.py, lambda_function.py, config.py) באותה תיקייה.")
    sys.exit(1)

# ==========================================
# הגדרות לבדיקה
# ==========================================
# שנה את המספר הזה למספר שקיים אצלך ב-users.json!
REGISTERED_PHONE = "972501234567" 
UNREGISTERED_PHONE = "972509999999"

def create_mock_event(phone, text):
    """יוצר אירוע דמה שמחקה את וואטסאפ"""
    return {
        "httpMethod": "POST",
        "body": json.dumps({
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "messages": [{
                            "from": phone,
                            "id": "wamid.TEST",
                            "text": {"body": text},
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
    }

# ==========================================
# בדיקה 1: בדיקת קובץ JSON (הכי בסיסי)
# ==========================================
print("🔍 --- בדיקה 1: טעינת משתמשים (local_storage) ---")
if not USERS_DB:
    print("❌ שגיאה: מסד הנתונים ריק! בדוק את users.json")
else:
    print(f"✅ נטענו {len(USERS_DB)} משתמשים בהצלחה.")
    
    # בדיקת משתמש קיים
    exists, user = check_user_local(REGISTERED_PHONE)
    if exists:
        print(f"✅ זיהוי משתמש קיים עובד: {user['name']}")
    else:
        print(f"❌ כישלון: לא מצא את המספר {REGISTERED_PHONE} ב-users.json")
        print("   -> טיפ: ודא שהמספר בקובץ שמור בלי '+' ובלי מקפים.")

print("-" * 50)

# ==========================================
# בדיקה 2: הרצה מלאה (תרחיש משתמש רשום)
# ==========================================
print(f"\n🚀 --- בדיקה 2: סימולציה מלאה - משתמש רשום ({REGISTERED_PHONE}) ---")
event = create_mock_event(REGISTERED_PHONE, "היי בוט, זו בדיקה")
response = lambda_handler(event, None)

print(f"Status: {response['statusCode']}")
print(f"Body: {response['body']}")

if response['statusCode'] == 200:
    print("✅ הלמבדה רצה בהצלחה.")
    print("   (אם ה-Config תקין, היית אמור לקבל הודעת 'ברוך הבא' לוואטסאפ שלך)")
    print("   (וגם לראות שורה חדשה ב-Google Sheets)")
else:
    print("❌ משהו השתבש בריצה.")

print("-" * 50)

# ==========================================
# בדיקה 3: הרצה מלאה (תרחיש משתמש לא רשום)
# ==========================================
print(f"\n🚀 --- בדיקה 3: סימולציה מלאה - לא רשום ({UNREGISTERED_PHONE}) ---")
event = create_mock_event(UNREGISTERED_PHONE, "אני חדש פה")
response = lambda_handler(event, None)

print(f"Status: {response['statusCode']}")
if response['statusCode'] == 200:
    print("✅ הלמבדה זיהתה שזה משתמש לא רשום.")
    print("   (היית אמור לקבל הודעת שגיאה + איש קשר לוואטסאפ)")
else:
    print("❌ שגיאה.")

print("\n🏁 סיום בדיקות.")