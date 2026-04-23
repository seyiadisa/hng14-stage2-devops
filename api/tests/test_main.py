from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api import main


class FakeRedis:
    def __init__(self):
        self.hashes = {}
        self.queue = []
        self.ping_should_fail = False

    def ping(self):
        if self.ping_should_fail:
            raise main.redis.RedisError("redis unavailable")
        return True

    def hset(self, key, field=None, value=None, mapping=None):
        bucket = self.hashes.setdefault(key, {})
        if mapping is not None:
            bucket.update(mapping)
            return
        bucket[field] = value

    def lpush(self, queue_name, value):
        self.queue.insert(0, (queue_name, value))

    def hget(self, key, field):
        return self.hashes.get(key, {}).get(field)


@pytest.fixture
def fake_redis():
    return FakeRedis()


@pytest.fixture
def client(fake_redis):
    with patch.object(main, "r", fake_redis):
        yield TestClient(main.app)


def test_create_job_queues_job_and_sets_status(client, fake_redis):
    response = client.post("/jobs")

    assert response.status_code == 200
    body = response.json()
    job_id = body["job_id"]

    assert fake_redis.hashes[f"job:{job_id}"]["status"] == "queued"
    assert fake_redis.queue[0] == ("job", job_id)


def test_get_job_returns_existing_job_status(client, fake_redis):
    fake_redis.hset("job:test-job", mapping={"status": "completed"})

    response = client.get("/jobs/test-job")

    assert response.status_code == 200
    assert response.json() == {"job_id": "test-job", "status": "completed"}


def test_get_job_returns_404_for_unknown_job(client):
    response = client.get("/jobs/missing-job")

    assert response.status_code == 404
    assert response.json() == {"detail": "job not found"}


def test_healthcheck_returns_503_when_redis_is_unavailable(client, fake_redis):
    fake_redis.ping_should_fail = True

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "redis unavailable"}
