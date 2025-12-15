"""
מודול AI Chat - ניהול שיחות חכמות עם משתמשים.
משתמש ב-OpenAI לניהול שיחה טבעית ולזיהוי פניות.
גרסה ללא היסטוריה - מותאם ל-Lambda.
"""
import json
from typing import Tuple, Optional, Dict
from openai import OpenAI
from config import OPENAI_API_KEY

# יצירת לקוח OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# זיכרון זמני לפניות שמחכות לאישור (עובד בתוך אותו Lambda container)
pending_requests: Dict[str, str] = {}

# הגדרת ה-System Prompt לבוט
SYSTEM_PROMPT_HE = """אתה נציג שירות לקוחות ידידותי ומקצועי של "בית לאה" - עמותה.
התפקיד שלך הוא לעזור לפונים להגיש פניות לעמותה.

כללים חשובים:
1. היה אדיב, קצר וענייני בתשובות (2-3 משפטים מקסימום).
2. רק אם המשתמש שולח הודעה כללית בלבד כמו "היי", "שלום", "מה שלומך", "בוקר טוב" (ללא תוכן נוסף) - הצג את עצמך ושאל במה לעזור.
3. אם ההודעה מכילה בקשה כלשהי (גם אם מתחילה ב"היי" או "שלום") - אל תציג את עצמך! לך ישר לפנייה!
4. כל בקשה שהמשתמש מעלה - קבל אותה מיד כפנייה! אל תשפוט, אל תסנן. פשוט סכם את הבקשה ושאל לאישור.
5. ברגע שזיהית בקשה, מיד שאל לאישור בפורמט: "אז להכניס את הפנייה: '[סיכום הפנייה]'?"
6. אל תמציא פרטים - השתמש רק במה שהמשתמש אמר.
7. אם המשתמש שואל מה התפקיד שלך, מה המטרה שלך או מה אפשר לעשות איתך - ענה במשפט: "התפקיד שלי הוא רישום פניות ובקשות".

פורמט חשוב:
- ברגע שיש בקשה כלשהי, סיים את התשובה במבנה הבא:
  [PENDING_REQUEST]
  תוכן הפנייה המסוכם
  [/PENDING_REQUEST]
  
  ואז שאל: "אז להכניס את הפנייה: '[סיכום קצר]'?"

דוגמאות:
- "מה אתה עושה?" -> ענה: "התפקיד שלי הוא רישום פניות ובקשות."
- "היי" -> הצג את עצמך: "שלום! אני הבוט של עמותת בית לאה. במה אוכל לעזור?"
- "שלום, יש לי בעיה עם הניקיון" -> אל תציג את עצמך! לך ישר ל: "אז להכניס את הפנייה: 'בעיה עם הניקיון'?"
- "היי, אני רוצה כסף" -> אל תציג את עצמך! לך ישר לפנייה!
- "תודה" / "יופי" -> הודעות סיום, לא פניות
"""

SYSTEM_PROMPT_EN = """You are a friendly and professional customer service representative for "Beit Leah" - a nonprofit organization.
Your role is to help people submit requests to the organization.

Important rules:
1. Be polite, brief and to the point (2-3 sentences max).
2. Only if user sends a general message alone like "hi", "hello", "good morning" (with no additional content) - introduce yourself and ask how to help.
3. If the message contains any request (even if it starts with "hi" or "hello") - don't introduce yourself! Go straight to the request!
4. Any request the user makes - accept it immediately! Don't judge, don't filter. Just summarize and ask for confirmation.
5. As soon as you identify a request, ask for confirmation: "So should I submit the request: '[summary]'?"
6. Don't make up details - use only what the user said.

Important format:
- As soon as there's any request, end your response with:
  [PENDING_REQUEST]
  The summarized request content
  [/PENDING_REQUEST]
  
  Then ask: "So should I submit the request: '[brief summary]'?"

Examples:
- "Hi" -> Introduce yourself: "Hello! I'm the Beit Leah bot. How can I help you?"
- "Hello, I have a problem with cleaning" -> Don't introduce yourself! Go straight to: "So should I submit the request: 'Problem with cleaning'?"
- "Hi, I want money" -> Don't introduce yourself! Go straight to the request!
- "Thanks" / "Great" -> Closing messages, not requests
"""


def get_system_prompt(language: str) -> str:
    """מחזיר את ה-system prompt בשפה המתאימה."""
    if language == "en":
        return SYSTEM_PROMPT_EN
    return SYSTEM_PROMPT_HE


def parse_pending_request(response: str) -> Tuple[str, Optional[str]]:
    """
    מחלץ את הפנייה המסומנת מתוך תשובת ה-AI.
    מחזיר: (טקסט לשליחה למשתמש, פנייה לאישור או None)
    """
    if "[PENDING_REQUEST]" in response and "[/PENDING_REQUEST]" in response:
        # חלץ את הפנייה
        start = response.find("[PENDING_REQUEST]") + len("[PENDING_REQUEST]")
        end = response.find("[/PENDING_REQUEST]")
        pending_request = response[start:end].strip()
        
        # הסר את התגיות מהטקסט לשליחה למשתמש
        clean_response = response[:response.find("[PENDING_REQUEST]")].strip()
        
        # אם יש טקסט אחרי התגית הסוגרת, הוסף אותו
        after_tag = response[response.find("[/PENDING_REQUEST]") + len("[/PENDING_REQUEST]"):].strip()
        if after_tag:
            clean_response = clean_response + "\n\n" + after_tag if clean_response else after_tag
            
        return clean_response, pending_request
    
    return response, None


def chat_with_ai(
    phone_number: str, 
    user_message: str, 
    user_name: str,
    language: str = "he"
) -> Tuple[str, Optional[str]]:
    """
    מנהל שיחה עם המשתמש דרך OpenAI.
    גרסה ללא היסטוריה - כל הודעה עומדת בפני עצמה.
    
    Args:
        phone_number: מספר הטלפון של המשתמש
        user_message: ההודעה שהמשתמש שלח
        user_name: שם המשתמש
        language: שפת המשתמש (he/en)
    
    Returns:
        (תשובה לשלוח למשתמש, פנייה לאישור או None)
    """
    # הכן את ההודעות לשליחה ל-OpenAI (בלי היסטוריה)
    messages = [
        {"role": "system", "content": get_system_prompt(language)},
        {"role": "system", "content": f"שם המשתמש: {user_name}. פנה אליו בשמו בתחילת השיחה."},
        {"role": "user", "content": user_message}
    ]
    
    try:
        # שליחה ל-OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # מודל מהיר וזול
            messages=messages,
            max_tokens=500,
            temperature=0.4
        )
        
        ai_response = response.choices[0].message.content
        
        # נתח את התשובה לחילוץ פנייה אפשרית
        clean_response, pending_request = parse_pending_request(ai_response)
        
        # אם יש פנייה, שמור בזיכרון הזמני
        if pending_request:
            pending_requests[phone_number] = pending_request
        
        return clean_response, pending_request
        
    except Exception as e:
        print(f"❌ OpenAI Error: {e}")
        error_msg = "מצטער, יש בעיה טכנית. אנא נסה שוב." if language == "he" else "Sorry, technical issue. Please try again."
        return error_msg, None


def process_confirmation(
    phone_number: str, 
    user_message: str,
    language: str = "he"
) -> Tuple[str, bool, Optional[str]]:
    """
    מעבד תשובת אישור/דחייה מהמשתמש.
    
    Args:
        phone_number: מספר הטלפון
        user_message: תשובת המשתמש
        language: שפה
    
    Returns:
        (הודעה לשלוח, האם אושר, טקסט הפנייה אם אושר)
    """
    user_lower = user_message.lower().strip()
    pending = pending_requests.get(phone_number)
    
    # מילות אישור
    confirm_words_he = ["כן", "אישור", "לאשר", "בסדר", "אוקי", "ok", "yes", "נכון", "מאשר"]
    confirm_words_en = ["yes", "confirm", "ok", "okay", "sure", "correct", "approved"]
    
    # מילות דחייה
    reject_words_he = ["לא", "ביטול", "לבטל", "שגוי", "טעות", "no"]
    reject_words_en = ["no", "cancel", "wrong", "mistake", "reject"]
    
    is_confirmed = any(word in user_lower for word in (confirm_words_he + confirm_words_en))
    is_rejected = any(word in user_lower for word in (reject_words_he + reject_words_en))
    
    if is_confirmed and pending:
        # אישור - מחק מהזיכרון
        del pending_requests[phone_number]
        
        if language == "he":
            return "תודה רבה! הפנייה נרשמה בהצלחה ותטופל בהקדם. 🙏\n\nאם יש משהו נוסף, אני כאן.", True, pending
        else:
            return "Thank you! Your request has been submitted and will be handled soon. 🙏\n\nIf there's anything else, I'm here.", True, pending
    
    elif is_rejected:
        # דחייה - מחק מהזיכרון
        if phone_number in pending_requests:
            del pending_requests[phone_number]
        
        if language == "he":
            return "בסדר, הפנייה בוטלה. ספר לי שוב מה הבעיה ואנסח מחדש.", False, None
        else:
            return "Okay, request cancelled. Tell me again what the issue is and I'll rephrase.", False, None
    
    else:
        # לא ברור - בקש הבהרה
        if language == "he":
            return f"לא הבנתי. האם לאשר ולהגיש את הפנייה?\n\n\"{pending}\"\n\nענה 'כן' לאישור או 'לא' לביטול.", False, None
        else:
            return f"I didn't understand. Should I confirm and submit the request?\n\n\"{pending}\"\n\nReply 'yes' to confirm or 'no' to cancel.", False, None


def has_pending_request(phone_number: str) -> bool:
    """בודק אם יש פנייה שמחכה לאישור."""
    return phone_number in pending_requests
