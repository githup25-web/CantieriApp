METRICS = {}


def inc(key: str, amount: int = 1):
    if key not in METRICS:
        METRICS[key] = 0
    METRICS[key] += amount


def get(key: str, default=0):
    return METRICS.get(key, default)


def snapshot():
    return METRICS.copy()
