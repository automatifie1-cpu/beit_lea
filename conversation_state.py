"""
מודול לניהול מצב השיחות עם המשתמשים.
שומר את היסטוריית השיחה והמצב הנוכחי לכל משתמש בקובץ JSON.
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# זמן תפוגה לשיחה (בדקות)
CONVERSATION_TIMEOUT_MINUTES = 30

# נתיב לקובץ השיחות
CONVERSATIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'conversations.json')


def _load_conversations() -> Dict[str, Dict[str, Any]]:
    """טוען את השיחות מהקובץ."""
    try:
        if os.path.exists(CONVERSATIONS_FILE):
            with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # המר מחרוזות תאריך לאובייקטי datetime
                for phone, conv in data.items():
                    if conv.get("last_activity"):
                        conv["last_activity"] = datetime.fromisoformat(conv["last_activity"])
                    if conv.get("created_at"):
                        conv["created_at"] = datetime.fromisoformat(conv["created_at"])
                return data
    except Exception as e:
        print(f"❌ Error loading conversations: {e}")
    return {}


def _save_conversations(conversations: Dict[str, Dict[str, Any]]) -> None:
    """שומר את השיחות לקובץ."""
    try:
        # המר datetime למחרוזות לפני שמירה
        data_to_save = {}
        for phone, conv in conversations.items():
            conv_copy = conv.copy()
            if isinstance(conv_copy.get("last_activity"), datetime):
                conv_copy["last_activity"] = conv_copy["last_activity"].isoformat()
            if isinstance(conv_copy.get("created_at"), datetime):
                conv_copy["created_at"] = conv_copy["created_at"].isoformat()
            data_to_save[phone] = conv_copy
            
        with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Error saving conversations: {e}")


def get_conversation(phone_number: str) -> Dict[str, Any]:
    """
    מחזיר את מצב השיחה הנוכחי למשתמש.
    אם אין שיחה פעילה או שהשיחה פגה, יוצר שיחה חדשה.
    """
    now = datetime.now()
    conversations = _load_conversations()
    
    if phone_number in conversations:
        conv = conversations[phone_number]
        last_activity = conv.get("last_activity")
        
        # בדוק אם השיחה עדיין בתוקף
        if last_activity:
            time_diff = now - last_activity
            if time_diff < timedelta(minutes=CONVERSATION_TIMEOUT_MINUTES):
                # עדכן זמן פעילות אחרון
                conv["last_activity"] = now
                _save_conversations(conversations)
                return conv
    
    # צור שיחה חדשה
    conversations[phone_number] = {
        "messages": [],  # היסטוריית הודעות לשליחה ל-OpenAI
        "state": "chatting",  # מצבים: chatting, confirming_request, completed
        "pending_request": None,  # הפנייה שמחכה לאישור
        "last_activity": now,
        "created_at": now
    }
    _save_conversations(conversations)
    
    return conversations[phone_number]


def add_message(phone_number: str, role: str, content: str) -> None:
    """
    מוסיף הודעה להיסטוריית השיחה.
    role: "user" או "assistant"
    """
    conversations = _load_conversations()
    conv = get_conversation(phone_number)
    conv["messages"].append({
        "role": role,
        "content": content
    })
    conv["last_activity"] = datetime.now()
    conversations[phone_number] = conv
    _save_conversations(conversations)


def get_messages(phone_number: str) -> List[Dict[str, str]]:
    """מחזיר את היסטוריית ההודעות לשליחה ל-OpenAI."""
    conv = get_conversation(phone_number)
    return conv["messages"]


def set_state(phone_number: str, state: str) -> None:
    """מעדכן את מצב השיחה."""
    conversations = _load_conversations()
    conv = get_conversation(phone_number)
    conv["state"] = state
    conv["last_activity"] = datetime.now()
    conversations[phone_number] = conv
    _save_conversations(conversations)


def get_state(phone_number: str) -> str:
    """מחזיר את מצב השיחה הנוכחי."""
    conv = get_conversation(phone_number)
    return conv.get("state", "chatting")


def set_pending_request(phone_number: str, request_text: str) -> None:
    """שומר פנייה שמחכה לאישור."""
    conversations = _load_conversations()
    conv = get_conversation(phone_number)
    conv["pending_request"] = request_text
    conv["last_activity"] = datetime.now()
    conversations[phone_number] = conv
    _save_conversations(conversations)


def get_pending_request(phone_number: str) -> Optional[str]:
    """מחזיר את הפנייה שמחכה לאישור."""
    conv = get_conversation(phone_number)
    return conv.get("pending_request")


def clear_conversation(phone_number: str) -> None:
    """מנקה את השיחה לחלוטין."""
    conversations = _load_conversations()
    if phone_number in conversations:
        del conversations[phone_number]
        _save_conversations(conversations)


def reset_for_new_request(phone_number: str) -> None:
    """מאפס את השיחה לקבלת פנייה חדשה (שומר היסטוריה מינימלית)."""
    conversations = _load_conversations()
    conv = get_conversation(phone_number)
    conv["messages"] = []
    conv["state"] = "chatting"
    conv["pending_request"] = None
    conv["last_activity"] = datetime.now()
    conversations[phone_number] = conv
    _save_conversations(conversations)
