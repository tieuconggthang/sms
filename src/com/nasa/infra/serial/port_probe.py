import re
import time
from dataclasses import dataclass
from typing import Optional, List

import serial
from serial.tools import list_ports

IMEI_RE = re.compile(r"\b(\d{14,17})\b")

@dataclass(frozen=True)
class ProbeConfig:
    baudrate: int
    timeout_seconds: float
    max_wait_seconds: float = 1.5

def _send(ser: serial.Serial, cmd: str, wait_s: float = 1.2) -> str:
    ser.write((cmd + "\r").encode("utf-8"))
    ser.flush()
    end = time.time() + wait_s
    buf = ""
    while time.time() < end:
        buf += _read_all(ser)
        if "OK" in buf or "ERROR" in buf or "+CME ERROR" in buf:
            break
    return buf
def _read_all(ser: serial.Serial) -> str:
    time.sleep(0.15)
    return ser.read_all().decode(errors="ignore")

def list_candidate_ports(limit_to: Optional[List[str]] = None) -> List[str]:
    ports = [p.device for p in list_ports.comports()]
    allPortsInLimit = ports
    if limit_to:
        s = set(limit_to)
        allPortsInLimit = [p for p in ports if p in s]
    return allPortsInLimit

def _probe_sms_capable(ser: serial.Serial) -> bool:
    r1 = _send(ser, "ATE0", 1.0)
    r2 = _send(ser, "AT+CMEE=2", 1.0)
    r3 = _send(ser, "AT+CMGF=1", 1.2)
    if "OK" not in r3:
        return False

    r4 = _send(ser, "AT+CPMS?", 1.2)
    r5 = _send(ser, 'AT+CPMS="SM","SM","SM"', 1.5)

    r6 = _send(ser, "AT+CMGL=?", 1.2)
    return ("+CMGL:" in r6) and ("OK" in r6)

def _probe_ussd_capable(ser: serial.Serial) -> bool:
    # enable USSD + check support
    r1 = _send(ser, "AT+CUSD=1", 1.2)
    r2 = _send(ser, "AT+CUSD=?", 1.2)
    return ("OK" in r2) or ("OK" in r1)

def probe_imei(port: str, cfg: ProbeConfig) -> Optional[str]:
    try:
        ser = serial.Serial(port, cfg.baudrate, timeout=cfg.timeout_seconds)
    except Exception:
        return None
    try:
        ser.write(b"AT\r"); ser.flush()
        buf = ""
        end = time.time() + cfg.max_wait_seconds
        while time.time() < end:
            buf += _read_all(ser)
            if "OK" in buf:
                break
        if "OK" not in buf:
            return None

        for cmd in (b"AT+CGSN\r", b"AT+GSN\r"):
            try:
                ser.reset_input_buffer()
            except Exception:
                pass
            ser.write(cmd); ser.flush()
            buf = ""
            end = time.time() + cfg.max_wait_seconds
            while time.time() < end:
                buf += _read_all(ser)
                if "OK" in buf or "ERROR" in buf:
                    break
            m = IMEI_RE.search(buf)
            if m:
                sms_ok = _probe_sms_capable(ser)
                ussd_ok = _probe_ussd_capable(ser)
                if sms_ok:
                    return m.group(1)
        return None
    finally:
        try:
            ser.close()
        except Exception:
            pass
