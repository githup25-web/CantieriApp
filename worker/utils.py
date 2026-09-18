from datetime import datetime


def utcnow():
    return datetime.utcnow()


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def truncate(text: str, max_len: int = 200):
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text
