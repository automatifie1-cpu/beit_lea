import json
import traceback
import config
from whatsApp import (
    extract_message_info, 
    send_message, 
    send_contact
)
# הייבוא החדש והפשוט
from local_storage import check_user_local
# רק לכתיבת לוגים (לא קריטי לאימות)
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
    "fr": {
        "welcome": "Bonjour {name}, comment puis-je vous aider?",
        "not_found_msg": "Bonjour, votre numéro n'est pas enregistré dans notre système.",
        "not_found_policy": " Veuillez consulter nos conditions générales:",
        "contact_person_name": "Sol - Personne de contact pour les demandes",
        "thank_you": "Merci de nous avoir contactés, votre demande a été enregistrée.",
    },
    "default": "he"
}

def lambda_handler(event, context):
    # בדיקת Webhook (GET)
    method = event.get("httpMethod", event.get("requestContext", {}).get("http", {}).get("method", ""))
    if method == "GET":
        params = event.get("queryStringParameters") or {}
        if params.get("hub.verify_token") == config.VERIFY_TOKEN:
            return {"statusCode": 200, "body": params.get("hub.challenge")}
        return {"statusCode": 403, "body": "Forbidden"}

    # עיבוד הודעה (POST)
    if method == "POST":
        try:
            raw_body = event.get("body", "{}")
            body_data = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
            
            from_number, message_text, msg_id = extract_message_info(body_data)
            
            if not from_number or not message_text:
                return {"statusCode": 200, "body": "No text message"}
            
            # ============================================
            # שלב 1: בדיקה בקובץ JSON מקומי (מהיר בטירוף)
            # ============================================
            exists, user_data = check_user_local(from_number)
            
            user_name = "חבר"
            user_lang = RESPONSES["default"]
            
            if exists and user_data:
                user_name = user_data.get("name") or "חבר"
                user_lang = user_data.get("language") or RESPONSES["default"]

            lang_res = RESPONSES.get(user_lang, RESPONSES["default"])
            
            # ============================================
            # שלב 2: לוגיקת שליחה
            # ============================================
            if exists:
                # משתמש רשום
                welcome_msg = lang_res["welcome"].format(name=user_name)
                send_message(from_number, welcome_msg)
                
                # עדיין מתעדים בגיליון (אופציונלי, לא תוקע את הבוט אם נכשל)
                send_structured_data(user_name, message_text, from_number)
                
                send_message(from_number, lang_res["thank_you"])
                
            else:
                # משתמש לא רשום
                send_message(from_number, lang_res["not_found_msg"])
                
                policy_text = lang_res["not_found_policy"]
                send_message(from_number, f"{policy_text}\n{config.BEIT_LEAH_URL}")
                
                contact_phone = "0515886650"  # החלף למספר האמיתי
                send_contact(from_number, lang_res["contact_person_name"], contact_phone) 
                
                send_structured_data("לא רשום", message_text, from_number)

        except Exception as e:
            print(f"FATAL ERROR: {e}")
            traceback.print_exc()
            return {"statusCode": 200, "body": "Error processed"}
            
        return {"statusCode": 200, "body": "EVENT_PROCESSED"}
    
    return {"statusCode": 404, "body": "Not Found"}