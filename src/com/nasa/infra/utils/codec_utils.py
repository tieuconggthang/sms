import re
from typing import Optional

class UssdUtils:

    @staticmethod
    def normalize_text(raw_text: str, dcs: Optional[int]) -> str:
        if not raw_text:
            return ""

        # UCS2 / HEX
        if dcs in (72, 8, 15) and re.fullmatch(r"[0-9A-Fa-f]+", raw_text):
            try:
                return bytes.fromhex(raw_text).decode("utf-16-be").strip()
            except Exception:
                return raw_text

        return raw_text.strip()

    @staticmethod
    def extract_msisdn(text: str) -> Optional[str]:
        if not text:
            return None

        m = re.search(r"(0\d{9,10}|\+84\d{9})", text)
        return m.group(1) if m else None
