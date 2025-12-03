import requests
from typing import Dict, Any
from config import PHONE_NUMBER_ID, WHATSAPP_TOKEN
import traceback

# Minimal, focused helper module for sending WhatsApp messages and contacts.
# Only essentials kept: phone normalization, payload builders, and send functions.

API_URL = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
headers = {
    "Authorization": f"Bearer {WHATSAPP_TOKEN}",
    "Content-Type": "application/json",
}
TIMEOUT = 15


def _post(payload: dict):
    """Send a raw payload to the WhatsApp Cloud API.

    Args:
        payload: Dict already shaped according to WhatsApp send message spec.

    Returns:
        (ok, data) where ok is True for HTTP 2xx, data is parsed JSON or raw text.
    """
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=TIMEOUT)
        try:
            data = r.json()
        except ValueError:
            data = {"raw": r.text}
        return (200 <= r.status_code < 300), data
    except requests.RequestException as e:
        tb = traceback.TracebackException.from_exception(e)
        frame = tb.stack[-1] if tb.stack else None
        log_event(
            'whatsapp_api_error',
            error=str(e),
            file=getattr(frame, 'filename', None),
            line=getattr(frame, 'lineno', None),
            func=getattr(frame, 'name', None),
        )
        return False, {"error": str(e)}


def build_text_payload(to: str, text: str) -> Dict[str, Any]:
    """Build (no network) the payload for a plain text message.

    Args:
        to: Destination phone number, must be in +972 format (current restriction).
        text: Message body (non-empty).

    Raises:
        ValueError: If inputs are invalid.

    Returns:
        dict ready to send.
    """
    if not to or not isinstance(to, str):
        raise ValueError("'to' must be a non-empty string phone number")
    if not text:
        raise ValueError("'text' must be a non-empty string")
    return {"messaging_product": "whatsapp", "to": normalize_phone_relaxed(to), "text": {"body": text}}


def _build_contact_payload(
    to: str,
    name: str,
    phone_number: str,
    phone_type: str = "CELL",
    first_name: str | None = None,
    last_name: str | None = None,
    org: str | None = None,
):
    """Build (no network) a contact card payload.

    WhatsApp requires the name object to include formatted_name plus at least
    one additional field (first_name or last_name) to avoid error 131009.

    Args:
        to: Recipient phone number (+972...).
        name: Full formatted display name.
        phone_number: The contact's phone number.
        phone_type: Optional phone type (default CELL).
        first_name: Explicit first name (derived if absent).
        last_name: Explicit last name (derived if absent and available).
        org: Optional organization/company name.

    Returns:
        dict contact payload.
    """
    if not to:
        raise ValueError("Recipient 'to' phone is required")
    if not name:
        raise ValueError("Contact 'name' is required")
    if not phone_number:
        raise ValueError("Contact 'phone_number' is required")

    normalized_to = normalize_phone_relaxed(to)
    normalized_contact_phone = normalize_phone_relaxed(phone_number)

    # Derive first/last name if not explicitly provided.
    if not first_name or first_name.strip() == "":
        parts = name.strip().split()
        if parts:
            first_name = parts[0]
            if not last_name and len(parts) > 1:
                last_name = " ".join(parts[1:])

    name_obj = {"formatted_name": name}
    # Add at least one optional name field to satisfy API rules.
    if first_name:
        name_obj["first_name"] = first_name
    if last_name:
        name_obj["last_name"] = last_name

    # Fallback: if somehow first_name still missing, reuse formatted_name
    if "first_name" not in name_obj:
        name_obj["first_name"] = name

    # Provide digits-only version for wa_id so WhatsApp can positively match the user.
    digits_only = normalized_contact_phone.lstrip('+')
    phone_obj = {"phone": digits_only, "type": phone_type.upper()}
    if digits_only.isdigit():
        phone_obj["wa_id"] = digits_only

    contact_entry: dict = {
        "name": name_obj,
        "phones": [phone_obj],
    }
    if org:
        contact_entry["org"] = {"company": org}

    return {"messaging_product": "whatsapp", "to": normalized_to, "type": "contacts", "contacts": [contact_entry]}


def normalize_phone_relaxed(raw: str) -> str:
    """Broader phone normalization for Israeli numbers.

    Accepts inputs like:
      +972547509607
      972547509607
      0547509607
      054-750-9607
      547509607 (missing leading 0)

    Strategy:
      1. Strip whitespace and separators (-, space, parentheses).
      2. Detect existing +972 prefix (return canonical +972 + rest).
      3. Detect 972 prefix without plus (convert to +972...).
      4. Mobile patterns: 05X....... or 5X....... (with/without leading 0).
      5. Landline basic patterns: 0[2,3,4,8,9]XXXXXXX or [2,3,4,8,9]XXXXXXX.

    Returns:
      E.164-like string beginning with +972.

    Raises:
      ValueError if cannot confidently normalize.
    """
    if not raw:
        raise ValueError("Phone number cannot be empty")
    # Remove separators
    cleaned = ''.join(ch for ch in raw if ch.isdigit() or ch == '+')
    if cleaned.startswith('+') and not cleaned.startswith('+972'):
        raise ValueError("Only Israeli (+972) numbers are supported")
    # +972 path
    if cleaned.startswith('+972'):
        rest = cleaned[4:]
        if rest.startswith('0'):
            # Remove accidental leading zero after country code
            rest = rest[1:]
        if not rest.isdigit() or len(rest) < 8 or len(rest) > 10:
            raise ValueError("Invalid +972 number body")
        return '+972' + rest
    # 972 without plus
    if cleaned.startswith('972'):
        rest = cleaned[3:]
        if rest.startswith('0'):
            rest = rest[1:]
        if not rest.isdigit() or len(rest) < 8 or len(rest) > 10:
            raise ValueError("Invalid 972 number body")
        return '+972' + rest
    # local with leading 0 (mobile or landline)
    if cleaned.startswith('0'):
        body = cleaned[1:]
        if body.startswith('5') and 8 <= len(body) <= 9:
            # mobile (05X... 9 or 10 digits including leading 0). Accept length variance.
            return '+972' + body
        if body[:1] in {'2','3','4','8','9'} and len(body) == 8:
            return '+972' + body
        # If exact mobile length 9 (after removing 0) we accept
        raise ValueError("Unrecognized local pattern with leading 0")
    # missing leading 0: mobile begins with 5
    if cleaned.startswith('5') and 8 <= len(cleaned) <= 9:
        return '+972' + cleaned
    # missing leading 0 landline (starts with area code digit)
    if cleaned[:1] in {'2','3','4','8','9'} and len(cleaned) == 8:
        return '+972' + cleaned
    raise ValueError("Cannot normalize number: %s" % raw)


def send_message(to: str, text: str):
    """Send a plain text message. Returns (ok, data)."""
    try:
        return _post(build_text_payload(to, text))
    except ValueError as e:
        # Handle empty text or invalid input
        tb = traceback.TracebackException.from_exception(e)
        frame = tb.stack[-1] if tb.stack else None
        log_event(
            'send_message_validation_error',
            error=str(e),
            to=to,
            text_empty=not text or not text.strip(),
            file=getattr(frame, 'filename', None),
            line=getattr(frame, 'lineno', None),
            func=getattr(frame, 'name', None),
        )
        return False, {"error": str(e)}


def send_contact(
    to: str,
    name: str,
    phone_number: str,
    phone_type: str = "CELL",
    first_name: str | None = None,
    last_name: str | None = None,
    org: str | None = None,
):
    """Send a contact card. Returns (ok, data)."""
    try:
        return _post(
            _build_contact_payload(
                to=to,
                name=name,
                phone_number=phone_number,
                phone_type=phone_type,
                first_name=first_name,
                last_name=last_name,
                org=org,
            )
        )
    except ValueError as e:
        # Handle validation errors in contact payload
        tb = traceback.TracebackException.from_exception(e)
        frame = tb.stack[-1] if tb.stack else None
        log_event(
            'send_contact_validation_error',
            error=str(e),
            to=to,
            name=name,
            phone_number=phone_number,
            file=getattr(frame, 'filename', None),
            line=getattr(frame, 'lineno', None),
            func=getattr(frame, 'name', None),
        )
        return False, {"error": str(e)}



def send_typing_state(msg_id:str):
    payload = {
    "messaging_product": "whatsapp",
    "status": "read",
    "message_id": msg_id,
    "typing_indicator": {"type": "text"}
    }

    resp = _post(payload)
    return resp



