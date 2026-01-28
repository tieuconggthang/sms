import re
from typing import List, Optional

from com.nasa.entities.sms import Sms

def parse_cmgl_text(resp: str) -> List[Sms]:
    lines = resp.splitlines()
    out: List[Sms] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip("\r")
        if line.startswith("+CMGL:"):
            m = re.match(
                r'^\+CMGL:\s*(\d+)\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*$',
                line
            )
            if m:
                idx = int(m.group(1))
                status = m.group(2)
                sender = m.group(3)
                ts = m.group(5)

                j = i + 1
                text_lines = []
                while j < len(lines):
                    nl = lines[j].strip("\r")
                    if nl.startswith("+CMGL:") or nl == "OK" or nl.startswith("ERROR"):
                        break
                    text_lines.append(nl)
                    j += 1

                out.append(Sms(index=idx, status=status, sender=sender, timestamp=ts, text="\n".join(text_lines).strip()))
                i = j
                continue
        i += 1
    return out

def extract_otp(text: str, otp_regex: str) -> Optional[str]:
    try:
        m = re.search(otp_regex, text)
        return m.group(1) if m else None
    except re.error:
        m = re.search(r"\b(\d{4,8})\b", text)
        return m.group(1) if m else None
