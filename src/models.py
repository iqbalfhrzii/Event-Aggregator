from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Dict, Any
from datetime import datetime, timezone
import uuid

# Model: Event

class Event(BaseModel):
    topic: str = Field(..., description="Nama topik, mis. 'user.created' atau 'order.paid'")
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Identitas unik event (string/UUID)"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Waktu pembuatan event dalam ISO8601 (UTC)"
    )
    source: str = Field(..., description="Sumber event, mis. 'user_service'")
    payload: Dict[str, Any] = Field(..., description="Isi data event dalam bentuk JSON")


    # Validators

    @field_validator("timestamp", mode="before")
    def ensure_utc_timestamp(cls, v):
        """Pastikan timestamp memiliki timezone UTC"""
        if isinstance(v, str):
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        elif isinstance(v, datetime):
            return v.astimezone(timezone.utc)
        raise ValueError("Invalid timestamp format")

    @field_validator("topic", "source")
    def non_empty_string(cls, v, field):
        """Validasi agar topic dan source tidak kosong"""
        if not v.strip():
            raise ValueError(f"{field.name} cannot be empty")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "topic": "account.registered",
                "event_id": "a1b2c3d4-e5f6-47a8-b9c0-112233445566",
                "timestamp": "2024-04-01T08:30:00Z",
                "source": "auth_service",
                "payload": {"account_id": "AC1001", "email": "iqbal@example.com"}
            }
        }
    )

# Model: EventBatch

class EventBatch(BaseModel):
    events: List[Event] = Field(..., description="Daftar event yang akan dipublikasikan")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "events": [
                    {
                        "topic": "payment.initiated",
                        "event_id": "pmt-20250401-001",
                        "timestamp": "2024-04-01T09:00:00Z",
                        "source": "payment_gateway",
                        "payload": {"payment_id": "P1001", "amount": 150000}
                    },
                    {
                        "topic": "shipment.scheduled",
                        "event_id": "shp-20250401-002",
                        "timestamp": "2024-04-01T09:05:00Z",
                        "source": "logistics",
                        "payload": {"order_id": "A124", "eta": "2024-04-03"}
                    }
                ]
            }
        }
    )
