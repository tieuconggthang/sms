import json
from dataclasses import dataclass
from typing import Optional
import redis
import logging
@dataclass(frozen=True)
class RedisOtpCacheConfig:
    ttl_seconds: int
    key_prefix: str

class RedisOtpCache:
    logger = logging.getLogger(__name__)
    def __init__(self, client: redis.Redis, cfg: RedisOtpCacheConfig):
        self.client = client
        self.cfg = cfg

    def put(self, sender: str, payload: dict) -> None:
        try:
            key = self.buildRedisKey(sender=sender, payload=payload)
            self.client.setex(key, self.cfg.ttl_seconds, json.dumps(payload, ensure_ascii=False))
            self.logger.info("put: %s", key)
            self.logger.debug("put payload key=%s payload=%s",key,json.dumps(payload, ensure_ascii=False))
        except Exception as e:
            self.logger.warning("put key=%s err=%s", key, e)


    def get(self, sender: str) -> Optional[dict]:
        try:
            key = f"{self.cfg.key_prefix}{sender or 'unknown'}"
            v = self.client.get(key)
            if not v:
                return None
            return json.loads(v)
        except Exception:
            return None
    
    def buildRedisKey(self, sender: str, payload: dict) -> None:
        key = f"{self.cfg.key_prefix}{sender or 'unknown'}"
        return key