from dataclasses import dataclass

@dataclass(frozen=True)
class Sms:
    index: int
    status: str
    sender: str
    timestamp: str
    text: str
