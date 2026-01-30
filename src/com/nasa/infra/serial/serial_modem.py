import time
import threading
from dataclasses import dataclass
from typing import Optional, Tuple
import re
import serial
import logging
from com.nasa.infra.utils.codec_utils import UssdUtils
@dataclass(frozen=True)
class SerialConfig:
    port: str
    baudrate: int
    timeout_seconds: float

CUSD_RE = re.compile(r'\+CUSD:\s*(\d+)\s*,\s*"([^"]*)"(?:\s*,\s*(\d+))?', re.IGNORECASE)
CNUM_RE = re.compile(r'\+CNUM:\s*(?:"[^"]*",)?\s*"?(?P<number>\+?\d{8,15})"?', re.IGNORECASE)

class SerialModem:
    logger = logging.getLogger(__name__)
    def __init__(self, cfg: SerialConfig):
        self.cfg = cfg
        self._lock = threading.Lock()
        self.ser = serial.Serial(cfg.port, cfg.baudrate, timeout=cfg.timeout_seconds)
        self.logger.info("Serial opened port=%s baudrate=%s", cfg.port, cfg.baudrate)

    def close(self):
        try:
            self.ser.close()
            self.logger.info("Serial closed port=%s", self.cfg.port)
        except Exception as e:
            self.logger.warning("Serial close failed port=%s err=%s", self.cfg.port, e)


    def _read_all(self) -> str:
        time.sleep(0.15)
        return self.ser.read_all().decode(errors="ignore")

    def send(self, cmd: str, max_wait_seconds: float = 2.0) -> str:
        with self._lock:
            try:
                # (optional) clear buffers — best effort, không critical
                try:
                    self.ser.reset_input_buffer()
                    self.ser.reset_output_buffer()
                except Exception:
                    pass

                self.logger.debug("AT SEND port=%s cmd=%s", self.cfg.port, cmd)

                # write
                self.ser.write((cmd + "\r").encode("utf-8"))
                self.ser.flush()

                # read
                end = time.time() + max_wait_seconds
                buf = ""
                while time.time() < end:
                    buf += self._read_all()

                    # thành công
                    if "\nOK" in buf or buf.strip().endswith("OK"):
                        self.logger.debug("AT OK port=%s cmd=%s", self.cfg.port, cmd)
                        return buf

                    # lỗi modem
                    if "ERROR" in buf or "+CME ERROR" in buf:
                        self.logger.warning("AT ERROR port=%s cmd=%s resp=%s", self.cfg.port, cmd, buf.strip())
                        return buf

                self.logger.warning("AT TIMEOUT port=%s cmd=%s resp=%s", self.cfg.port, cmd, buf.strip())
                return buf

            except Exception as e:
                # chỉ bắt 1 lần ở đây, wrap lại
                self.logger.exception("AT IO FAILED port=%s cmd=%s", self.cfg.port, cmd)
                return None

    def send_ussd(self, code: str, dcs: int = 15, timeout_s: float = 10.0) -> str:
        self.logger.info("USSD SEND port=%s code=%s", self.cfg.port, code)
        try:
            return self.send(f'AT+CUSD=1,"{code}",{dcs}', max_wait_seconds=timeout_s)
        except Exception as e:
            self.logger.exception("USSD FAILED port=%s code=%s err=%s", self.cfg.port, code, e)
            return ""

    def send_ussd_wait(self, code: str, dcs: int = 15, timeout_s: float = 12.0) -> str:
        """
        Gửi USSD và CHỜ đến khi thấy +CUSD: ... (vì +CUSD đến sau OK).
        Trả về toàn bộ buffer thu được.
        """
        with self._lock:
            try:
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
            except Exception:
                pass

            # gửi lệnh
            cmd = f'AT+CUSD=1,"{code}",{dcs}\r'
            self.ser.write(cmd.encode("utf-8"))
            self.ser.flush()

            end = time.time() + timeout_s
            buf = ""
            saw_ok = False

            while time.time() < end:
                buf += self._read_all()

                # có thể OK tới trước
                if "\nOK" in buf or buf.strip().endswith("OK"):
                    saw_ok = True

                # +CUSD là cái ta cần
                if "+CUSD:" in buf:
                    return buf

                # lỗi thì trả luôn
                if "ERROR" in buf or "+CME ERROR" in buf:
                    return buf

            # timeout: trả buf để bạn log xem đã nhận gì
            return buf
    def cancel_ussd(self) -> str:
        return self.send("AT+CUSD=2", max_wait_seconds=2.0)

    def init_for_sms(self) -> None:
        self.send("AT")
        self.send("ATE0")
        self.send("AT+CMEE=2")
        self.send('AT+CSCS="UCS2"')
        self.send("AT+CMGF=1")
        self.send('AT+CPMS="SM","SM","SM"')
        self.send("AT+CNMI=2,1,0,0,0")

    @staticmethod
    def parse_number(resp: str) -> Optional[str]:
        """Parse MSISDN from AT+CNUM response."""
        if not resp:
            return None
        for line in resp.splitlines():
            m = CNUM_RE.search(line.strip())
            if m:
                return m.group("number")
        return None

    def get_msisdn(self) -> Optional[str]:
        resp = self.send("AT+CNUM", max_wait_seconds=3.0)
        return self.parse_number(resp)

    def get_MSISDN101(self) -> Optional[str]:
        # best-effort: USSD code (tuỳ nhà mạng)
        resp = self.send_ussd_wait("*101#", timeout_s=12.0)
        mode, text, dcs = self.parse_ussd(resp)
        if text:
            # bạn có thể regex bóc số ở đây nếu cần
            text = UssdUtils.normalize_text(text, dcs)
            msisdn = UssdUtils.extract_msisdn(text)
            return text
        return ""

    def iter_lines(self):
        while True:
            try:
                line = self.ser.readline().decode(errors="ignore")
                if line:
                    yield line
            except Exception as e:
                self.logger.error("ex", e)

    def parse_cmti_index(self, line: str) -> int:
        try:
            self.logger.debug("line: %s", line)
        # +CMTI: "SM",12
            return int(line.split(",")[1])
        except Exception as e:
            self.logger.error("ex", e)

    def read_sms(self, idx: int) -> str:
        return self.send(f"AT+CMGR={idx}", max_wait_seconds=3.0)

    def list_unread(self) -> str:
        try:
            return self.send('AT+CMGL="REC UNREAD"', max_wait_seconds=4.0)
        except Exception as e:
            self.logger.exception("SMS LIST FAILED port=%s err=%s", self.cfg.port, e)
            return ""

    def delete_sms(self, index: int) -> str:
        try:
            return self.send(f"AT+CMGD={index}", max_wait_seconds=2.0)
        except Exception as e:
            self.logger.exception(
                "SMS DELETE FAILED port=%s index=%s err=%s",
                self.cfg.port, index, e
            )
            return ""

    def delete_all_sms(self) -> str:
        try:
            return self.send(f"AT+CMGD=1,4", max_wait_seconds=2.0)
        except Exception as e:
            self.logger.exception(
                "SMS DELETE FAILED port=%s err=%s",
                self.cfg.port,  e
            )
            return ""
    def parse_ussd(self, resp: str) -> Tuple[Optional[int], Optional[str], Optional[int]]:
        if not resp:
            return (None, None, None)
        m = CUSD_RE.search(resp)
        if not m:
            return (None, None, None)
        mode = int(m.group(1))
        text = m.group(2)
        dcs = int(m.group(3)) if m.group(3) else None
        return (mode, text, dcs)
