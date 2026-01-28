from dataclasses import dataclass

@dataclass(frozen=True)
class ModemInfo:
    imei: str
    port: str
