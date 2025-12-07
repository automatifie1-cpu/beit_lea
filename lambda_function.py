import json
from typing import Dict, Any, Tuple, Optional
import traceback
import config
# יבוא פונקציות מקבצי עזר
from whatsApp import (
    extract_message_info, 
    send_message, 
    send_contact
)
from google_sheets_utils import send_structured_data, check_if_phone_number_exists

# =======================================================================
# 1. הגדרות תגובות רב-לשוניות
# =======================================================================

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
    "fr": {
        "welcome": "Bonjour {name}, comment puis-je vous aider?",
        "not_found_msg": "Bonjour, votre numéro n'est pas enregistré dans notre système.",
        "not_found_policy": " Veuillez consulter nos conditions générales:",
        "contact_person_name": "Sol - Personne de contact pour les demandes",
        "thank_you": "Merci de nous avoir contactés, votre demande a été enregistrée.",
    },
    # ... (שאר השפות שהוספת: ru, es, de) ...
    "default": "he"
}

# =======================================================================
# 🚀 3. פונקציית ה-Lambda Handler
# =======================================================================

def lambda_handler(event, context):
    
    # ניתוח בקשת HTTP Method (מתוך API Gateway)
    method = event.get("httpMethod", event.get("requestContext", {}).get("http", {}).get("method", ""))

    # -----------------------------
    # א. GET - אימות Webhook
    # -----------------------------
    if method == "GET":
        params = event.get("queryStringParameters") or {}
        token = params.get("hub.verify_token")
        
        if token == config.VERIFY_TOKEN:
            return {"statusCode": 200, "body": params.get("hub.challenge")}
        return {"statusCode": 403, "body": "Forbidden"}

    # -----------------------------
    # ב. POST - עיבוד הודעות
    # -----------------------------
    if method == "POST":
        try:
            raw_body = event.get("body", "{}")
            body_data = json.loads(raw_body)
            
            from_number, message_text, msg_id = extract_message_info(body_data)
            
            if not from_number or not message_text:
                return {"statusCode": 200, "body": "Event processed, no text message found"}
            
            # שלב 1: בדיקת קיום משתמש ב-DB
            info = check_if_phone_number_exists(from_number)
            
            if info[0]:
                # ===================================================
                # תרחיש 1: משתמש קיים (רשום)
                # ===================================================
                infoDict = info[1]
                user_name, user_lang = infoDict.get("name"), infoDict.get("language")

                # הגדרת שפת התגובה
                lang_code = user_lang if user_lang in RESPONSES else RESPONSES["default"]
                lang_res = RESPONSES[lang_code]
                # 1. שליחת הודעת ברוך הבא בשפה של המשתמש
                welcome_msg = lang_res["welcome"].format(name=user_name)
                send_message(from_number, welcome_msg)
                
                # 2. רישום הפנייה ל-Google Sheets (הפנייה = תוכן ההודעה)
                send_structured_data(user_name, message_text, from_number)
                
                # 3. (אופציונלי) שליחת תודה
                send_message(from_number, lang_res["thank_you"])
                
            else:
                # ===================================================
                # תרחיש 2: משתמש לא קיים (לא רשום)
                # ===================================================
                
                # הגדרת שפת ברירת מחדל לעברית עבור משתמשים לא רשומים
                lang_code = RESPONSES["default"]
                lang_res = RESPONSES[lang_code]
                
                # 1. הודעת כשל (לא רשום)
                fail_msg = lang_res["not_found_msg"]
                send_message(from_number, fail_msg)
                
                # 2. שליחת קישור התקנון
                policy_text = lang_res["not_found_policy"]
                send_message(from_number, policy_text+"\n"+config.BEIT_LEAH_URL)
                
                # 3. שליחת איש קשר (כרטיס VCard)
                contact_name = lang_res["contact_person_name"]
                # 💡 משתמשים במספר בוט/איש קשר מהקונפיג
                send_contact(from_number, contact_name, "0532787416") 


        except Exception as e:
            print(f"FATAL ERROR in POST processing: {str(e)}")
            # במקרה של שגיאה קריטית, עדיין יש להחזיר 200 לוואטסאפ
            
        return {"statusCode": 200, "body": "EVENT_PROCESSED"}

    return {"statusCode": 404, "body": "Not Found"}