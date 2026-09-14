import re

def normalize_telegram_bot_token(raw_token: str) -> str:
    if not raw_token:
        return ""
    t = raw_token.strip().strip('"').strip("'").strip()
    # Remove leading full URL if pasted
    t = re.sub(r"^https?://api\.telegram\.org/bot", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^api\.telegram\.org/bot", "", t, flags=re.IGNORECASE)
    # Remove trailing endpoint if pasted
    t = re.sub(r"/[a-zA-Z]+$", "", t)
    # If starts with 'bot' followed immediately by digits (e.g. 'bot123456:ABC')
    if t.lower().startswith("bot") and ":" in t:
        parts = t.split(":", 1)
        if parts[0][3:].isdigit():
            t = parts[0][3:] + ":" + parts[1]
    return t.strip().strip('"').strip("'").strip()

def normalize_telegram_chat_id(raw_chat_id: str) -> str:
    if not raw_chat_id:
        return ""
    return str(raw_chat_id).strip().strip('"').strip("'").strip()

tests = [
    ("bot712345678:ABCDEF1234567890abcdef1234567890", "712345678:ABCDEF1234567890abcdef1234567890"),
    ('"712345678:ABCDEF1234567890abcdef1234567890"', "712345678:ABCDEF1234567890abcdef1234567890"),
    ("'712345678:ABCDEF1234567890abcdef1234567890' ", "712345678:ABCDEF1234567890abcdef1234567890"),
    ("https://api.telegram.org/bot712345678:ABCDEF1234567890abcdef1234567890", "712345678:ABCDEF1234567890abcdef1234567890"),
    ("https://api.telegram.org/bot712345678:ABCDEF1234567890abcdef1234567890/getMe", "712345678:ABCDEF1234567890abcdef1234567890"),
    (" 712345678:ABCDEF1234567890abcdef1234567890 \n", "712345678:ABCDEF1234567890abcdef1234567890"),
    ("712345678:ABCDEF1234567890abcdef1234567890", "712345678:ABCDEF1234567890abcdef1234567890")
]

for raw, expected in tests:
    norm = normalize_telegram_bot_token(raw)
    assert norm == expected, f"Failed on {raw} -> {norm} != {expected}"

print("All normalization unit tests passed!")
