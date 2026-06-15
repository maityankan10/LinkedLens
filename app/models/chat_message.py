from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

import uuid


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))   # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    session: Mapped["Session"] = relationship("Session", back_populates="messages")