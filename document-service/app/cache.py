import json

from redis import Redis
from redis.exceptions import RedisError


class DocumentCache:

    def __init__(self, redis_client: Redis, ttl: int = 60):
        self.redis = redis_client
        self.ttl = ttl

    def get(self, document_id: str) -> tuple[dict | None, str]:
        try:
            value = self.redis.get(self._key(document_id))

            if value is None:
                return None, "MISS"

            return json.loads(value), "HIT"

        except (RedisError, ValueError, TypeError):
            return None, "BYPASS"

    def set(self, document_id: str, document: dict) -> bool:
        try:
            self.redis.set(
                self._key(document_id),
                json.dumps(document),
                ex=self.ttl,
            )
            return True

        except RedisError:
            return False

    def invalidate(self, document_id: str) -> bool:
        try:
            self.redis.delete(self._key(document_id))
            return True

        except RedisError:
            return False

    @staticmethod
    def _key(document_id: str) -> str:
        return f"lab2:document-service:document:{document_id}"