import pytest
import asyncio
import os
from datetime import datetime, UTC
from src.store import SQLiteEventStore
from src.models import Event


@pytest.mark.asyncio
async def test_dedup_store_persistence(tmp_path):
    """
    Test bahwa event yang sudah tersimpan tetap terdeteksi duplikat
    setelah 'restart' (store baru dengan DB yang sama).
    """
    db_path = tmp_path / "test_events.db"

    # Instance pertama (sebelum restart)
    store1 = SQLiteEventStore(str(db_path))
    await store1.initialize()

    event = Event(
        topic="test.persistence",
        event_id="persist-1",
        timestamp=datetime.now(UTC),
        source="test",
        payload={"test": "persistence"},
    )

    is_stored = await store1.store_event(event)
    assert is_stored is True

    # Instance kedua (simulasi restart)
    store2 = SQLiteEventStore(str(db_path))
    await store2.initialize()

    is_duplicate = await store2.is_duplicate(event)
    assert is_duplicate is True


@pytest.mark.asyncio
async def test_dedup_detection():
    """
    Test bahwa event dengan (topic, event_id) yang sama hanya diproses sekali.
    """
    store = SQLiteEventStore(":memory:")
    await store.initialize()

    event = Event(
        topic="test.dedup",
        event_id="dedup-1",
        timestamp=datetime.now(UTC),
        source="test",
        payload={"test": "dedup"},
    )

    # Pertama kali harus berhasil
    result1 = await store.store_event(event)
    assert result1 is True

    # Kedua kali harus terdeteksi duplikat
    result2 = await store.store_event(event)
    assert result2 is False

    stats = await store.get_stats()
    assert stats["duplicate_dropped"] == 1


@pytest.mark.asyncio
async def test_event_retrieval():
    """
    Test bahwa semua event dapat diambil kembali,
    dan filter topic berfungsi dengan benar.
    """
    store = SQLiteEventStore(":memory:")
    await store.initialize()

    # Simpan beberapa event
    for i in range(3):
        event = Event(
            topic=f"test.retrieve.{i}",
            event_id=f"retrieve-{i}",
            timestamp=datetime.now(UTC),
            source="test",
            payload={"index": i},
        )
        await store.store_event(event)

    # Ambil semua event
    all_events = await store.get_events()
    assert len(all_events) == 3

    # Ambil berdasarkan topic
    topic_events = await store.get_events("test.retrieve.0")
    assert len(topic_events) == 1
    assert topic_events[0]["topic"] == "test.retrieve.0"
