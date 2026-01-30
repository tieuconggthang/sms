import logging
import time
from datetime import datetime, timezone

import serial

from com.nasa.cache.redis.otp_cache import RedisOtpCache
from com.nasa.entities.otp_message import OtpMessage
from com.nasa.infra.parser.sms_parser import parse_cmgl_text, parse_cmgr_text
from com.nasa.infra.serial.serial_modem import SerialModem, SerialConfig
from com.nasa.services.otp_extract_service import OtpExtractService

# logger = logging.getLogger("com.nasa.services.SmsService")

class SmsService:
    logger = logging.getLogger(__name__)
    def __init__(self,
                 port: str,
                 imei: str,
                 baudrate: int,
                 serial_timeout_s: float,
                 poll_interval_s: float,
                 delete_after_read: bool,
                 otp_extractor: OtpExtractService,
                 otp_cache: RedisOtpCache):
        self.port = port
        self.imei = imei
        self.baudrate = baudrate
        self.serial_timeout_s = serial_timeout_s
        self.poll_interval_s = poll_interval_s
        self.delete_after_read = delete_after_read
        self.otp_extractor = otp_extractor
        self.otp_cache = otp_cache

    def run_forever(self) -> None:
        modem = SerialModem(SerialConfig(port=self.port, baudrate=self.baudrate, timeout_seconds=self.serial_timeout_s))
        try:
            modem.init_for_sms()
            self.logger.info("connected imei=%s port=%s", self.imei, self.port)
            msisdn = modem.get_MSISDN101()
            self.logger.info("msisdn: %s", msisdn)
            # while True:
            modem.delete_all_sms()
            for line in modem.iter_lines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("+CME ERROR"):
                    continue
                if line.startswith("+CMTI"):
                    idx = modem.parse_cmti_index(line)
                    self.logger.debug("sms arrived imei=%s idx=%s", self.imei, idx)
                    self._handle_sms(modem, idx, msisdn)
                continue

                # resp = modem.list_unread()
                # msgs = parse_cmgl_text(resp)
                #
                # for sms in msgs:
                #     code = self.otp_extractor.extract(sms.text)
                #     msg = OtpMessage(
                #         otp=code or "",
                #         sender=sms.sender,
                #         imei=self.imei,
                #         msisdn=msisdn,
                #         port=self.port,
                #         received_at=datetime.now(timezone.utc),
                #         text=sms.text,
                #         timestamp=sms.timestamp,
                #         sms_index=sms.index
                #     )
                #
                #     payload = {
                #         "otp": msg.otp,
                #         "sender": msg.sender,
                #         "text": msg.text,
                #         "timestamp": msg.timestamp,
                #         "received_at": msg.received_at.isoformat(),
                #         "port": msg.port,
                #         "imei": msg.imei,
                #         "index": msg.sms_index,
                #     }
                #
                #     if code:
                #         self.otp_cache.put(msg.sender, payload)
                #         self.logger.info("PUSH imei=%s port=%s sender=%s otp=%s idx=%s",
                #                     self.imei, self.port, sms.sender, code, sms.index)
                #     else:
                #         self.logger.info("NO_OTP imei=%s port=%s sender=%s idx=%s",
                #                     self.imei, self.port, sms.sender, sms.index)
                #
                #     if self.delete_after_read:
                #         modem.delete_sms(sms.index)

                # time.sleep(self.poll_interval_s)
        except KeyboardInterrupt:
            self.logger.info("stopping imei=%s port=%s by signal", self.imei, self.port)
        except (serial.SerialException, OSError) as e:
            self.logger.error("DISCONNECTED imei=%s port=%s err=%s", self.imei, self.port, e, exc_info=True)
            raise
        finally:
            modem.close()
            self.logger.info("stopped imei=%s port=%s", self.imei, self.port)

    def _handle_sms(self, modem, idx, msisdn):
        resp = modem.read_sms(idx)  # AT+CMGR=idx
        sms = parse_cmgr_text(resp, idx)

        code = self.otp_extractor.extract(sms.text)
        msg = OtpMessage(
            otp=code or "",
            sender=sms.sender,
            imei=self.imei,
            msisdn=msisdn,
            port=self.port,
            received_at=datetime.now(timezone.utc),
            text=sms.text,
            timestamp=sms.timestamp,
            sms_index=sms.index
        )

        payload = {
            "otp": msg.otp,
            "sender": msg.sender,
            "text": msg.text,
            "timestamp": msg.timestamp,
            "received_at": msg.received_at.isoformat(),
            "port": msg.port,
            "imei": msg.imei,
            "index": msg.sms_index,
        }
        if code:
            self.otp_cache.put(msg.sender, payload)
            self.logger.info("PUSH imei=%s port=%s sender=%s otp=%s idx=%s",
                             self.imei, self.port, sms.sender, code, sms.index)
        else:
            self.logger.info("NO_OTP imei=%s port=%s sender=%s idx=%s",
                             self.imei, self.port, sms.sender, sms.index)

        if self.delete_after_read:
            modem.delete_sms(sms.index)
