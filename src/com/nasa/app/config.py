from dataclasses import dataclass
from typing import Optional, List
from com.nasa.common.utils import env_bool, env_float, env_int, env_str

@dataclass(frozen=True)
class AppConfig:
    manual_ports: Optional[List[str]]
    baudrate: int
    scan_interval_s: float
    probe_timeout_s: float
    serial_timeout_s: float
    poll_interval_s: float

    redis_url: str
    otp_ttl_seconds: int
    otp_key_prefix: str
    otp_regex: str
    delete_after_read: bool

    log_level: str
    log_file: str

def load_config() -> AppConfig:
    ports_raw = env_str("SERIAL_PORTS", "").strip()
    manual_ports = [p.strip() for p in ports_raw.split(",") if p.strip()] if ports_raw else None

    return AppConfig(
        manual_ports=manual_ports,
        baudrate=env_int("BAUDRATE", 115200),
        scan_interval_s=env_float("SCAN_INTERVAL_SECONDS", 3.0),
        probe_timeout_s=float(env_str("PROBE_TIMEOUT_SECONDS", "1.2")),
        serial_timeout_s=float(env_str("SERIAL_TIMEOUT_SECONDS", "2.0")),
        poll_interval_s=env_float("POLL_INTERVAL_SECONDS", 2.0),

        redis_url=env_str("REDIS_URL", "redis://localhost:6379/0"),
        otp_ttl_seconds=env_int("OTP_TTL_SECONDS", 300),
        otp_key_prefix=env_str("OTP_KEY_PREFIX", "otp:"),
        otp_regex=env_str("OTP_REGEX", r"\b(\d{4,8})\b"),
        delete_after_read=env_bool("DELETE_AFTER_READ", True),

        log_level=env_str("LOG_LEVEL", "INFO"),
        log_file=env_str("LOG_FILE", "logs/app.log"),
    )
