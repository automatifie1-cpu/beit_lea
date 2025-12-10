import json
import traceback
import config
from whatsApp import (
    extract_message_info, 
    send_message, 
    send_contact
)
from local_storage import check_user_local
from google_sheets_utils import send_structured_data

# הגדרות שפה
RESPONSES = {
    "he": {
        "welcome": "שלום {name}, איך אפשר לעזור?",
        "not_found_msg": "שלום, המספר שלך אינו רשום במערכת שלנו.",
        "not_found_policy": " אנא עיין בתקנון שלנו:",
        "contact_person_name": "סול - איש קשר לבירורים",
        "thank_you": "תודה על פנייתך, העניין נרשם לטיפול.",
    },
    "en": {
        "welcome": "Hello {name}, how can I assist you?",
        "not_found_msg": "Hi, your number is not registered in our system.",
        "not_found_policy": " Please see our terms and conditions:",
        "contact_person_name": "Sol - Inquiry Contact Person",
        "thank_you": "Thank you for your inquiry, it has been logged.",
    },
    "default": "he"
}

def lambda_handler(event, context):
    print("🚀 Lambda Started")
    
    # --- תיקון קריטי לזיהוי גרסת API Gateway (V1 vs V2) ---
    method = event.get("httpMethod") # ניסיון גרסה 1
    if not method:
        # ניסיון גרסה 2 (לפי הלוג ששלחת)
        method = event.get("requestContext", {}).get("http", {}).get("method")
    
    print(f"👉 Method Identified: {method}")

    # --- 1. אימות Webhook (GET) ---
    if method == "GET":
        params = event.get("queryStringParameters") or {}
        if params.get("hub.verify_token") == config.VERIFY_TOKEN:
            return {"statusCode": 200, "body": params.get("hub.challenge")}
        return {"statusCode": 403, "body": "Forbidden"}

    # --- 2. עיבוד הודעה (POST) ---
    if method == "POST":
        try:
            # חילוץ הגוף (Body)
            raw_body = event.get("body", "{}")
            body_data = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
            
            # חילוץ נתונים מוואטסאפ
            from_number, message_text, msg_id = extract_message_info(body_data)
            
            if not from_number or not message_text:
                print("⚠️ הודעה ללא טקסט או מספר (אולי סטטוס/תמונה)")
                return {"statusCode": 200, "body": "Event processed"}
            
            print(f"📩 הודעה נכנסת מ-{from_number}: {message_text}")

            # ============================================
            # שלב א': בדיקה בקובץ JSON מקומי
            # ============================================
            exists, user_data = check_user_local(from_number)
            
            user_name = "חבר"
            user_lang = RESPONSES["default"]
            
            if exists and user_data:
                user_name = user_data.get("name") or "חבר"
                user_lang = user_data.get("language") or RESPONSES["default"]

            lang_res = RESPONSES.get(user_lang, RESPONSES["default"])
            
            # ============================================
            # שלב ב': שליחת תגובה
            # ============================================
            if exists:
                # --- משתמש רשום ---
                print(f"✅ משתמש רשום: {user_name}")
                welcome_msg = lang_res["welcome"].format(name=user_name)
                send_message(from_number, welcome_msg)
                
                # תיעוד בגיליון
                send_structured_data(user_name, message_text, from_number)
                
                send_message(from_number, lang_res["thank_you"])
                
            else:
                # --- משתמש לא רשום ---
                print(f"❌ משתמש לא רשום: {from_number}")
                send_message(from_number, lang_res["not_found_msg"])
                
                policy_text = lang_res["not_found_policy"]
                policy_url = getattr(config, 'BEIT_LEAH_URL', 'https://example.com')
                send_message(from_number, f"{policy_text}\n{policy_url}")
                
                contact_phone = getattr(config, 'CONTACT_PHONE', "0532787416")
                send_contact(from_number, lang_res["contact_person_name"], contact_phone) 

        except Exception as e:
            print(f"🔥 FATAL ERROR: {e}")
            traceback.print_exc()
            return {"statusCode": 500, "body": "Internal Error"}
            
        return {"statusCode": 200, "body": "EVENT_PROCESSED"}
    
    return {"statusCode": 404, "body": "Method Not Allowed"}