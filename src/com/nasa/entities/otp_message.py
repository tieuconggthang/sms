from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class OtpMessage:
    otp: str
    sender: str
    imei: str
    msisdn: str
    port: str
    received_at: datetime
    text: str
    timestamp: str
    sms_index: int
