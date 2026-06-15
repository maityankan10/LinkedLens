from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

import uuid


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    linkedin_url: Mapped[str] = mapped_column(String(500), index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="session", uselist=False)
    messages: Mapped[list["ChatMessage"]] = relationship("ChatMessage", back_populates="session", order_by="ChatMessage.created_at")