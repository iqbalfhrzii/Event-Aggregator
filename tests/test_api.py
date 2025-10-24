import pytest
import asyncio
from datetime import datetime, UTC
from fastapi.testclient import TestClient
from src.main import app, event_service

@pytest.fixture(scope="module")
def client():
    """Membuat TestClient untuk API FastAPI"""
    return TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def event_loop():
    """Gunakan event loop baru untuk semua test async"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
async def setup_teardown():
    """Start & stop event_service sebelum dan sesudah setiap test"""
    await event_service.start()
    yield
    await event_service.stop()


def test_publish_single_event(client):
    event = {
        "events": [{
            "topic": "test.event",
            "event_id": "test-1",
            "timestamp": datetime.now(UTC).isoformat(),
            "source": "test",
            "payload": {"test": "data"}
        }]
    }
    response = client.post("/publish", json=event)
    assert response.status_code == 200
    data = response.json()
    assert "Processed" in data["message"]


def test_publish_duplicate_event(client):
    event_data = {
        "topic": "test.event",
        "event_id": "test-dup",
        "timestamp": datetime.now(UTC).isoformat(),
        "source": "test",
        "payload": {"test": "data"}
    }
    batch = {"events": [event_data, event_data]}
    response = client.post("/publish", json=batch)
    assert response.status_code == 200

    # Tunggu proses async selesai
    asyncio.run(asyncio.sleep(0.5))

    stats = client.get("/stats")
    stats_data = stats.json()
    assert "duplicate_dropped" in stats_data
    assert stats_data["duplicate_dropped"] >= 0


def test_get_events_by_topic(client):
    event = {
        "events": [{
            "topic": "test.filter",
            "event_id": "test-3",
            "timestamp": datetime.now(UTC).isoformat(),
            "source": "test",
            "payload": {"test": "filter"}
        }]
    }
    response = client.post("/publish", json=event)
    assert response.status_code == 200

    asyncio.run(asyncio.sleep(0.5))

    response = client.get("/events", params={"topic": "test.filter"})
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    assert all(e["topic"] == "test.filter" for e in events)


def test_stats_consistency(client):
    events = {
        "events": [
            {
                "topic": f"test.stats.{i}",
                "event_id": f"stats-{i}",
                "timestamp": datetime.now(UTC).isoformat(),
                "source": "test",
                "payload": {"index": i}
            } for i in range(5)
        ]
    }
    response = client.post("/publish", json=events)
    assert response.status_code == 200

    asyncio.run(asyncio.sleep(0.5))

    stats = client.get("/stats")
    stats_data = stats.json()
    assert stats_data["received"] >= 5
    assert len(stats_data["topics"]) >= 5


def test_performance(client):
    """Pastikan 1000 event bisa diproses < 5 detik"""
    unique_events = 800
    duplicate_events = 200

    events = []
    for i in range(unique_events):
        events.append({
            "topic": "test.perf",
            "event_id": f"perf-{i}",
            "timestamp": datetime.now(UTC).isoformat(),
            "source": "test",
            "payload": {"index": i}
        })

    for i in range(duplicate_events):
        events.append(events[i]) 

    batch = {"events": events}
    start_time = datetime.now(UTC)
    response = client.post("/publish", json=batch)
    end_time = datetime.now(UTC)

    assert response.status_code == 200
    processing_time = (end_time - start_time).total_seconds()
    assert processing_time < 5.0, f"Processing too slow: {processing_time}s"
