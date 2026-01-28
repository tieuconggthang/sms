import os

def env_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.strip().lower() in ("1","true","yes","y","on")

def env_float(key: str, default: float) -> float:
    v = os.getenv(key)
    if v is None or not v.strip():
        return default
    return float(v)

def env_int(key: str, default: int) -> int:
    v = os.getenv(key)
    if v is None or not v.strip():
        return default
    return int(v)

def env_str(key: str, default: str = "") -> str:
    v = os.getenv(key)
    return default if v is None else v
