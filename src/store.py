import aiosqlite
import json
import logging
from datetime import datetime
from .models import Event

logger = logging.getLogger("event_aggregator.store")

class SQLiteEventStore:
    """Asynchronous SQLite store for events and stats."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = None

    async def initialize(self):
        """Siapkan skema database jika belum ada."""
        if self.db_path == ":memory:":
            self._conn = await aiosqlite.connect(self.db_path)
            db = self._conn
            await db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    topic TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    UNIQUE(topic, event_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS stats (
                    key TEXT PRIMARY KEY,
                    value INTEGER
                )
            """)
            await db.executemany("""
                INSERT OR IGNORE INTO stats (key, value) VALUES (?, ?)
            """, [
                ("received", 0),
                ("unique_processed", 0),
                ("duplicate_dropped", 0)
            ])
            await db.commit()
            logger.info(f"Database siap di: {self.db_path}")
            return
        async with aiosqlite.connect(self.db_path) as db:
            # Table events
            await db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    topic TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    UNIQUE(topic, event_id)
                )
            """)
            # Table stats
            await db.execute("""
                CREATE TABLE IF NOT EXISTS stats (
                    key TEXT PRIMARY KEY,
                    value INTEGER
                )
            """)
            await db.executemany("""
                INSERT OR IGNORE INTO stats (key, value) VALUES (?, ?)
            """, [
                ("received", 0),
                ("unique_processed", 0),
                ("duplicate_dropped", 0)
            ])
            await db.commit()
            logger.info(f"Database siap di: {self.db_path}")

    async def is_duplicate(self, event: Event) -> bool:
        if self._conn:
            cursor = await self._conn.execute(
                "SELECT 1 FROM events WHERE topic = ? AND event_id = ?",
                (event.topic, event.event_id)
            )
            result = await cursor.fetchone()
            await cursor.close()
            return result is not None
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM events WHERE topic = ? AND event_id = ?",
                (event.topic, event.event_id)
            )
            result = await cursor.fetchone()
            await cursor.close()
            return result is not None

    async def store_event(self, event: Event) -> bool:
        """Store event and update stats."""
        if self._conn:
            db = self._conn
            await db.execute("UPDATE stats SET value = value + 1 WHERE key = 'received'")
            try:
                await db.execute(
                    """
                    INSERT INTO events (topic, event_id, timestamp, source, payload)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        event.topic,
                        event.event_id,
                        event.timestamp.isoformat(),
                        event.source,
                        json.dumps(event.payload)
                    )
                )

                await db.execute(
                    "UPDATE stats SET value = value + 1 WHERE key = 'unique_processed'"
                )
                await db.commit()
                logger.info(f"Event tersimpan: {event.topic}:{event.event_id}")
                return True
            except aiosqlite.IntegrityError:
                # Duplicate
                await db.execute(
                    "UPDATE stats SET value = value + 1 WHERE key = 'duplicate_dropped'"
                )
                await db.commit()
                logger.warning(f"Duplikat terdeteksi: {event.topic}:{event.event_id}")
                return False
            except Exception as e:
                logger.error(f"Kesalahan menyimpan event: {e}")
                return False
        # fallback: koneksi file-based per-call
        async with aiosqlite.connect(self.db_path) as db:
            # Increment received
            await db.execute("UPDATE stats SET value = value + 1 WHERE key = 'received'")
            try:
                await db.execute(
                    """
                    INSERT INTO events (topic, event_id, timestamp, source, payload)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        event.topic,
                        event.event_id,
                        event.timestamp.isoformat(),
                        event.source,
                        json.dumps(event.payload)
                    )
                )
                # Increment unique_processed
                await db.execute(
                    "UPDATE stats SET value = value + 1 WHERE key = 'unique_processed'"
                )
                await db.commit()
                logger.info(f"Event tersimpan: {event.topic}:{event.event_id}")
                return True
            except aiosqlite.IntegrityError:
                # Duplicate
                await db.execute(
                    "UPDATE stats SET value = value + 1 WHERE key = 'duplicate_dropped'"
                )
                await db.commit()
                logger.warning(f"Duplikat terdeteksi: {event.topic}:{event.event_id}")
                return False
            except Exception as e:
                logger.error(f"Kesalahan menyimpan event: {e}")
                return False

    async def get_events(self, topic: str = None):
        # support both persistent in-memory connection and file-backed DB
        if self._conn:
            db = self._conn
            if topic:
                query = "SELECT * FROM events WHERE topic = ?"
                params = (topic,)
            else:
                query = "SELECT * FROM events"
                params = ()
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            await cursor.close()
            return [
                {
                    "topic": row[0],
                    "event_id": row[1],
                    "timestamp": row[2],
                    "source": row[3],
                    "payload": json.loads(row[4])
                }
                for row in rows
            ]
        async with aiosqlite.connect(self.db_path) as db:
            if topic:
                query = "SELECT * FROM events WHERE topic = ?"
                params = (topic,)
            else:
                query = "SELECT * FROM events"
                params = ()
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            await cursor.close()
            return [
                {
                    "topic": row[0],
                    "event_id": row[1],
                    "timestamp": row[2],
                    "source": row[3],
                    "payload": json.loads(row[4])
                }
                for row in rows
            ]

    async def get_stats(self):
        if self._conn:
            db = self._conn
            cursor = await db.execute("SELECT key, value FROM stats")
            rows = await cursor.fetchall()
            await cursor.close()
            stats = {row[0]: row[1] for row in rows}
            # Include topics dynamically
            events_cursor = await db.execute("SELECT DISTINCT topic FROM events")
            topics_rows = await events_cursor.fetchall()
            await events_cursor.close()
            stats["topics"] = [row[0] for row in topics_rows]
            return stats
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT key, value FROM stats")
            rows = await cursor.fetchall()
            await cursor.close()
            stats = {row[0]: row[1] for row in rows}
            # Include topics dynamically
            events_cursor = await db.execute("SELECT DISTINCT topic FROM events")
            topics_rows = await events_cursor.fetchall()
            await events_cursor.close()
            stats["topics"] = [row[0] for row in topics_rows]
            return stats
