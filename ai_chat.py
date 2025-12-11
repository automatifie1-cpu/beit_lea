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
התפקיד שלך הוא לנהל שיחה טבעית עם פונים ולעזור להם להגיש פניות לעמותה.

כללים חשובים:
1. היה אדיב, קצר וענייני בתשובות (2-3 משפטים מקסימום).
2. אם המשתמש שולח הודעה כללית כמו "היי", "שלום", "מה שלומך" - הצג את עצמך! 
   ענה משהו כמו: "שלום! אני הבוט של עמותת בית לאה  אני כאן כדי לעזור לך להגיש פניות לעמותה. ספר לי במה אוכל לעזור?"
3. כל בקשה שהמשתמש מעלה - לא משנה מה היא, גם אם היא נשמעת לא הגיונית, גם בקשה לכסף, גם בקשה מוזרה - קבל אותה מיד כפנייה! אל תשפוט, אל תסנן, אל תשאל שאלות הבהרה. פשוט סכם את הבקשה ושאל לאישור.
4. ברגע שזיהית בקשה כלשהי, מיד שאל לאישור בפורמט: "אז להכניס את הפנייה: '[סיכום הפנייה]'?"
5. אל תמציא פרטים - השתמש רק במה שהמשתמש אמר.

פורמט חשוב:
- ברגע שיש בקשה כלשהי, סיים את התשובה במבנה הבא:
  [PENDING_REQUEST]
  תוכן הפנייה המסוכם
  [/PENDING_REQUEST]
  
  ואז שאל: "אז להכניס את הפנייה: '[סיכום קצר]'?"

דוגמאות לפניות (כל בקשה היא פנייה!):
- "יש לי בעיה עם הניקיון בחדר מדרגות" -> פנייה!
- "התאורה בחניה לא עובדת כבר שבוע" -> פנייה!
- "אני רוצה כסף" -> פנייה!
- "אני צריך עזרה עם משהו מוזר" -> פנייה!
- "אני רוצה לדעת מתי הפגישה הבאה" -> פנייה!

דוגמאות שאינן פניות (רק הודעות כלליות):
- "היי" / "שלום" / "בוקר טוב" -> הודעות כלליות, הצג את עצמך ושאל במה לעזור
- "תודה" / "יופי" -> הודעות סיום, לא פניות
"""

SYSTEM_PROMPT_EN = """You are a friendly and professional customer service representative for "Beit Leah" - a nonprofit organization.
Your role is to have natural conversations with people and help them submit requests to the organization.

Important rules:
1. Be polite, brief and to the point (2-3 sentences max).
2. If user sends general messages like "hi", "hello" - introduce yourself!
   Say something like: "Hello! I'm the Beit Leah bot. I'm here to help you submit requests. How can I help you?"
3. ANY request the user makes - no matter what it is, even if it sounds illogical, even a request for money, even a strange request - accept it immediately as a formal request! Don't judge, don't filter, don't ask clarifying questions. Just summarize the request and ask for confirmation.
4. As soon as you identify any request, immediately ask for confirmation like: "So should I submit the request: '[summary]'?"
5. Don't make up details - use only what the user said.

Important format:
- As soon as there's any request, end your response with:
  [PENDING_REQUEST]
  The summarized request content
  [/PENDING_REQUEST]
  
  Then ask: "So should I submit the request: '[brief summary]'?"

Examples of requests (any request counts!):
- "I have a problem with cleaning in the stairwell" -> Request!
- "The lighting in the parking lot hasn't worked for a week" -> Request!
- "I want money" -> Request!
- "I need help with something weird" -> Request!

Examples that are NOT requests (only general messages):
- "Hi" / "Hello" / "Good morning" -> General messages, introduce yourself and ask how to help
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
            temperature=0.3
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
