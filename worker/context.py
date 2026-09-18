CONTEXT = {}

def set(key: str, value):
    CONTEXT[key] = value

def get(key: str, default=None):
    return CONTEXT.get(key, default)

def all():
    return CONTEXT.copy()
