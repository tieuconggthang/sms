import logging
import re
from datetime import datetime
from typing import List, Optional

from com.nasa.entities.sms import Sms

log = logging.getLogger(__name__)
CMGR_RE = re.compile(
    r'\+CMGR:\s*"(?P<status>[^"]+)",\s*"(?P<sender>[^"]*)".*?\r\n(?P<text>.*?)\r\n',
    re.DOTALL
)

CMGR_HEADER_RE = re.compile(
    r'\+CMGR:\s*"(?P<status>[^"]+)",'
    r'"(?P<sender>[^"]*)",.*?,'
    r'"(?P<time>[^"]+)"'
)


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

                out.append(
                    Sms(index=idx, status=status, sender=sender, timestamp=ts, text="\n".join(text_lines).strip()))
                i = j
                continue
        i += 1
    return out


def parse_cmgr_text(resp: str, index: int) -> Optional[Sms]:
    if not resp:
        return None

    try:
        log.info("parse sms")
        lines = [l.strip() for l in resp.splitlines() if l.strip()]
        if len(lines) < 2:
            return None
        header = lines[0]
        body_raw = lines[1]
        # header = decode_ucs2_if_needed(lines[0])
        body = decode_ucs2_if_needed(lines[1])
        # header, body = lines[0], lines[1]

        m = CMGR_HEADER_RE.search(header)
        if not m:
            return None

        sender_raw = m.group("sender")
        status_raw = m.group("status")
        time_str = m.group("time")
        sender = decode_ucs2_if_needed(sender_raw)
        status = decode_ucs2_if_needed(status_raw)
        # parse timestamp (fallback nếu lỗi)

        return Sms(
            index=index,
            sender=sender,
            text=body,
            timestamp=time_str,
            status=status
        )

    except Exception as e:
        log.error(
            "CMGR parse failed idx=%s resp=%r",
            index, resp, e
        )
        return None


def decode_ucs2_if_needed(s: str) -> str:
    if s and all(c in "0123456789ABCDEFabcdef" for c in s):
        try:
            return bytes.fromhex(s).decode("utf-16-be")
        except Exception:
            return s
    return s


def extract_otp(text: str, otp_regex: str) -> Optional[str]:
    try:
        m = re.search(otp_regex, text)
        return m.group(1) if m else None
    except re.error:
        m = re.search(r"\b(\d{4,8})\b", text)
        return m.group(1) if m else None
