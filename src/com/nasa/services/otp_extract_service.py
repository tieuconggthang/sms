from dataclasses import dataclass
from typing import Optional
from com.nasa.infra.parser.sms_parser import extract_otp

@dataclass(frozen=True)
class OtpExtractService:
    otp_regex: str

    def extract(self, text: str) -> Optional[str]:
        return extract_otp(text, self.otp_regex)
