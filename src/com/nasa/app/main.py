from dotenv import load_dotenv

from com.nasa.app.config import load_config
from com.nasa.app.loggingconfig import setup_logging
from com.nasa.cache.redis.redis_client import create_redis
from com.nasa.cache.redis.otp_cache import RedisOtpCache, RedisOtpCacheConfig
from com.nasa.services.otp_extract_service import OtpExtractService
from com.nasa.services.port_manager_service import PortManagerService
import logging

def main():
    logger = logging.getLogger(__name__)
    load_dotenv()
    cfg = load_config()
    setup_logging(cfg.log_level, cfg.log_file)

    r = create_redis(cfg.redis_url)
    otp_cache = RedisOtpCache(r, RedisOtpCacheConfig(ttl_seconds=cfg.otp_ttl_seconds, key_prefix=cfg.otp_key_prefix))
    extractor = OtpExtractService(cfg.otp_regex)

    def sms_service_factory(port: str, imei: str):
        from com.nasa.services.sms_service import SmsService
        return SmsService(
            port=port,
            imei=imei,
            baudrate=cfg.baudrate,
            serial_timeout_s=cfg.serial_timeout_s,
            poll_interval_s=cfg.poll_interval_s,
            delete_after_read=cfg.delete_after_read,
            otp_extractor=extractor,
            otp_cache=otp_cache
        )

    pm = PortManagerService(
        manual_ports=cfg.manual_ports,
        baudrate=cfg.baudrate,
        scan_interval_s=cfg.scan_interval_s,
        probe_timeout_s=cfg.probe_timeout_s,
        serial_timeout_s=cfg.serial_timeout_s,
        poll_interval_s=cfg.poll_interval_s,
        sms_service_factory=sms_service_factory
    )
    try:
        pm.run_forever()
    except KeyboardInterrupt:
        logger.info("Received Ctrl+C, shutting down gracefully...")
    finally:
        pm.stop()   # nếu bạn có method này    
    # pm.run_forever()

if __name__ == "__main__":
    main()
