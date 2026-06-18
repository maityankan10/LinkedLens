from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

import uuid


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), unique=True, index=True)
    linkedin_url: Mapped[str] = mapped_column(String(500), index=True)

    # Stored AI output fields
    profile_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[str | None] = mapped_column(Text, nullable=True)               # JSON string
    improvements: Mapped[str | None] = mapped_column(Text, nullable=True)            # JSON string
    content_ideas: Mapped[str | None] = mapped_column(Text, nullable=True)           # JSON string
    recommended_topics: Mapped[str | None] = mapped_column(Text, nullable=True)      # JSON string
    profile_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Posts pipeline fields
    posts_summary: Mapped[str | None] = mapped_column(Text, nullable=True)           # Haiku/LLM compressed summary of posts

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    session: Mapped["Session"] = relationship("Session", back_populates="analysis")