
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None):
        self.data[key] = value
        return True

    def delete(self, key):
        self.data.pop(key, None)
        return 1

    def close(self):
        pass


@pytest.fixture
def client(tmp_path):
    database_file = tmp_path / "test.db"
    database_url = f"sqlite:///{database_file.as_posix()}"

    redis_client = FakeRedis()

    test_app = create_app(
        database_url=database_url,
        redis_client=redis_client,
    )

    with TestClient(test_app) as test_client:
        yield test_client
